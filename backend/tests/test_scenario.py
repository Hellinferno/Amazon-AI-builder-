"""Delayed-receipt scenario: immutable baseline, version binding, boundaries."""

from datetime import date, timedelta

import pytest

from cashflow.dates import DateError
from cashflow.forecast import ORIGIN_BASELINE, compute_forecast
from cashflow.money import format_money
from cashflow.scenario import (
    MAX_DELAY_DAYS,
    Scenario,
    ScenarioError,
    StaleScenarioError,
    apply_scenario,
    define_scenario,
)

from conftest import build_dataset

AS_OF = date(2026, 10, 5)
HORIZON = date(2026, 10, 9)
CREATED_AT = "2026-10-05T09:00:00Z"


def scenario_for(dataset, invoice_id="INV-001", delay_days=14, scenario_id="scn-1"):
    return define_scenario(
        dataset, invoice_id, delay_days, scenario_id=scenario_id, created_at=CREATED_AT
    )


def closing_by_date(forecast):
    return {d.date.isoformat(): format_money(d.closing) for d in forecast.daily}


# --- golden fixture ----------------------------------------------------------


def test_inv_001_delayed_14_days_matches_expected_results(golden_dataset, expected_results):
    expected = expected_results["scenario_inv_001_delayed_14_days"]
    scenario = scenario_for(golden_dataset, expected["invoice_id"], expected["delay_days"])
    result = apply_scenario(golden_dataset, scenario, HORIZON)

    assert result.original_date == date(2026, 10, 7)
    assert result.shifted_date.isoformat() == expected["shifted_date"]
    assert result.shifted_amount == 4_000_000
    assert result.receipt_within_horizon is False
    assert closing_by_date(result.forecast) == expected["daily_closing"]
    assert format_money(result.forecast.closing_cash) == expected["closing_cash"]
    assert format_money(result.difference_from_baseline) == expected["difference_from_baseline"]
    assert result.forecast.first_negative_date.isoformat() == expected["first_negative_date"]
    assert format_money(result.forecast.shortfall_below_zero) == expected["shortfall_below_zero"]
    assert result.forecast.minimum_balance == -1_500_000
    assert result.forecast.minimum_date == date(2026, 10, 9)

    # The baseline inside the result is the untouched golden baseline.
    assert closing_by_date(result.baseline) == expected_results["baseline"]["daily_closing"]
    assert result.baseline.first_negative_date is None


def test_shifted_receipt_beyond_horizon_is_retained_in_metadata(golden_dataset):
    result = apply_scenario(golden_dataset, scenario_for(golden_dataset), HORIZON)
    assert [m.record_id for m in result.forecast.movements] == ["BILL-001", "INV-002", "PAY-001"]
    (moved,) = result.forecast.beyond_horizon
    assert moved.record_id == "INV-001"
    assert moved.effective_date == date(2026, 10, 21)
    assert moved.amount == 4_000_000
    assert moved.assumption_origin == "scenario:scn-1"
    assert moved.source.row_number == 2
    assert result.forecast.warnings == (
        "invoice INV-001: expected on 2026-10-21, after the horizon end 2026-10-09; not counted",
    )


def test_golden_scenario_as_dict(golden_dataset, expected_results):
    expected = expected_results["scenario_inv_001_delayed_14_days"]
    payload = apply_scenario(golden_dataset, scenario_for(golden_dataset), HORIZON).as_dict()
    assert payload["scenario"] == {
        "scenario_id": "scn-1",
        "dataset_version": "demo-v1",
        "invoice_id": "INV-001",
        "delay_days": 14,
        "created_at": CREATED_AT,
    }
    assert payload["dataset_version"] == "demo-v1"
    assert payload["as_of_date"] == "2026-10-05"
    assert payload["currency"] == "INR"
    assert payload["original_date"] == "2026-10-07"
    assert payload["shifted_date"] == expected["shifted_date"]
    assert payload["shifted_amount"] == "40000.00"
    assert payload["receipt_within_horizon"] is False
    assert payload["closing_cash"] == expected["closing_cash"]
    assert payload["difference_from_baseline"] == expected["difference_from_baseline"]
    assert payload["first_negative_date"] == expected["first_negative_date"]
    assert payload["shortfall_below_zero"] == expected["shortfall_below_zero"]
    assert payload["baseline"]["daily_closing"] == expected_results["baseline"]["daily_closing"]
    assert payload["scenario_forecast"]["daily_closing"] == expected["daily_closing"]


