import { useState } from "react";
import { longDate, money } from "../format";
import type { AppState, ImportIssue } from "../types";

interface Props {
  state: AppState;
  horizonEnd: string;
  busy: boolean;
  onHorizonChange: (iso: string) => void;
  onReset: () => void;
  onImport: (snapshot: string, invoices: File, obligations: File) => Promise<void>;
  importIssues: ImportIssue[];
  importMessage: string | null;
}

export function DatasetPanel({ state, horizonEnd, busy, onHorizonChange, onReset, onImport, importIssues, importMessage }: Props) {
  const ds = state.dataset;
  const [showImport, setShowImport] = useState(false);
  const [snapshot, setSnapshot] = useState("");
  const [invoices, setInvoices] = useState<File | null>(null);
  const [obligations, setObligations] = useState<File | null>(null);

  if (!ds) return <p className="note error">No dataset is loaded. Use “Reset sample” to load the synthetic fixture.</p>;

  return (
    <div className="stack" style={{ gap: 10 }}>
      <dl className="kv">
        <dt>Business</dt>
        <dd>{state.business_name} (synthetic)</dd>
        <dt>Dataset</dt>
        <dd>
          <code>{ds.dataset_version}</code> · {ds.invoice_count} invoices, {ds.obligation_count} obligations
        </dd>
        <dt>As-of date</dt>
        <dd>
          {longDate(ds.as_of_date)} ({ds.timezone})
        </dd>
        <dt>Opening cash</dt>
        <dd>{money(ds.opening_cash, ds.currency)}</dd>
      </dl>
      <div className="row">
        <label className="field">
          <span>Forecast through</span>
          <input type="date" value={horizonEnd} min={ds.as_of_date} onChange={(e) => e.target.value && onHorizonChange(e.target.value)} />
        </label>
        {state.demo_reset_enabled && (
          <button type="button" className="btn" onClick={onReset} disabled={busy}>
            Reset sample
          </button>
        )}
        <button type="button" className="btn ghost" onClick={() => setShowImport((v) => !v)} aria-expanded={showImport}>
          {showImport ? "Hide import" : "Import CSVs"}
        </button>
      </div>
      {showImport && (
        <form
          className="stack"
          style={{ gap: 8 }}
          onSubmit={async (e) => {
            e.preventDefault();
            if (invoices && obligations) await onImport(snapshot, invoices, obligations);
          }}
        >
          <label className="field">
            <span>Snapshot JSON (business_id, dataset_version, currency, timezone, as_of_date, opening_cash)</span>
            <textarea rows={4} value={snapshot} onChange={(e) => setSnapshot(e.target.value)} placeholder='{"business_id":"demo-business","dataset_version":"demo-v2",...}' />
          </label>
          <label className="field">
            <span>invoices.csv</span>
            <input type="file" accept=".csv,text/csv" onChange={(e) => setInvoices(e.target.files?.[0] ?? null)} />
          </label>
          <label className="field">
            <span>obligations.csv</span>
            <input type="file" accept=".csv,text/csv" onChange={(e) => setObligations(e.target.files?.[0] ?? null)} />
          </label>
          <div className="row">
            <button type="submit" className="btn primary" disabled={busy || !snapshot || !invoices || !obligations}>
              Validate and import
            </button>
            <span className="muted">A single invalid row rejects the whole import; nothing changes.</span>
          </div>
        </form>
      )}
      {importMessage && <p className={`note ${importIssues.length ? "error" : "good"}`}>{importMessage}</p>}
      {importIssues.length > 0 && (
        <ul className="errors">
          {importIssues.map((i, idx) => (
            <li key={idx}>
              {i.file}
              {i.row_number != null ? ` row ${i.row_number}` : ""}
              {i.field ? ` · ${i.field}` : ""}: {i.reason}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
