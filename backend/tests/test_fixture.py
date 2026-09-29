"""The golden synthetic fixture loads cleanly and matches ACCOUNTING_RULES.md."""

import json
from datetime import date

from cashflow.importer import import_dataset
from cashflow.money import format_money, parse_money

from conftest import FIXTURE_DIR


def test_fixture_imports_without_errors_or_warnings(
    snapshot, invoices_csv, obligations_csv
):
    result = import_dataset(snapshot, invoices_csv, obligations_csv)
    assert result.errors == ()
    assert result.warnings == ()
    assert result.ok


def test_fixture_matches_golden_table(snapshot, invoices_csv, obligations_csv):
    dataset = import_dataset(snapshot, invoices_csv, obligations_csv).dataset

    assert dataset.snapshot.dataset_version == "demo-v1"
    assert dataset.snapshot.as_of_date == date(2026, 10, 5)
    assert dataset.snapshot.currency == "INR"
    assert dataset.snapshot.timezone == "Asia/Kolkata"
    assert format_money(dataset.snapshot.opening_cash) == "50000.00"

    invoices = {
        i.invoice_id: (i.expected_receipt_date, format_money(i.remaining_amount))
        for i in dataset.invoices
    }
    assert invoices == {
        "INV-001": (date(2026, 10, 7), "40000.00"),
        "INV-002": (date(2026, 10, 9), "15000.00"),
    }
    obligations = {
        o.obligation_id: (o.expected_payment_date, format_money(o.remaining_amount))
        for o in dataset.obligations
    }
    assert obligations == {
        "BILL-001": (date(2026, 10, 6), "10000.00"),
        "PAY-001": (date(2026, 10, 9), "70000.00"),
    }
    assert all(r.status == "open" for r in dataset.invoices + dataset.obligations)


def test_expected_results_are_internally_consistent(
    snapshot, invoices_csv, obligations_csv
):
    """Checks the oracle file's arithmetic only; the forecast engine is not built yet."""
    dataset = import_dataset(snapshot, invoices_csv, obligations_csv).dataset
    expected = json.loads(
        (FIXTURE_DIR / "expected_results.json").read_text(encoding="utf-8")
    )

    inflows = sum(i.remaining_amount for i in dataset.invoices)
    outflows = sum(o.remaining_amount for o in dataset.obligations)
    baseline_closing = dataset.snapshot.opening_cash + inflows - outflows
    assert format_money(baseline_closing) == expected["baseline"]["closing_cash"]

    scenario = expected["scenario_inv_001_delayed_14_days"]
    delayed = next(i for i in dataset.invoices if i.invoice_id == scenario["invoice_id"])
    assert format_money(baseline_closing - delayed.remaining_amount) == scenario["closing_cash"]
    assert parse_money(scenario["difference_from_baseline"], allow_negative=True) == (
        -delayed.remaining_amount
    )
