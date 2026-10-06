"""Deterministic prose from tool results.

Used by the mock provider as its "model" and by the orchestrator as the safe
fallback whenever a live explanation is missing or fails the grounding check.
Every amount is copied from a tool envelope; nothing is computed here.
"""

import re

from ..formatting import display_date, money
from ..tools import (
    TOOL_DRAFT_REMINDER,
    TOOL_GET_CASHFLOW,
    TOOL_GET_EVIDENCE,
    TOOL_LIST_OPEN_INVOICES,
    TOOL_LIST_OVERDUE,
    TOOL_SIMULATE_DELAY,
)

MOCK_FOOTER = (
    "[Mock mode: this explanation was composed by a rule-based planner from the tool "
    "results above. No model was called.]"
)
FALLBACK_NOTE = (
    "[The model's explanation was replaced by a template because it did not match the "
    "tool results. The figures below are taken directly from the tools.]"
)

_YES_NO_WORDS = re.compile(r"\b(cover|afford|enough|manage|safe|okay|ok|survive|meet)\b", re.I)

__all__ = ["compose_answer", "money", "display_date", "MOCK_FOOTER", "FALLBACK_NOTE"]


def _records_line(entries: list[dict], limit: int = 8) -> str:
    ids = []
    for e in entries:
        label = e.get("record_id", "")
        name = e.get("counterparty")
        if name:
            label = f"{label} ({name})"
        if label and label not in ids:
            ids.append(label)
    if not ids:
        return ""
    shown = ", ".join(ids[:limit])
    more = f" and {len(ids) - limit} more" if len(ids) > limit else ""
    return f"Based on records: {shown}{more}."


def _forecast_sentences(summary: dict, currency: str) -> list[str]:
    out = []
    if summary.get("first_negative_date"):
        out.append(
            f"Cash first goes negative on {display_date(summary['first_negative_date'])}; the lowest "
            f"end-of-day balance is {money(summary['minimum_balance'], currency)} on "
            f"{display_date(summary['minimum_date'])}. You would need "
            f"{money(summary['shortfall_below_zero'], currency)} more at the start of the period to "
            "keep every day at or above zero."
        )
    else:
        out.append(
            f"The lowest end-of-day balance is {money(summary['minimum_balance'], currency)} on "
            f"{display_date(summary['minimum_date'])}; no day goes negative."
        )
    return out


def compose_cashflow(env: dict, question: str) -> str:
    f = env["facts"]
    cur = env["currency"]
    parts = []
    if _YES_NO_WORDS.search(question or ""):
        parts.append("Short answer: no." if f.get("first_negative_date") else "Short answer: yes.")
    parts.append(
        f"Baseline forecast from {display_date(env['as_of_date'])} to {display_date(f['horizon_end'])}: "
        f"opening cash {money(f['opening_cash'], cur)}, closing cash {money(f['closing_cash'], cur)} "
        f"after {money(f['total_inflows'], cur)} in expected receipts and "
        f"{money(f['total_outflows'], cur)} in payments."
    )
    parts.extend(_forecast_sentences(f, cur))
    if f.get("unresolved"):
        items = ", ".join(
            f"{u['record_id']} ({money(u['amount'], cur)}, {u['reason']})" for u in f["unresolved"]
        )
        parts.append(f"Not included because they have no usable date: {items}.")
    if f.get("beyond_horizon"):
        items = ", ".join(
            f"{m['record_id']} ({money(m['amount'], cur)} on {display_date(m['effective_date'])})"
            for m in f["beyond_horizon"]
        )
        parts.append(f"After the horizon and not counted: {items}.")
    line = _records_line(f.get("movements", []) + f.get("unresolved", []))
    if line:
        parts.append(line)
    return " ".join(parts)


def compose_simulation(env: dict, question: str) -> str:
    f = env["facts"]
    cur = env["currency"]
    scen, base = f["scenario"], f["baseline"]
    parts = []
    if _YES_NO_WORDS.search(question or ""):
        parts.append("Short answer: no." if scen.get("first_negative_date") else "Short answer: yes.")
    moved = (
        f"If {f['customer_name']} ({f['invoice_id']}) pays {f['delay_days']} days late, the receipt of "
        f"{money(f['shifted_amount'], cur)} moves from {display_date(f['original_date'])} to "
        f"{display_date(f['shifted_date'])}"
    )
    if not f.get("receipt_within_horizon"):
        moved += f", which is after the horizon end {display_date(f['horizon_end'])}, so it is not counted"
    parts.append(moved + ".")
    parts.append(
        f"Closing cash on {display_date(f['horizon_end'])}: {money(scen['closing_cash'], cur)} in the "
        f"scenario versus {money(base['closing_cash'], cur)} in the baseline "
        f"(difference {money(f['difference_from_baseline'], cur)})."
    )
    parts.extend(_forecast_sentences(scen, cur))
    parts.append("The baseline forecast itself is unchanged.")
    line = _records_line(
        [{"record_id": f["invoice_id"], "counterparty": f["customer_name"]}]
        + f.get("scenario_movements", [])
        + f.get("scenario_beyond_horizon", [])
    )
    if line:
        parts.append(line)
    return " ".join(parts)


