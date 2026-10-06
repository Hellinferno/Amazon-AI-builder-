"""Typed, read-only tools over the accounting engine (docs/TOOLS_AND_API.md).

Business identity and the dataset come from the trusted ``ToolContext`` that
the backend builds; a model can never choose them. Every tool validates its
arguments, returns the shared envelope, and cites the records it used. Tools
never read the clock: ``created_at`` and the default horizon come from the
context.
"""

import re
from dataclasses import dataclass
from datetime import date

from cashflow.dates import DateError, parse_date, validate_horizon
from cashflow.forecast import DIRECTION_INFLOW, Forecast, Movement, UnresolvedItem, compute_forecast
from cashflow.models import RECORD_INVOICE, RECORD_OBLIGATION, STATUS_OPEN, Dataset, Invoice, Obligation
from cashflow.money import format_money
from cashflow.overdue import overdue_report
from cashflow.scenario import MAX_DELAY_DAYS, ScenarioError, apply_scenario, define_scenario

from .envelope import (
    E_INVALID_ARGUMENT,
    E_UNKNOWN_INVOICE,
    E_UNKNOWN_RECORD,
    E_UNKNOWN_TOOL,
    ToolError,
    error_envelope,
    evidence_entry,
    iso,
    ok_envelope,
)
from .reminder import TONE_FRIENDLY, TONES, draft_reminder

TOOL_GET_CASHFLOW = "get_cashflow"
TOOL_LIST_OPEN_INVOICES = "list_open_invoices"
TOOL_LIST_OVERDUE = "list_overdue_invoices"
TOOL_SIMULATE_DELAY = "simulate_payment_delay"
TOOL_GET_EVIDENCE = "get_record_evidence"
TOOL_DRAFT_REMINDER = "draft_collection_reminder"

_DATE_SCHEMA = {
    "type": "string",
    "description": "ISO calendar date YYYY-MM-DD in the business timezone",
    "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
}

# JSON-schema tool specifications in the shape used by Bedrock Converse
# (name, description, inputSchema). The orchestrator only allows these names.
TOOL_SPECS: tuple[dict, ...] = (
    {
        "name": TOOL_GET_CASHFLOW,
        "description": (
            "Baseline cash-flow forecast: end-of-day balances from the dataset's as-of date "
            "to horizon_end (inclusive), lowest balance and its date, first negative date, "
            "shortfall, and every counted receipt/payment with its source record."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"horizon_end": _DATE_SCHEMA},
                "required": [],
                "additionalProperties": False,
            }
        },
    },
    {
        "name": TOOL_LIST_OPEN_INVOICES,
        "description": (
            "List open customer invoices with outstanding amounts, due and expected dates. "
            "Use it to resolve a customer name to an invoice ID before simulating a delay."
        ),
        "inputSchema": {
            "json": {"type": "object", "properties": {}, "additionalProperties": False}
        },
    },
    {
        "name": TOOL_LIST_OVERDUE,
        "description": (
            "Open invoices and obligations whose due date is before the as-of date, with "
            "remaining amounts and days overdue."
        ),
        "inputSchema": {
            "json": {"type": "object", "properties": {}, "additionalProperties": False}
        },
    },
    {
        "name": TOOL_SIMULATE_DELAY,
        "description": (
            "What-if: move one open invoice's expected receipt later by delay_days and compare "
            "the scenario forecast with the unchanged baseline over the same horizon."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "string", "description": "Exact invoice ID"},
                    "delay_days": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": MAX_DELAY_DAYS,
                        "description": "Calendar days to delay the receipt",
                    },
                    "horizon_end": _DATE_SCHEMA,
                },
                "required": ["invoice_id", "delay_days"],
                "additionalProperties": False,
            }
        },
    },
    {
        "name": TOOL_GET_EVIDENCE,
        "description": "Source fields and import provenance of one invoice or obligation.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "record_type": {"type": "string", "enum": [RECORD_INVOICE, RECORD_OBLIGATION]},
                    "record_id": {"type": "string"},
                },
                "required": ["record_type", "record_id"],
                "additionalProperties": False,
            }
        },
    },
    {
        "name": TOOL_DRAFT_REMINDER,
        "description": (
            "Draft an editable, UNSENT payment reminder for one open invoice. "
            "This tool cannot send anything."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "string"},
                    "tone": {"type": "string", "enum": list(TONES)},
                },
                "required": ["invoice_id"],
                "additionalProperties": False,
            }
        },
    },
)
TOOL_NAMES: tuple[str, ...] = tuple(spec["name"] for spec in TOOL_SPECS)


