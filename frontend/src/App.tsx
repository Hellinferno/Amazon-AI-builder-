import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiFailure, api, importErrors } from "./api";
import { Banner } from "./components/Banner";
import { BalanceChart, type ChartPoint } from "./components/BalanceChart";
import { Chat } from "./components/Chat";
import { DatasetPanel } from "./components/DatasetPanel";
import { EvidencePanel } from "./components/EvidencePanel";
import { ForecastTable } from "./components/ForecastTable";
import { ReminderPanel } from "./components/ReminderPanel";
import { ScenarioPanel } from "./components/ScenarioPanel";
import { SummaryTiles } from "./components/SummaryTiles";
import type {
  AppState,
  CashflowFacts,
  ChatMessage,
  Envelope,
  Evidence,
  ImportIssue,
  InvoiceFact,
  RecordFacts,
  ReminderDraft,
  SavedScenario,
  SimulationFacts,
} from "./types";

const SUGGESTIONS = [
  "Can we cover Friday's payroll?",
  "What if Customer A pays two weeks late?",
  "And if it is three weeks instead?",
  "Who is overdue?",
  "Show me the evidence for INV-001",
  "Draft a firm reminder for Customer A",
];

function describe(err: unknown): string {
  if (err instanceof ApiFailure) return `${err.message} (${err.code})`;
  return err instanceof Error ? err.message : String(err);
}

let counter = 0;
const nextId = () => `m${++counter}`;