def compose_overdue(env: dict, question: str) -> str:
    f = env["facts"]
    cur = env["currency"]
    invoices, obligations = f.get("invoices", []), f.get("obligations", [])
    if not invoices and not obligations:
        return f"Nothing is overdue as of {display_date(env['as_of_date'])}."
    parts = []
    if invoices:
        items = "; ".join(
            f"{i['record_id']} from {i['counterparty']}, {money(i['remaining_amount'], cur)}, due "
            f"{display_date(i['due_date'])} ({i['days_overdue']} days overdue)"
            for i in invoices
        )
        parts.append(
            f"Overdue receivables total {money(f['total_overdue_receivable'], cur)}: {items}."
        )
    if obligations:
        items = "; ".join(
            f"{o['record_id']} to {o['counterparty']}, {money(o['remaining_amount'], cur)}, due "
            f"{display_date(o['due_date'])} ({o['days_overdue']} days overdue)"
            for o in obligations
        )
        parts.append(f"Overdue payables total {money(f['total_overdue_payable'], cur)}: {items}.")
    return " ".join(parts)


def compose_open_invoices(env: dict, question: str) -> str:
    f = env["facts"]
    cur = env["currency"]
    if not f.get("invoices"):
        return "There are no open invoices in this dataset."
    items = "; ".join(
        f"{i['invoice_id']} from {i['customer_name']}, {money(i['remaining_amount'], cur)} outstanding, "
        f"due {display_date(i['due_date'])}, expected "
        f"{display_date(i['expected_receipt_date']) if i['expected_receipt_date'] else 'no date'}"
        for i in f["invoices"]
    )
    return f"Open invoices total {money(f['total_outstanding'], cur)}: {items}."


def compose_evidence(env: dict, question: str) -> str:
    f = env["facts"]
    r = f["record"]
    cur = env["currency"]
    src = f["source"]
    if f["record_type"] == "invoice":
        head = (
            f"Invoice {r['invoice_id']} from {r['customer_name']}: total {money(r['total_amount'], cur)}, "
            f"settled before the as-of date {money(r['settled_before_as_of'], cur)}, remaining "
            f"{money(r['remaining_amount'], cur)}, due {display_date(r['due_date'])}, expected receipt "
            f"{display_date(r['expected_receipt_date']) if r['expected_receipt_date'] else 'no date'}, "
            f"status {r['status']}{', overdue' if r.get('overdue') else ''}."
        )
    else:
        head = (
            f"Obligation {r['obligation_id']} to {r['payee_name']} ({r['category']}): total "
            f"{money(r['total_amount'], cur)}, settled before the as-of date "
            f"{money(r['settled_before_as_of'], cur)}, remaining {money(r['remaining_amount'], cur)}, due "
            f"{display_date(r['due_date'])}, expected payment "
            f"{display_date(r['expected_payment_date']) if r['expected_payment_date'] else 'no date'}, "
            f"status {r['status']}."
        )
    return f"{head} Source: {src['record_type']}s file {src['source_file_id']}, row {src['row_number']}."


def compose_reminder(env: dict, question: str) -> str:
    d = env["facts"]["draft"]
    return (
        f"Here is a {d['tone']} reminder draft for {d['customer_name']} about invoice {d['invoice_id']} "
        f"({money(d['amount_outstanding'], env['currency'])} outstanding, due {display_date(d['due_date'])}). "
        "It has not been sent; edit it in the draft panel before you use it.\n\n"
        f"Subject: {d['subject']}\n\n{d['body']}"
    )


def compose_error(env: dict) -> str:
    err = env.get("error") or {}
    return f"I could not complete that: {err.get('message', 'unknown error')} (code {err.get('code')})."


_COMPOSERS = {
    TOOL_GET_CASHFLOW: compose_cashflow,
    TOOL_SIMULATE_DELAY: compose_simulation,
    TOOL_LIST_OVERDUE: compose_overdue,
    TOOL_LIST_OPEN_INVOICES: compose_open_invoices,
    TOOL_GET_EVIDENCE: compose_evidence,
    TOOL_DRAFT_REMINDER: compose_reminder,
}


def compose_answer(question: str, envelopes: list[dict], notes: list[str] = ()) -> str:
    """One paragraph per tool result, in call order, followed by any notes."""
    if not envelopes:
        return "No calculation was run for that question, so there is nothing to report."
    paragraphs = []
    for env in envelopes:
        if env.get("status") != "ok":
            paragraphs.append(compose_error(env))
            continue
        composer = _COMPOSERS.get(env.get("tool"))
        paragraphs.append(composer(env, question) if composer else "Tool result received.")
        for w in env.get("warnings", []):
            if w not in paragraphs:
                paragraphs.append(f"Note: {w}")
    for note in notes:
        paragraphs.append(note)
    return "\n\n".join(paragraphs)