@dataclass(frozen=True)
class ToolContext:
    """Trusted context resolved by the backend, never by the model."""

    dataset: Dataset
    default_horizon_end: date
    created_at: str  # ISO 8601 UTC timestamp supplied by the application
    business_name: str = "Demo Business"


# --- argument validation ---------------------------------------------------


def _require_object(arguments: object) -> dict:
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise ToolError(E_INVALID_ARGUMENT, "tool arguments must be an object")
    return arguments


def _reject_unknown(arguments: dict, allowed: tuple[str, ...]) -> None:
    unknown = sorted(set(arguments) - set(allowed))
    if unknown:
        raise ToolError(E_INVALID_ARGUMENT, f"unknown argument(s): {', '.join(unknown)}", unknown[0])


def _horizon(ctx: ToolContext, arguments: dict) -> date:
    raw = arguments.get("horizon_end")
    if raw is None or raw == "":
        return ctx.default_horizon_end
    try:
        horizon = parse_date(raw)
        validate_horizon(ctx.dataset.snapshot.as_of_date, horizon)
    except DateError as exc:
        raise ToolError(E_INVALID_ARGUMENT, f"horizon_end: {exc}", "horizon_end") from None
    return horizon


def _string(arguments: dict, field: str) -> str:
    value = arguments.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ToolError(E_INVALID_ARGUMENT, f"{field} must be a non-empty string", field)
    return value.strip()


def _delay_days(arguments: dict) -> int:
    value = arguments.get("delay_days")
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        value = int(value.strip())
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolError(E_INVALID_ARGUMENT, "delay_days must be a whole number of days", "delay_days")
    if value < 0 or value > MAX_DELAY_DAYS:
        raise ToolError(
            E_INVALID_ARGUMENT, f"delay_days must be between 0 and {MAX_DELAY_DAYS}", "delay_days"
        )
    return value


# --- record lookup ---------------------------------------------------------


def find_invoice(dataset: Dataset, invoice_id: str) -> Invoice | None:
    for inv in dataset.invoices:
        if inv.invoice_id == invoice_id:
            return inv
    return None


def find_obligation(dataset: Dataset, obligation_id: str) -> Obligation | None:
    for ob in dataset.obligations:
        if ob.obligation_id == obligation_id:
            return ob
    return None


def counterparty_of(dataset: Dataset, record_type: str, record_id: str) -> str:
    if record_type == RECORD_INVOICE:
        inv = find_invoice(dataset, record_id)
        return inv.customer_name if inv else ""
    ob = find_obligation(dataset, record_id)
    return ob.payee_name if ob else ""


def resolve_invoice_reference(dataset: Dataset, text: str) -> list[Invoice]:
    """Open invoices mentioned in free text by exact ID or customer name.

    Matching is case-insensitive. The text is treated as data: only equality
    with known IDs or containment of known customer names is tested.
    """
    lowered = text.lower()

    def mentioned(phrase: str) -> bool:
        # Whole-phrase match: "customer a" must not match "customer and".
        return re.search(r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)", lowered) is not None

    by_id = [
        inv for inv in dataset.invoices if inv.status == STATUS_OPEN and mentioned(inv.invoice_id)
    ]
    if by_id:
        return by_id
    return [
        inv
        for inv in dataset.invoices
        if inv.status == STATUS_OPEN and inv.remaining_amount > 0 and mentioned(inv.customer_name)
    ]


# --- serialization helpers ---------------------------------------------------