# --- delay boundaries ----------------------------------------------------------


def test_zero_day_delay_gives_identical_dated_balances(golden_dataset):
    result = apply_scenario(golden_dataset, scenario_for(golden_dataset, delay_days=0), HORIZON)
    assert result.forecast.daily == result.baseline.daily
    assert result.difference_from_baseline == 0
    assert result.daily_difference == (0, 0, 0, 0, 0)
    assert result.shifted_date == result.original_date
    # The movement is still labelled as a scenario assumption, not baseline data.
    moved = next(m for m in result.forecast.movements if m.record_id == "INV-001")
    assert moved.assumption_origin == "scenario:scn-1"
    assert all(
        m.assumption_origin == ORIGIN_BASELINE for m in result.baseline.movements
    )


def test_delay_within_horizon_moves_the_receipt_but_not_the_closing(golden_dataset):
    result = apply_scenario(golden_dataset, scenario_for(golden_dataset, delay_days=1), HORIZON)
    assert result.shifted_date == date(2026, 10, 8)
    assert result.receipt_within_horizon is True
    assert [d.closing for d in result.forecast.daily] == [
        5_000_000,
        4_000_000,
        4_000_000,
        8_000_000,
        2_500_000,
    ]
    assert result.difference_from_baseline == 0
    assert result.daily_difference == (0, 0, -4_000_000, 0, 0)


def test_delay_to_the_horizon_end_is_still_counted(golden_dataset):
    result = apply_scenario(golden_dataset, scenario_for(golden_dataset, delay_days=2), HORIZON)
    assert result.shifted_date == HORIZON
    assert result.receipt_within_horizon is True
    assert result.forecast.closing_cash == 2_500_000
    assert result.forecast.daily[-1].inflows == 5_500_000


def test_delay_one_day_past_the_horizon_removes_the_receipt(golden_dataset):
    result = apply_scenario(golden_dataset, scenario_for(golden_dataset, delay_days=3), HORIZON)
    assert result.shifted_date == HORIZON + timedelta(days=1)
    assert result.receipt_within_horizon is False
    assert result.forecast.closing_cash == -1_500_000
    assert result.difference_from_baseline == -4_000_000


def test_partially_settled_invoice_delays_only_the_remainder(snapshot):
    dataset = build_dataset(
        snapshot,
        invoices=["INV-A,Customer,40000.00,15000.00,2026-10-07,2026-10-07,open,INR"],
    )
    result = apply_scenario(dataset, scenario_for(dataset, "INV-A", 30), HORIZON)
    assert result.shifted_amount == 2_500_000
    assert result.difference_from_baseline == -2_500_000
    assert result.forecast.closing_cash == 5_000_000


def test_other_records_are_untouched_by_the_scenario(golden_dataset):
    result = apply_scenario(golden_dataset, scenario_for(golden_dataset), HORIZON)
    others = lambda f: [  # noqa: E731
        (m.record_id, m.effective_date, m.amount, m.assumption_origin)
        for m in f.movements
        if m.record_id != "INV-001"
    ]
    assert others(result.forecast) == others(result.baseline)


# --- immutability --------------------------------------------------------------


def test_scenario_never_edits_the_dataset(golden_dataset):
    before = [(i.invoice_id, i.expected_receipt_date, i.status) for i in golden_dataset.invoices]
    baseline_before = compute_forecast(golden_dataset, HORIZON)

    apply_scenario(golden_dataset, scenario_for(golden_dataset), HORIZON)

    after = [(i.invoice_id, i.expected_receipt_date, i.status) for i in golden_dataset.invoices]
    assert after == before
    assert compute_forecast(golden_dataset, HORIZON) == baseline_before
    with pytest.raises(AttributeError):
        golden_dataset.invoices[0].expected_receipt_date = date(2026, 10, 21)


