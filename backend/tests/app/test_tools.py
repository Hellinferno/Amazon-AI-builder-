"""Typed tools: golden values, envelope shape, argument validation, allowlist."""

import pytest

from cashflow_app.tools import (
    TOOL_NAMES,
    TOOL_SPECS,
    ToolContext,
    resolve_invoice_reference,
    run_tool,
)

from app.helpers import AS_OF, FIXED_NOW, FRIDAY, make_dataset

ENVELOPE_KEYS = {"status", "tool", "dataset_version", "as_of_date", "currency", "facts", "evidence", "warnings", "error"}


def test_tool_specs_are_well_formed():
    assert set(TOOL_NAMES) == {
        "get_cashflow",
        "list_open_invoices",
        "list_overdue_invoices",
        "simulate_payment_delay",
        "get_record_evidence",
        "draft_collection_reminder",
    }
    for spec in TOOL_SPECS:
        schema = spec["inputSchema"]["json"]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False


def test_get_cashflow_reproduces_golden_baseline(golden_ctx):
    env = run_tool(golden_ctx, "get_cashflow", {"horizon_end": "2026-10-09"})
    assert set(env) == ENVELOPE_KEYS
    assert env["status"] == "ok"
    assert env["dataset_version"] == "demo-v1"
    assert env["as_of_date"] == "2026-10-05"
    assert env["currency"] == "INR"
    f = env["facts"]
    assert f["closing_cash"] == "25000.00"
    assert f["first_negative_date"] is None
    assert [d["closing"] for d in f["daily"]] == ["50000.00", "40000.00", "80000.00", "80000.00", "25000.00"]
    assert {m["record_id"] for m in f["movements"]} == {"INV-001", "INV-002", "BILL-001", "PAY-001"}
    assert {e["record_id"] for e in env["evidence"]} == {"INV-001", "INV-002", "BILL-001", "PAY-001"}
    for e in env["evidence"]:
        assert e["source_file_id"].startswith("sha256:") and e["row_number"] >= 2


def test_get_cashflow_defaults_to_context_horizon(golden_ctx):
    env = run_tool(golden_ctx, "get_cashflow", {})
    assert env["facts"]["horizon_end"] == FRIDAY.isoformat()


def test_simulate_reproduces_golden_delay(golden_ctx):
    env = run_tool(golden_ctx, "simulate_payment_delay", {"invoice_id": "INV-001", "delay_days": 14})
    f = env["facts"]
    assert f["shifted_date"] == "2026-10-21"
    assert f["receipt_within_horizon"] is False
    assert f["scenario"]["closing_cash"] == "-15000.00"
    assert f["baseline"]["closing_cash"] == "25000.00"
    assert f["difference_from_baseline"] == "-40000.00"
    assert f["scenario"]["first_negative_date"] == "2026-10-09"
    assert f["scenario"]["shortfall_below_zero"] == "15000.00"
    assert [d["scenario_closing"] for d in f["daily"]] == ["50000.00", "40000.00", "40000.00", "40000.00", "-15000.00"]
    assert f["scenario_definition"]["created_at"] == FIXED_NOW
    assert env["evidence"][0]["record_id"] == "INV-001"
    assert any("not counted" in w for w in env["warnings"])


def test_simulate_accepts_numeric_string_delay(golden_ctx):
    env = run_tool(golden_ctx, "simulate_payment_delay", {"invoice_id": "INV-001", "delay_days": "14"})
    assert env["status"] == "ok" and env["facts"]["delay_days"] == 14


@pytest.mark.parametrize(
    "arguments, code, field",
    [
        ({"invoice_id": "INV-404", "delay_days": 1}, "unknown_invoice", "invoice_id"),
        ({"invoice_id": "INV-001", "delay_days": -1}, "invalid_argument", "delay_days"),
        ({"invoice_id": "INV-001", "delay_days": 366}, "invalid_argument", "delay_days"),
        ({"invoice_id": "INV-001", "delay_days": 1.5}, "invalid_argument", "delay_days"),
        ({"invoice_id": "INV-001", "delay_days": True}, "invalid_argument", "delay_days"),
        ({"invoice_id": "", "delay_days": 1}, "invalid_argument", "invoice_id"),
        ({"invoice_id": "INV-001", "delay_days": 1, "horizon_end": "2026-10-04"}, "invalid_argument", "horizon_end"),
        ({"invoice_id": "INV-001", "delay_days": 1, "horizon_end": "next friday"}, "invalid_argument", "horizon_end"),
        ({"invoice_id": "INV-001", "delay_days": 1, "extra": 1}, "invalid_argument", "extra"),
        ({"invoice_id": "INV-001"}, "invalid_argument", "delay_days"),
    ],
)
def test_simulate_rejects_bad_arguments(golden_ctx, arguments, code, field):
    env = run_tool(golden_ctx, "simulate_payment_delay", arguments)
    assert env["status"] == "error"
    assert env["facts"] == {} and env["evidence"] == []
    assert env["error"]["code"] == code
    assert env["error"]["field"] == field
    assert env["dataset_version"] == "demo-v1"


def test_unknown_tool_is_rejected(golden_ctx):
    env = run_tool(golden_ctx, "transfer_funds", {"amount": "1.00"})
    assert env["status"] == "error" and env["error"]["code"] == "unknown_tool"
    env = run_tool(golden_ctx, None, {})
    assert env["error"]["code"] == "unknown_tool"


def test_arguments_must_be_an_object(golden_ctx):
    env = run_tool(golden_ctx, "get_cashflow", ["2026-10-09"])
    assert env["error"]["code"] == "invalid_argument"
    assert run_tool(golden_ctx, "get_cashflow", None)["status"] == "ok"


