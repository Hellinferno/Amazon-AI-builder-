import { useEffect, useState } from "react";
import { longDate, money } from "../format";
import type { InvoiceFact, ReminderDraft } from "../types";

interface Props {
  draft: ReminderDraft | null;
  invoices: InvoiceFact[];
  busy: boolean;
  onDraft: (invoiceId: string, tone: "friendly" | "firm") => void;
}

export function ReminderPanel({ draft, invoices, busy, onDraft }: Props) {
  const [invoiceId, setInvoiceId] = useState(invoices[0]?.invoice_id ?? "");
  const [tone, setTone] = useState<"friendly" | "firm">("friendly");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!invoiceId && invoices[0]) setInvoiceId(invoices[0].invoice_id);
  }, [invoices, invoiceId]);

  useEffect(() => {
    if (draft) {
      setSubject(draft.subject);
      setBody(draft.body);
      setInvoiceId(draft.invoice_id);
      setTone(draft.tone);
      setCopied(false);
    }
  }, [draft]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="stack draft" style={{ gap: 10 }}>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          if (invoiceId) onDraft(invoiceId, tone);
        }}
      >
        <label className="field">
          <span>Invoice</span>
          <select value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)}>
            {invoices.map((i) => (
              <option key={i.invoice_id} value={i.invoice_id}>
                {i.invoice_id} · {i.customer_name} · {money(i.remaining_amount, i.currency)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Tone</span>
          <select value={tone} onChange={(e) => setTone(e.target.value as "friendly" | "firm")}>
            <option value="friendly">Friendly</option>
            <option value="firm">Firm</option>
          </select>
        </label>
        <button type="submit" className="btn" disabled={busy || !invoiceId}>
          Draft reminder
        </button>
      </form>
      {draft ? (
        <>
          <div className="note warning" role="status">
            <strong>Draft only — not sent.</strong> Grounded on {draft.invoice_id} ({money(draft.amount_outstanding, draft.currency)} outstanding, due{" "}
            {longDate(draft.due_date)}). Edit freely; this app cannot send messages.
          </div>
          <label className="field">
            <span>Subject</span>
            <input className="subject" type="text" value={subject} onChange={(e) => setSubject(e.target.value)} />
          </label>
          <label className="field">
            <span>Message</span>
            <textarea value={body} onChange={(e) => setBody(e.target.value)} />
          </label>
          <div className="row">
            <button type="button" className="btn" onClick={copy}>
              {copied ? "Copied" : "Copy to clipboard"}
            </button>
            <span className="muted">Nothing leaves this page unless you paste it somewhere yourself.</span>
          </div>
        </>
      ) : (
        <p className="muted">Ask the assistant to “draft a reminder for Customer A”, or use the form above.</p>
      )}
    </div>
  );
}