def _movement_fact(dataset: Dataset, m: Movement) -> dict:
    return {
        "record_type": m.record_type,
        "record_id": m.record_id,
        "counterparty": counterparty_of(dataset, m.record_type, m.record_id),
        "direction": m.direction,
        "amount": format_money(m.amount),
        "effective_date": m.effective_date.isoformat(),
        "assumption_origin": m.assumption_origin,
    }


def _unresolved_fact(dataset: Dataset, u: UnresolvedItem) -> dict:
    return {
        "record_type": u.record_type,
        "record_id": u.record_id,
        "counterparty": counterparty_of(dataset, u.record_type, u.record_id),
        "direction": u.direction,
        "amount": format_money(u.amount),
        "expected_date": iso(u.expected_date),
        "reason": u.reason,
    }


def _forecast_summary(f: Forecast) -> dict:
    return {
        "opening_cash": format_money(f.opening_cash),
        "closing_cash": format_money(f.closing_cash),
        "total_inflows": format_money(f.total_inflows),
        "total_outflows": format_money(f.total_outflows),
        "minimum_balance": format_money(f.minimum_balance),
        "minimum_date": f.minimum_date.isoformat(),
        "first_negative_date": iso(f.first_negative_date),
        "shortfall_below_zero": format_money(f.shortfall_below_zero),
    }


def _forecast_evidence(f: Forecast) -> list[dict]:
    return [evidence_entry(m.source) for m in (*f.movements, *f.beyond_horizon)] + [
        evidence_entry(u.source) for u in f.unresolved
    ]


def _invoice_fact(inv: Invoice, as_of: date) -> dict:
    return {
        "invoice_id": inv.invoice_id,
        "customer_name": inv.customer_name,
        "total_amount": format_money(inv.total_amount),
        "settled_before_as_of": format_money(inv.settled_before_as_of),
        "remaining_amount": format_money(inv.remaining_amount),
        "due_date": inv.due_date.isoformat(),
        "expected_receipt_date": iso(inv.expected_receipt_date),
        "status": inv.status,
        "currency": inv.currency,
        "overdue": inv.status == STATUS_OPEN and inv.remaining_amount > 0 and inv.due_date < as_of,
    }


def _obligation_fact(ob: Obligation) -> dict:
    return {
        "obligation_id": ob.obligation_id,
        "payee_name": ob.payee_name,
        "category": ob.category,
        "total_amount": format_money(ob.total_amount),
        "settled_before_as_of": format_money(ob.settled_before_as_of),
        "remaining_amount": format_money(ob.remaining_amount),
        "due_date": ob.due_date.isoformat(),
        "expected_payment_date": iso(ob.expected_payment_date),
        "status": ob.status,
        "currency": ob.currency,
    }


# --- tools -------------------------------------------------------------------


def get_cashflow(ctx: ToolContext, arguments: dict) -> dict:
    _reject_unknown(arguments, ("horizon_end",))
    horizon = _horizon(ctx, arguments)
    f = compute_forecast(ctx.dataset, horizon)
    facts = {
        "horizon_end": horizon.isoformat(),
        **_forecast_summary(f),
        "daily": [d.as_dict() for d in f.daily],
        "movements": [_movement_fact(ctx.dataset, m) for m in f.movements],
        "beyond_horizon": [_movement_fact(ctx.dataset, m) for m in f.beyond_horizon],
        "unresolved": [_unresolved_fact(ctx.dataset, u) for u in f.unresolved],
    }
    return ok_envelope(
        ctx.dataset,
        tool=TOOL_GET_CASHFLOW,
        facts=facts,
        evidence=_forecast_evidence(f),
        warnings=list(f.warnings),
    )


def list_open_invoices(ctx: ToolContext, arguments: dict) -> dict:
    _reject_unknown(arguments, ())
    as_of = ctx.dataset.snapshot.as_of_date
    open_invoices = [
        inv for inv in ctx.dataset.invoices if inv.status == STATUS_OPEN and inv.remaining_amount > 0
    ]
    open_invoices.sort(key=lambda i: (i.due_date, i.invoice_id))
    facts = {
        "invoices": [_invoice_fact(inv, as_of) for inv in open_invoices],
        "total_outstanding": format_money(sum(i.remaining_amount for i in open_invoices)),
    }
    return ok_envelope(
        ctx.dataset,
        tool=TOOL_LIST_OPEN_INVOICES,
        facts=facts,
        evidence=[evidence_entry(i.source) for i in open_invoices],
        warnings=[],
    )


