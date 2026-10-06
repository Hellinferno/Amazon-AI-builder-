"""Dated baseline forecast: docs/ACCOUNTING_RULES.md and docs/TEST_PLAN.md cases."""

from datetime import date, timedelta

import pytest

from cashflow.dates import MAX_HORIZON_DAYS, DateError
from cashflow.forecast import (
    DIRECTION_INFLOW,
    DIRECTION_OUTFLOW,
    ORIGIN_BASELINE,
    REASON_EXPECTED_DATE_BEFORE_AS_OF,
    REASON_NO_EXPECTED_DATE,
    Movement,
    baseline_movements,
    compute_forecast,
)
from cashflow.money import format_money, parse_money

from conftest import build_dataset

AS_OF = date(2026, 10, 5)
HORIZON = date(2026, 10, 9)


def closing_by_date(forecast):
    return {d.date.isoformat(): format_money(d.closing) for d in forecast.daily}


# --- golden fixture ----------------------------------------------------------


def test_golden_baseline_matches_expected_results(golden_dataset, expected_results):
    forecast = compute_forecast(golden_dataset, date.fromisoformat(expected_results["horizon_end"]))
    expected = expected_results["baseline"]

    assert closing_by_date(forecast) == expected["daily_closing"]
    assert format_money(forecast.closing_cash) == expected["closing_cash"]
    assert forecast.first_negative_date is None
    assert expected["first_negative_date"] is None
    assert format_money(forecast.minimum_balance) == "25000.00"
    assert forecast.minimum_date == date(2026, 10, 9)
    assert forecast.shortfall_below_zero == 0
    assert forecast.unresolved == () and forecast.beyond_horizon == ()
    assert forecast.warnings == ()


def test_golden_daily_inflows_and_outflows(golden_dataset):
    forecast = compute_forecast(golden_dataset, HORIZON)
    rows = [(d.date.day, d.inflows, d.outflows, d.closing) for d in forecast.daily]
    assert rows == [
        (5, 0, 0, 5_000_000),
        (6, 0, 1_000_000, 4_000_000),
        (7, 4_000_000, 0, 8_000_000),
        (8, 0, 0, 8_000_000),
        (9, 1_500_000, 7_000_000, 2_500_000),
    ]


def test_golden_as_dict_is_json_ready(golden_dataset, expected_results):
    payload = compute_forecast(golden_dataset, HORIZON).as_dict()
    assert payload["dataset_version"] == "demo-v1"
    assert payload["as_of_date"] == "2026-10-05"
    assert payload["horizon_end"] == "2026-10-09"
    assert payload["currency"] == "INR"
    assert payload["opening_cash"] == "50000.00"
    assert payload["daily_closing"] == expected_results["baseline"]["daily_closing"]
    assert payload["closing_cash"] == "25000.00"
    assert payload["total_inflows"] == "55000.00"
    assert payload["total_outflows"] == "80000.00"
    assert payload["minimum_balance"] == "25000.00"
    assert payload["minimum_date"] == "2026-10-09"
    assert payload["first_negative_date"] is None
    assert payload["shortfall_below_zero"] == "0.00"
    assert payload["daily"][1] == {
        "date": "2026-10-06",
        "inflows": "0.00",
        "outflows": "10000.00",
        "closing": "40000.00",
    }
    assert [m["record_id"] for m in payload["movements"]] == [
        "BILL-001",
        "INV-001",
        "INV-002",
        "PAY-001",
    ]
    assert payload["beyond_horizon"] == [] and payload["unresolved"] == []
    assert payload["warnings"] == []


# --- provenance --------------------------------------------------------------


def test_every_movement_carries_source_and_assumption(golden_dataset):
    forecast = compute_forecast(golden_dataset, HORIZON)
    inv_001 = next(m for m in forecast.movements if m.record_id == "INV-001")
    assert inv_001.record_type == "invoice"
    assert inv_001.direction == DIRECTION_INFLOW
    assert inv_001.signed_amount == 4_000_000
    assert inv_001.effective_date == date(2026, 10, 7)
    assert inv_001.currency == "INR"
    assert inv_001.dataset_version == "demo-v1"
    assert inv_001.assumption_origin == ORIGIN_BASELINE
    assert (inv_001.source.record_type, inv_001.source.record_id, inv_001.source.row_number) == (
        "invoice",
        "INV-001",
        2,
    )
    assert inv_001.source.source_file_id.startswith("sha256:")

    pay = next(m for m in forecast.movements if m.record_id == "PAY-001")
    assert pay.direction == DIRECTION_OUTFLOW and pay.signed_amount == -7_000_000

    serialized = inv_001.as_dict()
    assert serialized["amount"] == "40000.00"
    assert serialized["source"] == {
        "source_file_id": inv_001.source.source_file_id,
        "row_number": 2,
        "record_type": "invoice",
        "record_id": "INV-001",
    }