def test_scenarios_do_not_affect_each_other(golden_dataset):
    long_delay = scenario_for(golden_dataset, delay_days=14, scenario_id="long")
    short_delay = scenario_for(golden_dataset, "INV-002", 1, scenario_id="short")

    first = apply_scenario(golden_dataset, long_delay, HORIZON)
    second = apply_scenario(golden_dataset, short_delay, HORIZON)
    first_again = apply_scenario(golden_dataset, long_delay, HORIZON)

    assert first.forecast.daily == first_again.forecast.daily
    assert first.baseline.daily == second.baseline.daily
    assert second.forecast.closing_cash == 1_000_000  # INV-002 moved past the horizon
    assert first.forecast.closing_cash == -1_500_000


def test_scenario_and_result_are_immutable(golden_dataset):
    scenario = scenario_for(golden_dataset)
    result = apply_scenario(golden_dataset, scenario, HORIZON)
    with pytest.raises(AttributeError):
        scenario.delay_days = 0
    with pytest.raises(AttributeError):
        result.shifted_date = AS_OF


# --- dataset version binding -----------------------------------------------------


def test_scenario_binds_to_dataset_version(golden_dataset):
    scenario = scenario_for(golden_dataset)
    assert scenario.dataset_version == "demo-v1"
    assert scenario.created_at == CREATED_AT
    assert scenario.assumption_origin == "scenario:scn-1"


def test_stale_scenario_is_rejected_on_a_changed_dataset(snapshot, golden_dataset):
    scenario = scenario_for(golden_dataset)
    changed = build_dataset(
        {**snapshot, "dataset_version": "demo-v2"},
        invoices=["INV-001,Customer A,40000.00,0.00,2026-10-07,2026-10-07,open,INR"],
    )
    with pytest.raises(StaleScenarioError) as info:
        apply_scenario(changed, scenario, HORIZON)
    assert info.value.code == "stale_dataset"
    assert "demo-v1" in str(info.value) and "demo-v2" in str(info.value)
    assert isinstance(info.value, ScenarioError)


def test_explicit_recompute_on_new_version_creates_a_new_scenario(snapshot, golden_dataset):
    old = scenario_for(golden_dataset)
    changed = build_dataset(
        {**snapshot, "dataset_version": "demo-v2"},
        invoices=["INV-001,Customer A,40000.00,20000.00,2026-10-07,2026-10-07,open,INR"],
    )
    recomputed = define_scenario(
        changed, old.invoice_id, old.delay_days, scenario_id="scn-2", created_at=CREATED_AT
    )
    assert recomputed.dataset_version == "demo-v2"
    result = apply_scenario(changed, recomputed, HORIZON)
    assert result.shifted_amount == 2_000_000


# --- rejected inputs ---------------------------------------------------------------


def error_code(func, *args, **kwargs):
    with pytest.raises(ScenarioError) as info:
        func(*args, **kwargs)
    return info.value.code


def test_unknown_invoice(golden_dataset):
    assert error_code(scenario_for, golden_dataset, "INV-999") == "unknown_invoice"
    assert error_code(scenario_for, golden_dataset, "BILL-001") == "unknown_invoice"
    assert error_code(scenario_for, golden_dataset, 1) == "unknown_invoice"


def test_obligation_sharing_an_invoice_id_is_not_confused_with_it(snapshot):
    dataset = build_dataset(
        snapshot,
        obligations=["INV-001,Office Landlord,rent,10000.00,0.00,2026-10-06,2026-10-06,open,INR"],
    )
    assert error_code(scenario_for, dataset, "INV-001") == "unknown_invoice"