def list_overdue_invoices(ctx: ToolContext, arguments: dict) -> dict:
    _reject_unknown(arguments, ())
    report = overdue_report(ctx.dataset)
    data = report.as_dict()
    facts = {
        "invoices": data["invoices"],
        "obligations": data["obligations"],
        "total_overdue_receivable": data["total_overdue_receivable"],
        "total_overdue_payable": data["total_overdue_payable"],
    }
    evidence = [evidence_entry(i.source) for i in (*report.invoices, *report.obligations)]
    return ok_envelope(
        ctx.dataset, tool=TOOL_LIST_OVERDUE, facts=facts, evidence=evidence, warnings=[]
    )


def simulate_payment_delay(ctx: ToolContext, arguments: dict) -> dict:
    _reject_unknown(arguments, ("invoice_id", "delay_days", "horizon_end"))
    invoice_id = _string(arguments, "invoice_id")
    delay_days = _delay_days(arguments)
    horizon = _horizon(ctx, arguments)
    invoice = find_invoice(ctx.dataset, invoice_id)
    if invoice is None:
        raise ToolError(E_UNKNOWN_INVOICE, f"invoice {invoice_id} does not exist in this dataset", "invoice_id")
    try:
        scenario = define_scenario(
            ctx.dataset,
            invoice_id,
            delay_days,
            scenario_id=f"sim-{invoice_id}-{delay_days}d",
            created_at=ctx.created_at,
        )
        result = apply_scenario(ctx.dataset, scenario, horizon)
    except ScenarioError as exc:
        raise ToolError(exc.code, str(exc), "invoice_id") from None

    base, scen = result.baseline, result.forecast
    warnings = list(scen.warnings)
    if not result.receipt_within_horizon:
        # Replace the engine's generic beyond-horizon note for this invoice with a fuller one.
        warnings = [w for w in warnings if not w.startswith(f"{RECORD_INVOICE} {invoice_id}:")]
        warnings.append(
            f"The delayed receipt of {format_money(result.shifted_amount)} {scen.currency} from "
            f"{invoice.customer_name} ({invoice_id}) now falls on {result.shifted_date.isoformat()}, "
            f"after the horizon end {horizon.isoformat()}, so it is not counted in the scenario closing cash."
        )
    facts = {
        "invoice_id": invoice_id,
        "customer_name": invoice.customer_name,
        "delay_days": delay_days,
        "original_date": result.original_date.isoformat(),
        "shifted_date": result.shifted_date.isoformat(),
        "shifted_amount": format_money(result.shifted_amount),
        "receipt_within_horizon": result.receipt_within_horizon,
        "horizon_end": horizon.isoformat(),
        "baseline": _forecast_summary(base),
        "scenario": _forecast_summary(scen),
        "difference_from_baseline": format_money(result.difference_from_baseline),
        "daily": [
            {
                "date": b.date.isoformat(),
                "baseline_closing": format_money(b.closing),
                "scenario_closing": format_money(s.closing),
                "difference": format_money(s.closing - b.closing),
            }
            for b, s in zip(base.daily, scen.daily)
        ],
        "scenario_movements": [_movement_fact(ctx.dataset, m) for m in scen.movements],
        "scenario_beyond_horizon": [_movement_fact(ctx.dataset, m) for m in scen.beyond_horizon],
        "unresolved": [_unresolved_fact(ctx.dataset, u) for u in scen.unresolved],
        "scenario_definition": scenario.as_dict(),
    }
    evidence = [evidence_entry(invoice.source)] + _forecast_evidence(scen)
    return ok_envelope(
        ctx.dataset, tool=TOOL_SIMULATE_DELAY, facts=facts, evidence=evidence, warnings=warnings
    )


