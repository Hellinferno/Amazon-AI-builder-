"""Visibly mocked model provider.

A rule-based planner maps the user's question to tool calls, and the
deterministic composer turns tool results into prose. It exists so the whole
workflow (tools, grounding, evidence, sessions, UI) runs and is testable
without AWS. It is not a language model and is labelled as such in every
answer.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from cashflow.dates import MAX_HORIZON_DAYS
from cashflow.models import RECORD_INVOICE, RECORD_OBLIGATION, STATUS_OPEN, Invoice

from ..tools import (
    TOOL_DRAFT_REMINDER,
    TOOL_GET_CASHFLOW,
    TOOL_GET_EVIDENCE,
    TOOL_LIST_OPEN_INVOICES,
    TOOL_LIST_OVERDUE,
    TOOL_SIMULATE_DELAY,
    find_invoice,
    find_obligation,
    resolve_invoice_reference,
)
from ..formatting import display_date
from .compose import MOCK_FOOTER, compose_answer
from .provider import ModelTurn, PlannerContext, ToolCall, latest_user_text, tool_results_after

MOCK_MODEL_ID = "mock-rule-based-planner"

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "couple": 2, "fortnight": 14,
}
_UNIT_DAYS = {"day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30}

_RE_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_RE_DURATION = re.compile(
    r"\b(\d{1,3}|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|couple(?: of)?)"
    r"[\s-]*(days?|weeks?|months?)\b",
    re.I,
)
_RE_FORTNIGHT = re.compile(r"\bfortnight\b", re.I)
_RE_UNSUPPORTED = re.compile(
    r"\b(send|email|e-mail|mail|text|sms|whatsapp|transfer|wire|pay (him|her|them|it|the)|"
    r"make (a|the) payment|file (the |my )?(gst|tax|return)|submit)\b",
    re.I,
)
_RE_REMINDER = re.compile(r"\b(remind|reminder|chase|chaser|nudge|follow[- ]?up|draft)\b", re.I)
_RE_FIRM = re.compile(r"\b(firm|strict|formal|stern|final notice)\b", re.I)
_RE_DELAY = re.compile(
    r"\b(late|later|delay|delays|delayed|slip|slips|postpone|postponed|push(ed|es)?|defer|"
    r"pays? (in|on|after|only)|pays? me|instead|what about|what if)\b",
    re.I,
)
_RE_OVERDUE = re.compile(r"\b(overdue|past[- ]due|who owes|owes us|outstanding|unpaid)\b", re.I)
_RE_EVIDENCE = re.compile(
    r"\b(evidence|source|sources|prove|proof|show (me )?(the )?(records?|rows?|details?)|"
    r"where (does|did|do) .* come from|which records?|based on what|details (for|of|on))\b",
    re.I,
)
_RE_LIST_INVOICES = re.compile(r"\b(which|what|list|show)( open| the| all| my)* invoices\b", re.I)
_RE_BASELINE = re.compile(r"\b(baseline|without (the|any) delay|original forecast|as planned)\b", re.I)
_RE_PAYROLL = re.compile(r"\b(payroll|salaries|salary|wages)\b", re.I)
_RE_RECORD_ID = re.compile(r"\b([A-Za-z][A-Za-z0-9._-]{0,63})\b")

K_CASHFLOW = "cashflow"
K_DELAY = "delay"
K_OVERDUE = "overdue"
K_EVIDENCE = "evidence"
K_REMINDER = "reminder"
K_LIST_INVOICES = "list_invoices"
K_UNSUPPORTED = "unsupported"
K_AMBIGUOUS = "ambiguous"
K_NEED_INVOICE = "need_invoice"
K_NEED_DELAY = "need_delay"


@dataclass
class Intent:
    kind: str
    invoice: Invoice | None = None
    candidates: list[Invoice] = field(default_factory=list)
    delay_days: int | None = None
    horizon_end: date | None = None
    record_type: str | None = None
    record_id: str | None = None
    tone: str = "friendly"
    notes: list[str] = field(default_factory=list)


# --- date and duration parsing --------------------------------------------------


def _next_weekday(as_of: date, weekday_index: int) -> date:
    delta = (weekday_index - as_of.weekday()) % 7
    return as_of + timedelta(days=delta)


def parse_duration_days(text: str) -> int | None:
    if _RE_FORTNIGHT.search(text):
        return 14
    m = _RE_DURATION.search(text)
    if not m:
        return None
    qty_raw = m.group(1).lower().replace(" of", "")
    qty = int(qty_raw) if qty_raw.isdigit() else _NUMBER_WORDS.get(qty_raw, None)
    if qty is None:
        return None
    return qty * _UNIT_DAYS[m.group(2).lower()]


def parse_horizon(text: str, ctx: PlannerContext, notes: list[str]) -> date | None:
    """Explicit date, a weekday name, or a payroll reference → horizon end."""
    as_of = ctx.dataset.snapshot.as_of_date
    lowered = text.lower()
    m = _RE_ISO_DATE.search(text)
    if m:
        try:
            d = date.fromisoformat(m.group(1))
        except ValueError:
            d = None
        if d and as_of <= d <= as_of + timedelta(days=MAX_HORIZON_DAYS):
            return d
    for idx, name in enumerate(_WEEKDAYS):
        if re.search(rf"\b{name}\b", lowered):
            d = _next_weekday(as_of, idx)
            qualifier = "next " if re.search(rf"\bnext {name}\b", lowered) else ""
            notes.append(
                f"I read \"{qualifier}{name.capitalize()}\" as {display_date(d.isoformat())}, the first "
                f"{name.capitalize()} on or after the as-of date {display_date(as_of.isoformat())}."
            )
            return d
    if _RE_PAYROLL.search(lowered):
        payroll_dates = [
            ob.expected_payment_date
            for ob in ctx.dataset.obligations
            if ob.status == STATUS_OPEN
            and ob.remaining_amount > 0
            and ob.expected_payment_date is not None
            and ob.expected_payment_date >= as_of
            and _RE_PAYROLL.search(f"{ob.category} {ob.payee_name}")
        ]
        if payroll_dates:
            d = min(payroll_dates)
            notes.append(f"The next payroll payment in the records falls on {display_date(d.isoformat())}.")
            return d
    return None


# --- intent --------------------------------------------------------------------


def _record_reference(text: str, ctx: PlannerContext) -> tuple[str, str] | None:
    for token in _RE_RECORD_ID.findall(text):
        if find_invoice(ctx.dataset, token):
            return RECORD_INVOICE, token
        if find_obligation(ctx.dataset, token):
            return RECORD_OBLIGATION, token
    return None


def interpret(question: str, ctx: PlannerContext) -> Intent:
    text = question.strip()
    notes: list[str] = []
    horizon = parse_horizon(text, ctx, notes) or ctx.horizon_end
    matches = resolve_invoice_reference(ctx.dataset, text)
    active = ctx.active_scenario
    delay = parse_duration_days(text)

    if _RE_UNSUPPORTED.search(text) and not re.search(r"\b(don't|do not|without) send", text, re.I):
        return Intent(K_UNSUPPORTED, notes=notes)

    if _RE_REMINDER.search(text):
        tone = "firm" if _RE_FIRM.search(text) else "friendly"
        if len(matches) == 1:
            return Intent(K_REMINDER, invoice=matches[0], tone=tone, notes=notes)
        if len(matches) > 1:
            return Intent(K_AMBIGUOUS, candidates=matches, notes=notes)
        if active:
            inv = find_invoice(ctx.dataset, active.invoice_id)
            if inv:
                return Intent(K_REMINDER, invoice=inv, tone=tone, notes=notes)
        return Intent(K_NEED_INVOICE, notes=notes)

    if _RE_BASELINE.search(text):
        return Intent(K_CASHFLOW, horizon_end=horizon, notes=notes)

    # "and three weeks?" after a scenario is a follow-up that changes only the delay.
    delay_words = bool(_RE_DELAY.search(text)) or (delay is not None and active is not None)
    ref = _record_reference(text, ctx)
    if _RE_EVIDENCE.search(text) and not delay_words:
        if ref:
            return Intent(K_EVIDENCE, record_type=ref[0], record_id=ref[1], notes=notes)
        return Intent(K_CASHFLOW, horizon_end=horizon, notes=notes)
    if delay_words or (matches and delay is not None) or (matches and active):
        if len(matches) > 1:
            return Intent(K_AMBIGUOUS, candidates=matches, notes=notes)
        invoice = matches[0] if matches else None
        if invoice is None and active:
            invoice = find_invoice(ctx.dataset, active.invoice_id)
        if invoice is None:
            if _RE_OVERDUE.search(text):
                return Intent(K_OVERDUE, notes=notes)
            return Intent(K_NEED_INVOICE, notes=notes)
        if delay is None:
            iso_match = _RE_ISO_DATE.search(text)
            if iso_match and invoice.expected_receipt_date is not None:
                try:
                    target = date.fromisoformat(iso_match.group(1))
                    diff = (target - invoice.expected_receipt_date).days
                    if diff >= 0:
                        delay = diff
                        notes.append(
                            f"Paying on {display_date(target.isoformat())} is {diff} days after the expected "
                            f"receipt date {display_date(invoice.expected_receipt_date.isoformat())}."
                        )
                except ValueError:
                    pass
        if delay is None and active:
            delay = active.delay_days
            notes.append(f"I reused the {delay}-day delay from the previous scenario.")
        if delay is None:
            return Intent(K_NEED_DELAY, invoice=invoice, notes=notes)
        return Intent(K_DELAY, invoice=invoice, delay_days=delay, horizon_end=horizon, notes=notes)

    if _RE_OVERDUE.search(text):
        return Intent(K_OVERDUE, notes=notes)

    if _RE_LIST_INVOICES.search(text):
        return Intent(K_LIST_INVOICES, notes=notes)

    if ref:
        return Intent(K_EVIDENCE, record_type=ref[0], record_id=ref[1], notes=notes)

    return Intent(K_CASHFLOW, horizon_end=horizon, notes=notes)


# --- planning and composing ---------------------------------------------------


def _clarification(intent: Intent, ctx: PlannerContext) -> str:
    if intent.kind == K_UNSUPPORTED:
        return (
            "I can't send messages, move money, or file anything. I can draft a payment reminder "
            "for you to review, or show the cash-flow effect of a late payment. Which would you like?"
        )
    if intent.kind == K_AMBIGUOUS:
        options = "; ".join(
            f"{inv.invoice_id} ({inv.customer_name}, due {display_date(inv.due_date.isoformat())})"
            for inv in intent.candidates
        )
        return f"Which invoice do you mean? It could be: {options}. Please name the invoice ID."
    if intent.kind == K_NEED_INVOICE:
        open_invoices = [
            inv for inv in ctx.dataset.invoices if inv.status == STATUS_OPEN and inv.remaining_amount > 0
        ]
        options = "; ".join(f"{inv.invoice_id} ({inv.customer_name})" for inv in open_invoices)
        return (
            "Which customer or invoice should I use? Open invoices: "
            f"{options or 'none'}. Say, for example, \"Customer A pays two weeks late\"."
        )
    if intent.kind == K_NEED_DELAY:
        assert intent.invoice is not None
        return (
            f"How late would {intent.invoice.customer_name} ({intent.invoice.invoice_id}) pay? "
            "Give a number of days or weeks, or a new payment date."
        )
    return "I did not understand that. Ask about cash flow, a late payment, overdue items, or a reminder."


def plan(intent: Intent) -> tuple[ToolCall, ...]:
    if intent.kind == K_CASHFLOW:
        args = {"horizon_end": intent.horizon_end.isoformat()} if intent.horizon_end else {}
        return (ToolCall("mock-1", TOOL_GET_CASHFLOW, args),)
    if intent.kind == K_DELAY:
        assert intent.invoice is not None and intent.delay_days is not None
        args = {"invoice_id": intent.invoice.invoice_id, "delay_days": intent.delay_days}
        if intent.horizon_end:
            args["horizon_end"] = intent.horizon_end.isoformat()
        return (ToolCall("mock-1", TOOL_SIMULATE_DELAY, args),)
    if intent.kind == K_OVERDUE:
        return (ToolCall("mock-1", TOOL_LIST_OVERDUE, {}),)
    if intent.kind == K_LIST_INVOICES:
        return (ToolCall("mock-1", TOOL_LIST_OPEN_INVOICES, {}),)
    if intent.kind == K_EVIDENCE:
        return (
            ToolCall(
                "mock-1",
                TOOL_GET_EVIDENCE,
                {"record_type": intent.record_type, "record_id": intent.record_id},
            ),
        )
    if intent.kind == K_REMINDER:
        assert intent.invoice is not None
        return (
            ToolCall(
                "mock-1", TOOL_DRAFT_REMINDER, {"invoice_id": intent.invoice.invoice_id, "tone": intent.tone}
            ),
        )
    return ()


class MockProvider:
    name = "mock"
    model_id = MOCK_MODEL_ID
    mode = "mock"

    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_specs: tuple[dict, ...],
        *,
        max_tokens: int,
        timeout: float,
        context: PlannerContext,
    ) -> ModelTurn:
        idx, question = latest_user_text(messages)
        intent = interpret(question, context)
        results = tool_results_after(messages, idx)
        if not results:
            calls = plan(intent)
            if calls:
                return ModelTurn(tool_calls=calls, stop_reason="tool_use")
            text = _clarification(intent, context)
            return ModelTurn(text=f"{text}\n\n{MOCK_FOOTER}", stop_reason="end_turn")
        answer = compose_answer(question, results, intent.notes)
        return ModelTurn(text=f"{answer}\n\n{MOCK_FOOTER}", stop_reason="end_turn")
