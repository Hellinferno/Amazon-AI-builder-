import { longDate, money } from "../format";
import type { Evidence, InvoiceFact, MovementFact, ObligationFact, RecordFacts, UnresolvedFact } from "../types";

interface Props {
  movements: MovementFact[];
  beyondHorizon: MovementFact[];
  unresolved: UnresolvedFact[];
  evidence: Evidence[];
  inspected: RecordFacts | null;
  inspecting: boolean;
  onInspect: (type: "invoice" | "obligation", id: string) => void;
  currency: string;
}

function RecordDetails({ facts, currency }: { facts: RecordFacts; currency: string }) {
  const r = facts.record;
  const isInvoice = facts.record_type === "invoice";
  const inv = r as InvoiceFact;
  const ob = r as ObligationFact;
  return (
    <div>
      <h3>
        {isInvoice ? `Invoice ${inv.invoice_id}` : `Obligation ${ob.obligation_id}`}
        {isInvoice && inv.overdue && (
          <span className="badge error" style={{ marginLeft: 8 }}>
            overdue
          </span>
        )}
      </h3>
      <dl className="kv" style={{ marginTop: 6 }}>
        <dt>{isInvoice ? "Customer" : "Payee"}</dt>
        <dd>{isInvoice ? inv.customer_name : `${ob.payee_name} (${ob.category})`}</dd>
        <dt>Total</dt>
        <dd>{money(r.total_amount, currency)}</dd>
        <dt>Settled before as-of</dt>
        <dd>{money(r.settled_before_as_of, currency)}</dd>
        <dt>Remaining</dt>
        <dd>{money(r.remaining_amount, currency)}</dd>
        <dt>Due</dt>
        <dd>{longDate(r.due_date)}</dd>
        <dt>Expected {isInvoice ? "receipt" : "payment"}</dt>
        <dd>{longDate(isInvoice ? inv.expected_receipt_date : ob.expected_payment_date)}</dd>
        <dt>Status</dt>
        <dd>{r.status}</dd>
        <dt>Source</dt>
        <dd>
          <code>{facts.source.source_file_id}</code> row {facts.source.row_number}
        </dd>
      </dl>
    </div>
  );
}

export function EvidencePanel({ movements, beyondHorizon, unresolved, evidence, inspected, inspecting, onInspect, currency }: Props) {
  const cited = new Set(evidence.map((e) => `${e.record_type}:${e.record_id}`));
  const rows = [
    ...movements.map((m) => ({ ...m, note: `${m.direction === "inflow" ? "receipt" : "payment"} on ${longDate(m.effective_date)}`, origin: m.assumption_origin })),
    ...beyondHorizon.map((m) => ({ ...m, note: `after the horizon: ${longDate(m.effective_date)}`, origin: m.assumption_origin })),
    ...unresolved.map((u) => ({ record_type: u.record_type, record_id: u.record_id, counterparty: u.counterparty, amount: u.amount, note: `excluded: ${u.reason}`, origin: "unresolved" })),
  ];
  return (
    <div className="stack" style={{ gap: 12 }}>
      {rows.length === 0 ? (
        <p className="muted">No records feed the current forecast.</p>
      ) : (
        <ul className="list" aria-label="Supporting records">
          {rows.map((r) => (
            <li key={`${r.record_type}:${r.record_id}:${r.origin}`}>
              <div>
                <span className="id">{r.record_id}</span> <span className="sub">{r.counterparty}</span>
                <div className="sub">
                  {money(r.amount, currency)} · {r.note}
                  {r.origin.startsWith("scenario:") ? " · moved by scenario" : ""}
                  {cited.has(`${r.record_type}:${r.record_id}`) ? " · cited in the last answer" : ""}
                </div>
              </div>
              <button type="button" className="btn small" onClick={() => onInspect(r.record_type, r.record_id)} disabled={inspecting}>
                Source
              </button>
            </li>
          ))}
        </ul>
      )}
      {inspected && (
        <div className="note">
          <RecordDetails facts={inspected} currency={currency} />
        </div>
      )}
    </div>
  );
}