export function App() {
  const [state, setState] = useState<AppState | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [horizonEnd, setHorizonEnd] = useState<string>("");
  const [baseline, setBaseline] = useState<CashflowFacts | null>(null);
  const [baselineCurrency, setBaselineCurrency] = useState("INR");
  const [scenario, setScenario] = useState<SimulationFacts | null>(null);
  const [scenarioLabel, setScenarioLabel] = useState<string | undefined>(undefined);
  const [invoices, setInvoices] = useState<InvoiceFact[]>([]);
  const [saved, setSaved] = useState<SavedScenario[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [inspected, setInspected] = useState<RecordFacts | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [draft, setDraft] = useState<ReminderDraft | null>(null);
  const [importIssues, setImportIssues] = useState<ImportIssue[]>([]);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const horizonRef = useRef(horizonEnd);
  horizonRef.current = horizonEnd;

  const currency = state?.dataset?.currency ?? baselineCurrency;

  const loadDashboard = useCallback(async (horizon?: string) => {
    const st = await api.state();
    setState(st);
    setBackendError(null);
    const h = horizon || st.dataset?.default_horizon_end || "";
    setHorizonEnd(h);
    const [forecast, inv, sc] = await Promise.all([api.forecast(h || undefined), api.invoices(), api.scenarios()]);
    setBaseline(forecast.facts);
    setBaselineCurrency(forecast.currency ?? "INR");
    setInvoices(inv.facts.invoices);
    setSaved(sc.scenarios);
    return st;
  }, []);

  useEffect(() => {
    loadDashboard().catch((err) => setBackendError(describe(err)));
  }, [loadDashboard]);

  async function withBusy<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setNotice(null);
    try {
      return await fn();
    } catch (err) {
      setNotice(describe(err));
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  async function changeHorizon(iso: string) {
    await withBusy(async () => {
      const forecast = await api.forecast(iso);
      setBaseline(forecast.facts);
      setHorizonEnd(iso);
      if (scenario) {
        const sim = await api.simulate(scenario.invoice_id, scenario.delay_days, iso);
        setScenario(sim.facts);
      }
    });
  }

  async function runScenario(invoiceId: string, delayDays: number, label?: string) {
    await withBusy(async () => {
      const sim = await api.simulate(invoiceId, delayDays, horizonRef.current || undefined);
      setScenario(sim.facts);
      setScenarioLabel(label ?? `${sim.facts.customer_name} ${delayDays}d late`);
      setEvidence(sim.evidence);
    });
  }

  function applyChatResponse(resp: Envelope[]) {
    for (const env of resp) {
      if (env.status !== "ok") continue;
      if (env.tool === "simulate_payment_delay") {
        const f = env.facts as unknown as SimulationFacts;
        setScenario(f);
        setScenarioLabel(`${f.customer_name} ${f.delay_days}d late`);
      } else if (env.tool === "get_cashflow") {
        const f = env.facts as unknown as CashflowFacts;
        setBaseline(f);
        setHorizonEnd(f.horizon_end);
        setScenario(null);
      } else if (env.tool === "draft_collection_reminder") {
        setDraft((env.facts as unknown as { draft: ReminderDraft }).draft);
      } else if (env.tool === "get_record_evidence") {
        setInspected(env.facts as unknown as RecordFacts);
      }
    }
  }

  async function send(text: string) {
    setChatError(null);
    setMessages((m) => [...m, { id: nextId(), role: "user", text }]);
    setChatBusy(true);
    try {
      const resp = await api.chat(text, sessionId);
      setSessionId(resp.session_id);
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: resp.answer, response: resp, failed: resp.status === "error" }]);
      if (resp.evidence.length) setEvidence(resp.evidence);
      applyChatResponse(resp.tool_results);
      if (resp.session.horizon_end && resp.session.horizon_end !== horizonRef.current) {
        const forecast = await api.forecast(resp.session.horizon_end);
        setBaseline(forecast.facts);
        setHorizonEnd(resp.session.horizon_end);
      }
      if (resp.status === "error" && resp.error) setChatError(`${resp.error.message} (${resp.error.code})`);
    } catch (err) {
      const message = describe(err);
      setChatError(message);
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `The assistant could not answer: ${message}. The figures on this page are unaffected.`, failed: true }]);
    } finally {
      setChatBusy(false);
    }
  }

  async function inspect(type: "invoice" | "obligation", id: string) {
    setInspecting(true);
    try {
      setInspected((await api.record(type, id)).facts);
    } catch (err) {
      setNotice(describe(err));
    } finally {
      setInspecting(false);
    }
  }

  async function reset() {
    await withBusy(async () => {
      const out = await api.reset();
      setScenario(null);
      setMessages([]);
      setSessionId(null);
      setEvidence([]);
      setInspected(null);
      setDraft(null);
      setImportIssues([]);
      setImportMessage(null);
      await loadDashboard();
      setNotice(`Sample dataset ${out.dataset_version} restored; ${out.scenarios_cleared} saved scenario(s) cleared.`);
    });
  }

  async function importDataset(snapshot: string, inv: File, ob: File) {
    setImportIssues([]);
    setImportMessage(null);
    await withBusy(async () => {
      try {
        const out = await api.importDataset(snapshot, inv, ob);
        setImportMessage(`Imported ${out.dataset_version}: ${out.invoice_count} invoices, ${out.obligation_count} obligations.${out.stale_scenarios.length ? ` ${out.stale_scenarios.length} saved scenario(s) are now stale.` : ""}`);
        setScenario(null);
        setEvidence([]);
        setInspected(null);
        await loadDashboard();
      } catch (err) {
        if (err instanceof ApiFailure) {
          setImportIssues(importErrors(err));
          setImportMessage(err.message);
          return;
        }
        throw err;
      }
    });
  }

  const chartPoints: ChartPoint[] = useMemo(() => {
    if (!baseline) return [];
    const byDate = new Map(scenario?.daily.map((d) => [d.date, d.scenario_closing]) ?? []);
    return baseline.daily.map((d) => ({ date: d.date, baseline: d.closing, scenario: byDate.get(d.date) }));
  }, [baseline, scenario]);

  return (
    <div className="app">
      <Banner state={state} backendError={backendError} />
      <header className="masthead">
        <div>
          <h1>Cashflow Assistant</h1>
          <p className="sub">Ask whether upcoming receipts cover payroll and bills. Every figure comes from the records shown on the right.</p>
        </div>
        {notice && (
          <p className="note" role="status">
            {notice}
          </p>
        )}
      </header>
      {backendError && (
        <p className="note error" role="alert">
          {backendError} Start it with <code>uvicorn cashflow_app.main:app</code> and reload.
        </p>
      )}
      <div className="grid">
        <div className="stack">
          <Chat messages={messages} busy={chatBusy} error={chatError} mode={state?.mode ?? null} suggestions={SUGGESTIONS} onSend={send} />
          <section className="card" aria-labelledby="reminder-h">
            <div className="card-head">
              <h2 id="reminder-h">Reminder draft</h2>
              <span className="hint">review only · never sent</span>
            </div>
            <ReminderPanel draft={draft} invoices={invoices} busy={busy} onDraft={(id, tone) => withBusy(async () => setDraft((await api.reminder(id, tone)).facts.draft))} />
          </section>
        </div>
        <div className="stack">
          <section className="card" aria-labelledby="dataset-h">
            <div className="card-head">
              <h2 id="dataset-h">Sample business</h2>
              <span className="hint">synthetic fixture · reset at any time</span>
            </div>
            {state ? (
              <DatasetPanel state={state} horizonEnd={horizonEnd} busy={busy} onHorizonChange={changeHorizon} onReset={reset} onImport={importDataset} importIssues={importIssues} importMessage={importMessage} />
            ) : (
              <p className="muted">Loading…</p>
            )}
          </section>
          <section className="card" aria-labelledby="forecast-h">
            <div className="card-head">
              <h2 id="forecast-h">{scenario ? "Baseline vs scenario" : "Baseline forecast"}</h2>
              <span className="hint">end-of-day balances · {currency}</span>
            </div>
            <SummaryTiles baseline={baseline} scenario={scenario} currency={currency} />
            {baseline && (
              <div style={{ marginTop: 14 }}>
                <BalanceChart points={chartPoints} currency={currency} scenarioLabel={scenarioLabel} />
              </div>
            )}
            {baseline && (
              <div style={{ marginTop: 10 }}>
                <ForecastTable baseline={baseline} scenario={scenario} currency={currency} />
              </div>
            )}
            {baseline && baseline.unresolved.length > 0 && (
              <p className="note warning" style={{ marginTop: 10 }}>
                {baseline.unresolved.length} open item(s) have no usable expected date and are excluded from the timed forecast. See the records list.
              </p>
            )}
          </section>
          <section className="card" aria-labelledby="scenario-h">
            <div className="card-head">
              <h2 id="scenario-h">What-if scenario</h2>
              <span className="hint">one invoice, moved later · baseline never edited</span>
            </div>
            <ScenarioPanel
              scenario={scenario}
              invoices={invoices}
              saved={saved}
              busy={busy}
              currency={currency}
              onRun={(id, d) => runScenario(id, d)}
              onClear={() => setScenario(null)}
              onSave={(name) =>
                scenario &&
                withBusy(async () => {
                  const out = await api.saveScenario(scenario.invoice_id, scenario.delay_days, name);
                  setSaved((await api.scenarios()).scenarios);
                  setNotice(`Saved “${out.scenario.name}” for dataset ${out.scenario.dataset_version}.`);
                })
              }
              onLoad={(id) =>
                withBusy(async () => {
                  const out = await api.getScenario(id);
                  setScenario(out.result.facts);
                  setScenarioLabel(out.scenario.name);
                  setEvidence(out.result.evidence);
                })
              }
              onRecompute={(id) =>
                withBusy(async () => {
                  const out = await api.recomputeScenario(id);
                  setScenario(out.result.facts);
                  setScenarioLabel(out.scenario.name);
                  setSaved((await api.scenarios()).scenarios);
                  setNotice(`Recomputed on dataset ${out.scenario.dataset_version} as a new saved scenario.`);
                })
              }
              onDelete={(id) =>
                withBusy(async () => {
                  await api.deleteScenario(id);
                  setSaved((await api.scenarios()).scenarios);
                })
              }
            />
          </section>
          <section className="card" aria-labelledby="evidence-h">
            <div className="card-head">
              <h2 id="evidence-h">Supporting records</h2>
              <span className="hint">every amount traces to a row</span>
            </div>
            <EvidencePanel
              movements={scenario ? scenario.scenario_movements : (baseline?.movements ?? [])}
              beyondHorizon={scenario ? scenario.scenario_beyond_horizon : (baseline?.beyond_horizon ?? [])}
              unresolved={scenario ? scenario.unresolved : (baseline?.unresolved ?? [])}
              evidence={evidence}
              inspected={inspected}
              inspecting={inspecting}
              onInspect={inspect}
              currency={currency}
            />
          </section>
        </div>
      </div>
    </div>
  );
}