@pytest.mark.parametrize(
    "row",
    [
        "INV-A,Customer,40000.00,40000.00,2026-10-07,2026-10-07,settled,INR",
        "INV-A,Customer,40000.00,0.00,2026-10-07,2026-10-07,cancelled,INR",
    ],
)
def test_settled_or_cancelled_invoice_cannot_be_delayed(snapshot, row):
    dataset = build_dataset(snapshot, invoices=[row])
    assert error_code(scenario_for, dataset, "INV-A") == "invoice_not_open"


def test_invoice_without_expected_date_cannot_be_delayed(snapshot):
    dataset = build_dataset(snapshot, invoices=["INV-A,Customer,40000.00,0.00,2026-10-07,,open,INR"])
    assert error_code(scenario_for, dataset, "INV-A") == "no_base_date"


def test_invoice_with_past_expected_date_cannot_be_delayed(snapshot):
    dataset = build_dataset(
        snapshot, invoices=["INV-A,Customer,40000.00,0.00,2026-09-30,2026-10-04,open,INR"]
    )
    assert error_code(scenario_for, dataset, "INV-A") == "base_date_before_as_of"


@pytest.mark.parametrize("delay", [-1, 1.5, "14", True, None, MAX_DELAY_DAYS + 1])
def test_invalid_delay_days(golden_dataset, delay):
    assert error_code(scenario_for, golden_dataset, "INV-001", delay) == "invalid_delay"


def test_maximum_delay_is_accepted(golden_dataset):
    result = apply_scenario(
        golden_dataset, scenario_for(golden_dataset, delay_days=MAX_DELAY_DAYS), HORIZON
    )
    assert result.shifted_date == date(2026, 10, 7) + timedelta(days=365)


@pytest.mark.parametrize("scenario_id", ["", " ", "x" * 65, "bad\nid", 7])
def test_invalid_scenario_id(golden_dataset, scenario_id):
    assert (
        error_code(scenario_for, golden_dataset, "INV-001", 14, scenario_id)
        == "invalid_scenario_id"
    )


@pytest.mark.parametrize(
    "created_at",
    [
        None,
        123,
        "",
        "yesterday",
        "2026-10-05",  # date only, no time or offset
        "2026-10-05T09:00:00",  # naive: no UTC offset
        "2026-10-05T09:00:00+05:30",  # explicit but not UTC
        "2026-13-05T09:00:00Z",  # not a real calendar date
    ],
)
def test_invalid_created_at(golden_dataset, created_at):
    with pytest.raises(ScenarioError) as info:
        define_scenario(golden_dataset, "INV-001", 14, scenario_id="scn-1", created_at=created_at)
    assert info.value.code == "invalid_created_at"


@pytest.mark.parametrize(
    "created_at", ["2026-10-05T09:00:00Z", "2026-10-05T09:00:00+00:00", "2026-10-05T09:00:00.250Z"]
)
def test_created_at_accepts_utc_timestamps_verbatim(golden_dataset, created_at):
    scenario = define_scenario(
        golden_dataset, "INV-001", 14, scenario_id="scn-1", created_at=created_at
    )
    assert scenario.created_at == created_at


def test_apply_revalidates_a_hand_built_scenario(golden_dataset):
    forged = Scenario("scn-x", "demo-v1", "INV-001", -5, CREATED_AT)
    assert error_code(apply_scenario, golden_dataset, forged, HORIZON) == "invalid_delay"
    missing = Scenario("scn-y", "demo-v1", "INV-404", 5, CREATED_AT)
    assert error_code(apply_scenario, golden_dataset, missing, HORIZON) == "unknown_invoice"
    undated = Scenario("scn-z", "demo-v1", "INV-001", 5, "yesterday")
    assert error_code(apply_scenario, golden_dataset, undated, HORIZON) == "invalid_created_at"


def test_invalid_horizon_propagates(golden_dataset):
    scenario = scenario_for(golden_dataset)
    with pytest.raises(DateError):
        apply_scenario(golden_dataset, scenario, AS_OF - timedelta(days=1))
    with pytest.raises(DateError):
        apply_scenario(golden_dataset, scenario, AS_OF + timedelta(days=91))
    with pytest.raises(DateError):
        apply_scenario(golden_dataset, scenario, "2026-10-09")