def get_record_evidence(ctx: ToolContext, arguments: dict) -> dict:
    _reject_unknown(arguments, ("record_type", "record_id"))
    record_type = _string(arguments, "record_type")
    record_id = _string(arguments, "record_id")
    as_of = ctx.dataset.snapshot.as_of_date
    if record_type == RECORD_INVOICE:
        inv = find_invoice(ctx.dataset, record_id)
        if inv is None:
            raise ToolError(E_UNKNOWN_RECORD, f"invoice {record_id} does not exist in this dataset", "record_id")
        facts = {"record_type": record_type, "record": _invoice_fact(inv, as_of)}
        source = inv.source
    elif record_type == RECORD_OBLIGATION:
        ob = find_obligation(ctx.dataset, record_id)
        if ob is None:
            raise ToolError(E_UNKNOWN_RECORD, f"obligation {record_id} does not exist in this dataset", "record_id")
        facts = {"record_type": record_type, "record": _obligation_fact(ob)}
        source = ob.source
    else:
        raise ToolError(
            E_INVALID_ARGUMENT, f"record_type must be {RECORD_INVOICE} or {RECORD_OBLIGATION}", "record_type"
        )
    facts["source"] = evidence_entry(source)
    return ok_envelope(
        ctx.dataset, tool=TOOL_GET_EVIDENCE, facts=facts, evidence=[evidence_entry(source)], warnings=[]
    )


def draft_collection_reminder(ctx: ToolContext, arguments: dict) -> dict:
    _reject_unknown(arguments, ("invoice_id", "tone"))
    invoice_id = _string(arguments, "invoice_id")
    tone = arguments.get("tone") or TONE_FRIENDLY
    if tone not in TONES:
        raise ToolError(E_INVALID_ARGUMENT, f"tone must be one of: {', '.join(TONES)}", "tone")
    invoice = find_invoice(ctx.dataset, invoice_id)
    if invoice is None:
        raise ToolError(E_UNKNOWN_INVOICE, f"invoice {invoice_id} does not exist in this dataset", "invoice_id")
    if invoice.status != STATUS_OPEN or invoice.remaining_amount <= 0:
        raise ToolError(
            E_INVALID_ARGUMENT,
            f"invoice {invoice_id} is {invoice.status} with nothing outstanding; no reminder is needed",
            "invoice_id",
        )
    draft = draft_reminder(invoice, ctx.dataset.snapshot.as_of_date, tone, ctx.business_name)
    facts = {"draft": draft.as_dict(), "invoice": _invoice_fact(invoice, ctx.dataset.snapshot.as_of_date)}
    return ok_envelope(
        ctx.dataset,
        tool=TOOL_DRAFT_REMINDER,
        facts=facts,
        evidence=[evidence_entry(invoice.source)],
        warnings=["This is a draft for review. Nothing has been sent."],
    )


_TOOLS = {
    TOOL_GET_CASHFLOW: get_cashflow,
    TOOL_LIST_OPEN_INVOICES: list_open_invoices,
    TOOL_LIST_OVERDUE: list_overdue_invoices,
    TOOL_SIMULATE_DELAY: simulate_payment_delay,
    TOOL_GET_EVIDENCE: get_record_evidence,
    TOOL_DRAFT_REMINDER: draft_collection_reminder,
}


def run_tool(ctx: ToolContext, name: object, arguments: object) -> dict:
    """Dispatch by name through the allowlist. Never raises; returns an envelope."""
    if not isinstance(name, str) or name not in _TOOLS:
        return error_envelope(
            tool=name if isinstance(name, str) else None,
            code=E_UNKNOWN_TOOL,
            message=f"unknown tool {name!r}; allowed: {', '.join(TOOL_NAMES)}",
            dataset=ctx.dataset,
        )
    try:
        return _TOOLS[name](ctx, _require_object(arguments))
    except ToolError as exc:
        return error_envelope(
            tool=name, code=exc.code, message=exc.message, field=exc.field, dataset=ctx.dataset
        )
