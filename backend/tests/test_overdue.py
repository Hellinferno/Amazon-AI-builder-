"""Overdue reporting: due before as-of with money outstanding."""

from datetime import date

from cashflow.forecast import compute_forecast
from cashflow.overdue import is_overdue, overdue_report

from conftest import build_dataset

HORIZON = date(2026, 10, 9)


def test_golden_fixture_has_nothing_overdue(golden_dataset):
    report = overdue_report(golden_dataset)
    assert report.invoices == () and report.obligations == ()
    assert report.total_overdue_receivable == 0 and report.total_overdue_payable == 0
    assert report.dataset_version == "demo-v1"
    assert report.as_of_date == date(2026, 10, 5)


def test_due_before_as_of_is_overdue_and_due_today_is_not(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=[
            "INV-LATE,Customer A,40000.00,0.00,2026-10-04,2026-10-07,open,INR",
            "INV-TODAY,Customer B,15000.00,0.00,2026-10-05,2026-10-05,open,INR",
            "INV-FUTURE,Customer C,1000.00,0.00,2026-10-06,2026-10-06,open,INR",
        ],
    )
    report = overdue_report(dataset)
    assert [(i.record_id, i.days_overdue) for i in report.invoices] == [("INV-LATE", 1)]
    assert report.total_overdue_receivable == 4_000_000
    assert not is_overdue(dataset.invoices[1], dataset.snapshot.as_of_date)


def test_overdue_invoice_with_future_expected_date_is_still_forecast(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-LATE,Customer A,40000.00,0.00,2026-09-25,2026-10-07,open,INR"],
    )
    (item,) = overdue_report(dataset).invoices
    assert item.days_overdue == 10
    assert item.expected_date == date(2026, 10, 7)

    forecast = compute_forecast(dataset, HORIZON)
    assert [m.record_id for m in forecast.movements] == ["INV-LATE"]
    assert forecast.unresolved == ()


def test_overdue_invoice_without_expected_date_is_overdue_and_unresolved(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-LATE,Customer A,40000.00,0.00,2026-09-25,,open,INR"],
    )
    (item,) = overdue_report(dataset).invoices
    assert item.expected_date is None
    forecast = compute_forecast(dataset, HORIZON)
    assert [u.record_id for u in forecast.unresolved] == ["INV-LATE"]
    assert forecast.movements == ()


def test_settled_and_cancelled_items_are_never_overdue(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=[
            "INV-PAID,Customer A,40000.00,40000.00,2026-09-01,,settled,INR",
            "INV-VOID,Customer B,15000.00,0.00,2026-09-01,,cancelled,INR",
        ],
        obligations=["BILL-PAID,Landlord,rent,10000.00,10000.00,2026-09-01,,settled,INR"],
    )
    report = overdue_report(dataset)
    assert report.invoices == () and report.obligations == ()


def test_partially_settled_overdue_item_reports_the_remainder(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-PART,Customer A,40000.00,30000.00,2026-10-01,,open,INR"],
    )
    (item,) = overdue_report(dataset).invoices
    assert item.remaining_amount == 1_000_000
    assert item.days_overdue == 4


def test_overdue_obligations_are_reported_separately(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-LATE,Customer A,40000.00,0.00,2026-10-01,2026-10-07,open,INR"],
        obligations=[
            "BILL-LATE,Landlord,rent,10000.00,0.00,2026-10-03,2026-10-06,open,INR",
            "BILL-OLDER,Supplier,stock,500.00,0.00,2026-09-30,,open,INR",
            "BILL-TODAY,Utility,power,200.00,0.00,2026-10-05,2026-10-05,open,INR",
        ],
    )
    report = overdue_report(dataset)
    assert [i.record_id for i in report.invoices] == ["INV-LATE"]
    assert [o.record_id for o in report.obligations] == ["BILL-OLDER", "BILL-LATE"]
    assert report.total_overdue_receivable == 4_000_000
    assert report.total_overdue_payable == 1_050_000
    assert report.obligations[0].direction == "outflow"
    assert report.obligations[0].counterparty == "Supplier"


def test_sorted_by_due_date_then_id(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=[
            "INV-B,Customer,10.00,0.00,2026-10-01,,open,INR",
            "INV-A,Customer,10.00,0.00,2026-10-01,,open,INR",
            "INV-C,Customer,10.00,0.00,2026-09-01,,open,INR",
        ],
    )
    assert [i.record_id for i in overdue_report(dataset).invoices] == ["INV-C", "INV-A", "INV-B"]


def test_report_as_dict_uses_decimal_strings_and_sources(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-LATE,Customer A,40000.50,0.00,2026-10-01,2026-10-07,open,INR"],
    )
    payload = overdue_report(dataset).as_dict()
    assert payload["dataset_version"] == "demo-v1"
    assert payload["as_of_date"] == "2026-10-05"
    assert payload["currency"] == "INR"
    assert payload["total_overdue_receivable"] == "40000.50"
    assert payload["total_overdue_payable"] == "0.00"
    (item,) = payload["invoices"]
    assert item["record_id"] == "INV-LATE"
    assert item["counterparty"] == "Customer A"
    assert item["direction"] == "inflow"
    assert item["due_date"] == "2026-10-01"
    assert item["days_overdue"] == 4
    assert item["remaining_amount"] == "40000.50"
    assert item["expected_date"] == "2026-10-07"
    assert item["source"]["row_number"] == 2
    assert item["source"]["record_type"] == "invoice"