# --- horizon boundaries ------------------------------------------------------


def test_as_of_day_and_end_day_movements_count_exactly_once(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=[
            "INV-A,On as-of day,100.00,0.00,2026-10-05,2026-10-05,open,INR",
            "INV-B,On horizon end,200.00,0.00,2026-10-09,2026-10-09,open,INR",
            "INV-C,Day after horizon,400.00,0.00,2026-10-10,2026-10-10,open,INR",
        ],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.daily[0].inflows == 10_000
    assert forecast.daily[-1].inflows == 20_000
    assert forecast.closing_cash == 5_000_000 + 10_000 + 20_000
    assert [m.record_id for m in forecast.movements] == ["INV-A", "INV-B"]
    assert [m.record_id for m in forecast.beyond_horizon] == ["INV-C"]
    assert forecast.warnings == (
        "invoice INV-C: expected on 2026-10-10, after the horizon end 2026-10-09; not counted",
    )


def test_single_day_horizon(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-A,Today,100.00,0.00,2026-10-05,2026-10-05,open,INR"],
        obligations=["BILL-A,Rent,rent,30.00,0.00,2026-10-05,2026-10-05,open,INR"],
    )
    forecast = compute_forecast(dataset, AS_OF)
    assert len(forecast.daily) == 1
    assert forecast.daily[0].closing == 5_000_000 + 10_000 - 3_000
    assert forecast.closing_cash == forecast.minimum_balance


def test_horizon_before_as_of_is_rejected(golden_dataset):
    with pytest.raises(DateError):
        compute_forecast(golden_dataset, AS_OF - timedelta(days=1))


def test_horizon_given_as_a_string_is_rejected_with_date_error(golden_dataset):
    with pytest.raises(DateError):
        compute_forecast(golden_dataset, "2026-10-09")


def test_horizon_cap_is_90_days(golden_dataset):
    assert MAX_HORIZON_DAYS == 90
    at_cap = compute_forecast(golden_dataset, AS_OF + timedelta(days=90))
    assert len(at_cap.daily) == 91
    assert at_cap.daily[-1].date == date(2027, 1, 3)
    with pytest.raises(DateError):
        compute_forecast(golden_dataset, AS_OF + timedelta(days=91))


def test_every_calendar_day_in_horizon_has_a_balance(golden_dataset):
    forecast = compute_forecast(golden_dataset, date(2026, 11, 4))
    dates = [d.date for d in forecast.daily]
    assert dates == [AS_OF + timedelta(days=n) for n in range(31)]
    # Balance holds flat on days without movements.
    assert [d.closing for d in forecast.daily[4:]] == [2_500_000] * 27


# --- settlement and status ---------------------------------------------------


def test_partial_settlement_forecasts_only_the_remainder(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-A,Customer,40000.00,15000.00,2026-10-07,2026-10-07,open,INR"],
        obligations=["BILL-A,Landlord,rent,10000.00,2500.00,2026-10-06,2026-10-06,open,INR"],
    )
    forecast = compute_forecast(dataset, HORIZON)
    amounts = {m.record_id: m.amount for m in forecast.movements}
    assert amounts == {"INV-A": 2_500_000, "BILL-A": 750_000}
    assert forecast.closing_cash == 5_000_000 + 2_500_000 - 750_000


def test_settled_amounts_never_change_opening_cash_or_duplicate_receipts(snapshot):
    """Historical settlements are evidence only: the snapshot already reflects them."""
    dataset = build_dataset(
        snapshot,
        invoices=[
            "INV-A,Customer,40000.00,10000.00,2026-10-07,2026-10-07,open,INR",
            "INV-B,Paid customer,5000.00,5000.00,2026-10-01,,settled,INR",
        ],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.opening_cash == parse_money(snapshot["opening_cash"])
    assert forecast.daily[0].closing == forecast.opening_cash
    assert forecast.total_inflows == 3_000_000
    assert [m.record_id for m in forecast.movements] == ["INV-A"]


@pytest.mark.parametrize(
    "invoice_row, obligation_row",
    [
        (
            "INV-A,Customer,40000.00,40000.00,2026-10-07,2026-10-07,settled,INR",
            "BILL-A,Landlord,rent,10000.00,10000.00,2026-10-06,2026-10-06,settled,INR",
        ),
        (
            "INV-A,Customer,40000.00,0.00,2026-10-07,2026-10-07,cancelled,INR",
            "BILL-A,Landlord,rent,10000.00,2500.00,2026-10-06,2026-10-06,cancelled,INR",
        ),
    ],
)
def test_settled_and_cancelled_items_produce_no_movement(snapshot, invoice_row, obligation_row):
    dataset = build_dataset(snapshot, invoices=[invoice_row], obligations=[obligation_row])
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.movements == () and forecast.unresolved == ()
    assert all(d.closing == 5_000_000 for d in forecast.daily)


def test_no_movements_means_closing_equals_opening_every_day(snapshot):
    forecast = compute_forecast(build_dataset(snapshot), HORIZON)
    assert [d.closing for d in forecast.daily] == [5_000_000] * 5
    assert forecast.total_inflows == 0 and forecast.total_outflows == 0
    assert forecast.minimum_date == AS_OF


# --- unresolved items ----------------------------------------------------------


def test_missing_expected_date_is_excluded_with_warning(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-A,Customer,40000.00,0.00,2026-10-07,,open,INR"],
        obligations=["BILL-A,Landlord,rent,10000.00,0.00,2026-10-06,,open,INR"],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.movements == ()
    assert [(u.record_id, u.reason, u.expected_date) for u in forecast.unresolved] == [
        ("INV-A", REASON_NO_EXPECTED_DATE, None),
        ("BILL-A", REASON_NO_EXPECTED_DATE, None),
    ]
    assert forecast.closing_cash == 5_000_000
    assert forecast.warnings == (
        "invoice INV-A: open item has no expected date; 40000.00 INR excluded from the timed forecast",
        "obligation BILL-A: open item has no expected date; 10000.00 INR excluded from the timed forecast",
    )
    assert forecast.as_dict()["unresolved"][0] == {
        "record_type": "invoice",
        "record_id": "INV-A",
        "direction": "inflow",
        "amount": "40000.00",
        "expected_date": None,
        "reason": REASON_NO_EXPECTED_DATE,
        "source": forecast.unresolved[0].as_dict()["source"],
    }


def test_past_expected_date_is_excluded_not_moved_to_today(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-A,Customer,40000.00,0.00,2026-09-30,2026-10-04,open,INR"],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.movements == ()
    assert forecast.daily[0].inflows == 0
    (item,) = forecast.unresolved
    assert item.reason == REASON_EXPECTED_DATE_BEFORE_AS_OF
    assert item.expected_date == date(2026, 10, 4)
    assert item.amount == 4_000_000


def test_expected_date_on_as_of_is_resolved(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-A,Customer,40000.00,0.00,2026-09-30,2026-10-05,open,INR"],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.unresolved == ()
    assert forecast.daily[0].inflows == 4_000_000


# --- negative balances -------------------------------------------------------


def test_negative_opening_is_negative_on_first_day(snapshot):
    dataset = build_dataset({**snapshot, "opening_cash": "-1000.00"})
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.first_negative_date == AS_OF
    assert forecast.minimum_balance == -100_000
    assert forecast.shortfall_below_zero == 100_000


def test_same_day_inflow_resolves_negative_opening_at_end_of_day(snapshot):
    dataset = build_dataset(
        {**snapshot, "opening_cash": "-1000.00"},
        invoices=["INV-A,Customer,2500.00,0.00,2026-10-05,2026-10-05,open,INR"],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.daily[0].closing == 150_000
    assert forecast.first_negative_date is None
    assert forecast.shortfall_below_zero == 0


def test_first_negative_date_and_shortfall_track_the_lowest_day(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-A,Customer,80000.00,0.00,2026-10-08,2026-10-08,open,INR"],
        obligations=[
            "BILL-A,Landlord,rent,60000.00,0.00,2026-10-06,2026-10-06,open,INR",
            "BILL-B,Supplier,stock,20000.00,0.00,2026-10-07,2026-10-07,open,INR",
        ],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert [d.closing for d in forecast.daily] == [
        5_000_000,
        -1_000_000,
        -3_000_000,
        5_000_000,
        5_000_000,
    ]
    assert forecast.first_negative_date == date(2026, 10, 6)
    assert forecast.minimum_date == date(2026, 10, 7)
    assert forecast.shortfall_below_zero == 3_000_000


def test_minimum_date_is_earliest_day_at_the_minimum(snapshot):
    dataset = build_dataset(
        snapshot,
        obligations=["BILL-A,Landlord,rent,10000.00,0.00,2026-10-06,2026-10-06,open,INR"],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.minimum_balance == 4_000_000
    assert forecast.minimum_date == date(2026, 10, 6)


# --- properties --------------------------------------------------------------


def test_conservation_closing_equals_opening_plus_inflows_minus_outflows(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=[
            "INV-A,Customer,123.45,0.01,2026-10-05,2026-10-05,open,INR",
            "INV-B,Customer,999999.99,0.00,2026-10-07,2026-10-07,open,INR",
            "INV-C,Customer,5.00,0.00,2026-10-20,2026-10-20,open,INR",
        ],
        obligations=[
            "BILL-A,Landlord,rent,0.01,0.00,2026-10-05,2026-10-05,open,INR",
            "BILL-B,Supplier,stock,50000.00,49999.99,2026-10-09,2026-10-09,open,INR",
        ],
    )
    forecast = compute_forecast(dataset, HORIZON)
    assert forecast.closing_cash == (
        forecast.opening_cash + forecast.total_inflows - forecast.total_outflows
    )
    assert forecast.total_inflows == sum(m.amount for m in forecast.movements if m.direction == "inflow")
    assert forecast.total_outflows == sum(m.amount for m in forecast.movements if m.direction == "outflow")
    for previous, current in zip(forecast.daily, forecast.daily[1:]):
        assert current.closing == previous.closing + current.inflows - current.outflows


def test_record_order_does_not_change_results(snapshot):
    invoices = [
        "INV-A,Customer,100.00,0.00,2026-10-07,2026-10-07,open,INR",
        "INV-B,Customer,200.00,0.00,2026-10-07,2026-10-07,open,INR",
        "INV-C,Customer,300.00,0.00,2026-10-06,,open,INR",
    ]
    obligations = [
        "BILL-A,Landlord,rent,50.00,0.00,2026-10-06,2026-10-06,open,INR",
        "BILL-B,Supplier,stock,75.00,0.00,2026-10-09,2026-10-09,open,INR",
    ]
    forward = compute_forecast(build_dataset(snapshot, invoices, obligations), HORIZON)
    reverse = compute_forecast(
        build_dataset(snapshot, invoices[::-1], obligations[::-1]), HORIZON
    )
    assert forward.daily == reverse.daily
    assert [(m.record_id, m.effective_date) for m in forward.movements] == [
        (m.record_id, m.effective_date) for m in reverse.movements
    ]
    assert [u.record_id for u in forward.unresolved] == [u.record_id for u in reverse.unresolved]


def test_same_day_movements_are_aggregated(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=[
            "INV-A,Customer,100.00,0.00,2026-10-07,2026-10-07,open,INR",
            "INV-B,Customer,200.00,0.00,2026-10-07,2026-10-07,open,INR",
        ],
        obligations=["BILL-A,Landlord,rent,50.00,0.00,2026-10-07,2026-10-07,open,INR"],
    )
    day = compute_forecast(dataset, HORIZON).daily[2]
    assert (day.inflows, day.outflows, day.closing) == (30_000, 5_000, 5_000_000 + 25_000)


def test_money_round_trips_without_float_drift(snapshot):
    dataset = build_dataset(
        {**snapshot, "opening_cash": "0.10"},
        invoices=[
            "INV-A,Customer,0.20,0.00,2026-10-05,2026-10-05,open,INR",
            "INV-B,Customer,0.70,0.00,2026-10-05,2026-10-05,open,INR",
        ],
        obligations=["BILL-A,Landlord,rent,0.30,0.00,2026-10-05,2026-10-05,open,INR"],
    )
    payload = compute_forecast(dataset, HORIZON).as_dict()
    assert payload["daily_closing"]["2026-10-05"] == "0.70"  # 0.1 + 0.2 + 0.7 - 0.3 in floats is 0.7000000000000001
    assert payload["total_inflows"] == "0.90"
    assert parse_money(payload["closing_cash"]) == 70


def test_baseline_movements_can_be_computed_without_a_horizon(golden_dataset):
    movements, unresolved = baseline_movements(golden_dataset)
    assert [m.record_id for m in movements] == ["BILL-001", "INV-001", "INV-002", "PAY-001"]
    assert unresolved == ()


def test_movement_before_as_of_is_rejected(golden_dataset):
    movements, unresolved = baseline_movements(golden_dataset)
    bad = Movement(
        record_type="invoice",
        record_id="X",
        direction="inflow",
        amount=1,
        effective_date=AS_OF - timedelta(days=1),
        currency="INR",
        dataset_version="demo-v1",
        assumption_origin="baseline",
        source=movements[0].source,
    )
    with pytest.raises(ValueError, match="before the as-of date"):
        compute_forecast(golden_dataset, HORIZON, movements + (bad,), unresolved)


def test_forecast_results_are_immutable(golden_dataset):
    forecast = compute_forecast(golden_dataset, HORIZON)
    with pytest.raises(AttributeError):
        forecast.opening_cash = 0
    with pytest.raises(AttributeError):
        forecast.daily[0].closing = 0
    with pytest.raises(AttributeError):
        forecast.movements[0].amount = 0
