import { useState } from "react";
import { longDate, money } from "../format";
import type { InvoiceFact, SavedScenario, SimulationFacts } from "../types";

interface Props {
  scenario: SimulationFacts | null;
  invoices: InvoiceFact[];
  saved: SavedScenario[];
  busy: boolean;
  currency: string;
  onRun: (invoiceId: string, delayDays: number) => void;
  onClear: () => void;
  onSave: (name: string) => void;
  onLoad: (id: string) => void;
  onRecompute: (id: string) => void;
  onDelete: (id: string) => void;
}

export function ScenarioPanel({ scenario, invoices, saved, busy, currency, onRun, onClear, onSave, onLoad, onRecompute, onDelete }: Props) {
  const [invoiceId, setInvoiceId] = useState(invoices[0]?.invoice_id ?? "");
  const [delay, setDelay] = useState(14);
  const [name, setName] = useState("");
  const chosen = invoiceId || invoices[0]?.invoice_id || "";

  return (
    <div className="stack" style={{ gap: 12 }}>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          if (chosen) onRun(chosen, delay);
        }}
      >
        <label className="field">
          <span>Invoice</span>
          <select value={chosen} onChange={(e) => setInvoiceId(e.target.value)}>
            {invoices.map((i) => (
              <option key={i.invoice_id} value={i.invoice_id}>
                {i.invoice_id} · {i.customer_name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Days late</span>
          <input type="number" min={0} max={365} value={delay} onChange={(e) => setDelay(Number(e.target.value))} style={{ width: 90 }} />
        </label>
        <button type="submit" className="btn" disabled={busy || !chosen}>
          Run what-if
        </button>
        {scenario && (
          <button type="button" className="btn ghost" onClick={onClear} disabled={busy}>
            Back to baseline
          </button>
        )}
      </form>

      {scenario && (
        <div className="note">
          <strong>
            {scenario.customer_name} ({scenario.invoice_id}) pays {scenario.delay_days} days late
          </strong>
          : {money(scenario.shifted_amount, currency)} moves from {longDate(scenario.original_date)} to {longDate(scenario.shifted_date)}
          {scenario.receipt_within_horizon ? "." : ` — after the horizon end ${longDate(scenario.horizon_end)}, so it is not counted.`}{" "}
          Closing cash {money(scenario.scenario.closing_cash, currency)} vs baseline {money(scenario.baseline.closing_cash, currency)} (difference{" "}
          {money(scenario.difference_from_baseline, currency)}). The baseline is unchanged.
          <form
            className="row"
            style={{ marginTop: 8 }}
            onSubmit={(e) => {
              e.preventDefault();
              onSave(name);
              setName("");
            }}
          >
            <label className="field">
              <span>Name (optional)</span>
              <input type="text" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} placeholder={`${scenario.invoice_id} delayed ${scenario.delay_days} days`} />
            </label>
            <button type="submit" className="btn primary" disabled={busy}>
              Save scenario
            </button>
            <span className="muted">Saving is explicit; chat never saves.</span>
          </form>
        </div>
      )}

      <div>
        <h3>Saved scenarios</h3>
        {saved.length === 0 ? (
          <p className="muted">None saved yet.</p>
        ) : (
          <ul className="list" aria-label="Saved scenarios">
            {saved.map((s) => (
              <li key={s.scenario_id}>
                <div>
                  <span className="id">{s.name}</span>{" "}
                  <span className="sub">
                    {s.invoice_id} · {s.delay_days} days · dataset {s.dataset_version}
                  </span>
                  {s.stale && (
                    <div className="sub" style={{ color: "var(--critical)" }}>
                      Saved for dataset {s.dataset_version}; current is {s.current_dataset_version}. Recompute before comparing.
                    </div>
                  )}
                </div>
                <span className="row" style={{ gap: 6 }}>
                  {s.stale ? (
                    <button type="button" className="btn small" onClick={() => onRecompute(s.scenario_id)} disabled={busy}>
                      Recompute
                    </button>
                  ) : (
                    <button type="button" className="btn small" onClick={() => onLoad(s.scenario_id)} disabled={busy}>
                      Load
                    </button>
                  )}
                  <button type="button" className="btn small ghost" onClick={() => onDelete(s.scenario_id)} disabled={busy} aria-label={`Delete ${s.name}`}>
                    Delete
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