def test_list_open_invoices(golden_ctx):
    env = run_tool(golden_ctx, "list_open_invoices", {})
    ids = [i["invoice_id"] for i in env["facts"]["invoices"]]
    assert ids == ["INV-001", "INV-002"]
    assert env["facts"]["total_outstanding"] == "55000.00"
    assert env["facts"]["invoices"][0]["overdue"] is False


def test_overdue_on_golden_is_empty(golden_ctx):
    env = run_tool(golden_ctx, "list_overdue_invoices", {})
    assert env["facts"]["invoices"] == [] and env["facts"]["obligations"] == []
    assert env["facts"]["total_overdue_receivable"] == "0.00"


def test_overdue_lists_past_due_items(snapshot):
    ds = make_dataset(
        snapshot,
        invoices=["INV-OLD,Late Customer,1000.00,250.00,2026-09-30,2026-10-12,open,INR"],
        obligations=["BILL-OLD,Old Vendor,supplies,500.00,0.00,2026-10-01,,open,INR"],
    )
    ctx = ToolContext(ds, FRIDAY, FIXED_NOW)
    env = run_tool(ctx, "list_overdue_invoices", {})
    inv = env["facts"]["invoices"][0]
    assert inv["record_id"] == "INV-OLD" and inv["remaining_amount"] == "750.00" and inv["days_overdue"] == 5
    assert env["facts"]["obligations"][0]["record_id"] == "BILL-OLD"
    assert {e["record_id"] for e in env["evidence"]} == {"INV-OLD", "BILL-OLD"}


def test_record_evidence_invoice_and_obligation(golden_ctx):
    env = run_tool(golden_ctx, "get_record_evidence", {"record_type": "invoice", "record_id": "INV-001"})
    r = env["facts"]["record"]
    assert r["customer_name"] == "Customer A" and r["remaining_amount"] == "40000.00"
    assert env["facts"]["source"]["row_number"] == 2
    env = run_tool(golden_ctx, "get_record_evidence", {"record_type": "obligation", "record_id": "PAY-001"})
    assert env["facts"]["record"]["category"] == "payroll"
    assert env["facts"]["source"]["row_number"] == 3


@pytest.mark.parametrize(
    "arguments, code",
    [
        ({"record_type": "invoice", "record_id": "NOPE"}, "unknown_record"),
        ({"record_type": "obligation", "record_id": "INV-001"}, "unknown_record"),
        ({"record_type": "bank", "record_id": "INV-001"}, "invalid_argument"),
        ({"record_type": "invoice"}, "invalid_argument"),
    ],
)
def test_record_evidence_errors(golden_ctx, arguments, code):
    assert run_tool(golden_ctx, "get_record_evidence", arguments)["error"]["code"] == code


def test_reminder_draft_is_grounded_and_unsent(golden_ctx):
    env = run_tool(golden_ctx, "draft_collection_reminder", {"invoice_id": "INV-001", "tone": "firm"})
    d = env["facts"]["draft"]
    assert d["sent"] is False and d["status"] == "draft_not_sent"
    assert d["amount_outstanding"] == "40000.00"
    assert "INR 40,000.00" in d["body"] and "Customer A" in d["body"]
    assert "7 October 2026" in d["body"]
    assert d["days_overdue"] == -2
    assert env["warnings"] == ["This is a draft for review. Nothing has been sent."]
    friendly = run_tool(golden_ctx, "draft_collection_reminder", {"invoice_id": "INV-001"})
    assert friendly["facts"]["draft"]["tone"] == "friendly"
    assert friendly["facts"]["draft"]["body"] != d["body"]


def test_reminder_rejects_bad_tone_and_settled_invoice(golden_ctx, snapshot):
    env = run_tool(golden_ctx, "draft_collection_reminder", {"invoice_id": "INV-001", "tone": "angry"})
    assert env["error"]["code"] == "invalid_argument" and env["error"]["field"] == "tone"
    ds = make_dataset(snapshot, invoices=["INV-S,Paid Customer,100.00,100.00,2026-09-01,,settled,INR"])
    env = run_tool(ToolContext(ds, FRIDAY, FIXED_NOW), "draft_collection_reminder", {"invoice_id": "INV-S"})
    assert env["error"]["code"] == "invalid_argument"


def test_reminder_mentions_days_overdue(snapshot):
    ds = make_dataset(snapshot, invoices=["INV-OLD,Late Customer,1000.00,0.00,2026-09-30,2026-10-12,open,INR"])
    env = run_tool(ToolContext(ds, FRIDAY, FIXED_NOW), "draft_collection_reminder", {"invoice_id": "INV-OLD"})
    assert "5 days overdue" in env["facts"]["draft"]["body"]


def test_resolve_invoice_reference_uses_whole_phrases(golden_ctx):
    ds = golden_ctx.dataset
    assert [i.invoice_id for i in resolve_invoice_reference(ds, "customer a pays late")] == ["INV-001"]
    assert [i.invoice_id for i in resolve_invoice_reference(ds, "what if the customer and the bank")] == []
    assert [i.invoice_id for i in resolve_invoice_reference(ds, "inv-002 slips")] == ["INV-002"]
    assert resolve_invoice_reference(ds, "nothing here") == []


def test_tools_never_read_the_clock(golden_ctx):
    """Two runs with the same context are byte-identical."""
    a = run_tool(golden_ctx, "simulate_payment_delay", {"invoice_id": "INV-002", "delay_days": 3})
    b = run_tool(golden_ctx, "simulate_payment_delay", {"invoice_id": "INV-002", "delay_days": 3})
    assert a == b
    assert AS_OF.isoformat() == a["as_of_date"]
