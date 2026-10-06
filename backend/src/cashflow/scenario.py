"""Delayed-receipt scenario.

A scenario shifts the expected date of one open invoice by a nonnegative
number of calendar days and recomputes the forecast. It never edits the
baseline dataset: the dataset's records are frozen, and the scenario works on
a fresh tuple of movements. A scenario binds to a dataset version; applying it
to a different version raises ``StaleScenarioError`` instead of silently
recomputing against changed records.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .forecast import (
    DIRECTION_INFLOW,
    Forecast,
    Movement,
    baseline_movements,
    compute_forecast,
)
from .models import RECORD_INVOICE, STATUS_OPEN, Dataset, Invoice
from .money import format_money

MAX_DELAY_DAYS = 365

_SCENARIO_ID_MAX_LENGTH = 64


class ScenarioError(ValueError):
    """The scenario cannot be applied. ``code`` is a stable machine-readable key."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class StaleScenarioError(ScenarioError):
    """The scenario was defined against a different dataset version."""

    def __init__(self, scenario_version: str, dataset_version: str):
        super().__init__(
            "stale_dataset",
            f"scenario was defined for dataset version {scenario_version}, "
            f"but the current dataset is {dataset_version}; recompute it explicitly",
        )


@dataclass(frozen=True)
class Scenario:
    """Saved scenario definition. Field names follow docs/DATA_MODEL.md.

    ``created_at`` is an ISO 8601 UTC timestamp supplied by the caller and
    validated by ``define_scenario``; the engine never reads the clock.
    """

    scenario_id: str
    dataset_version: str
    invoice_id: str
    delay_days: int
    created_at: str

    @property
    def assumption_origin(self) -> str:
        return f"scenario:{self.scenario_id}"

    def as_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "dataset_version": self.dataset_version,
            "invoice_id": self.invoice_id,
            "delay_days": self.delay_days,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ScenarioResult:
    """Baseline and scenario forecasts over the same horizon, plus the shift."""

    scenario: Scenario
    baseline: Forecast
    forecast: Forecast
    original_date: date
    shifted_date: date
    shifted_amount: int

    @property
    def receipt_within_horizon(self) -> bool:
        return self.shifted_date <= self.forecast.horizon_end

    @property
    def difference_from_baseline(self) -> int:
        """Scenario closing cash minus baseline closing cash."""
        return self.forecast.closing_cash - self.baseline.closing_cash

    @property
    def daily_difference(self) -> tuple[int, ...]:
        return tuple(
            s.closing - b.closing for s, b in zip(self.forecast.daily, self.baseline.daily)
        )

    def as_dict(self) -> dict:
        return {
            "scenario": self.scenario.as_dict(),
            "dataset_version": self.forecast.dataset_version,
            "as_of_date": self.forecast.as_of_date.isoformat(),
            "horizon_end": self.forecast.horizon_end.isoformat(),
            "currency": self.forecast.currency,
            "invoice_id": self.scenario.invoice_id,
            "delay_days": self.scenario.delay_days,
            "original_date": self.original_date.isoformat(),
            "shifted_date": self.shifted_date.isoformat(),
            "shifted_amount": format_money(self.shifted_amount),
            "receipt_within_horizon": self.receipt_within_horizon,
            "baseline": self.baseline.as_dict(),
            "scenario_forecast": self.forecast.as_dict(),
            "closing_cash": format_money(self.forecast.closing_cash),
            "difference_from_baseline": format_money(self.difference_from_baseline),
            "first_negative_date": (
                None
                if self.forecast.first_negative_date is None
                else self.forecast.first_negative_date.isoformat()
            ),
            "shortfall_below_zero": format_money(self.forecast.shortfall_below_zero),
        }


def _validate_delay_days(delay_days: object) -> int:
    if isinstance(delay_days, bool) or not isinstance(delay_days, int):
        raise ScenarioError("invalid_delay", "delay_days must be a whole number of days")
    if delay_days < 0:
        raise ScenarioError("invalid_delay", "delay_days must not be negative")
    if delay_days > MAX_DELAY_DAYS:
        raise ScenarioError(
            "invalid_delay", f"delay_days must be at most {MAX_DELAY_DAYS}"
        )
    return delay_days


def _validate_created_at(created_at: object) -> str:
    """Require an ISO 8601 timestamp with an explicit UTC offset, e.g. 2026-10-05T09:00:00Z."""
    if isinstance(created_at, str):
        try:
            parsed = datetime.fromisoformat(created_at)
        except ValueError:
            parsed = None
        if parsed is not None and parsed.utcoffset() == timedelta(0):
            return created_at
    raise ScenarioError(
        "invalid_created_at",
        "created_at must be an ISO 8601 UTC timestamp such as 2026-10-05T09:00:00Z",
    )


def _validate_scenario_id(scenario_id: object) -> str:
    if (
        not isinstance(scenario_id, str)
        or not scenario_id.strip()
        or len(scenario_id) > _SCENARIO_ID_MAX_LENGTH
        or any(not ch.isprintable() for ch in scenario_id)
    ):
        raise ScenarioError(
            "invalid_scenario_id",
            f"scenario_id must be 1-{_SCENARIO_ID_MAX_LENGTH} printable characters",
        )
    return scenario_id


def _find_invoice(dataset: Dataset, invoice_id: object) -> Invoice:
    if not isinstance(invoice_id, str):
        raise ScenarioError("unknown_invoice", "invoice_id must be a string")
    for invoice in dataset.invoices:
        if invoice.invoice_id == invoice_id:
            return invoice
    raise ScenarioError(
        "unknown_invoice",
        f"invoice {invoice_id} does not exist in dataset {dataset.snapshot.dataset_version}",
    )


def _shiftable_date(dataset: Dataset, invoice: Invoice) -> date:
    """The baseline date a scenario may move. Mirrors the baseline movement rules."""
    if invoice.status != STATUS_OPEN or invoice.remaining_amount <= 0:
        raise ScenarioError(
            "invoice_not_open",
            f"invoice {invoice.invoice_id} is {invoice.status} with nothing outstanding; "
            "it has no receipt to delay",
        )
    if invoice.expected_receipt_date is None:
        raise ScenarioError(
            "no_base_date",
            f"invoice {invoice.invoice_id} has no expected receipt date; "
            "set one before simulating a delay",
        )
    if invoice.expected_receipt_date < dataset.snapshot.as_of_date:
        raise ScenarioError(
            "base_date_before_as_of",
            f"invoice {invoice.invoice_id} has expected receipt date "
            f"{invoice.expected_receipt_date.isoformat()}, before the as-of date "
            f"{dataset.snapshot.as_of_date.isoformat()}; it is unresolved, not delayable",
        )
    return invoice.expected_receipt_date


def define_scenario(
    dataset: Dataset,
    invoice_id: str,
    delay_days: int,
    *,
    scenario_id: str,
    created_at: str,
) -> Scenario:
    """Validate the inputs against the dataset and return a bound ``Scenario``."""
    invoice = _find_invoice(dataset, invoice_id)
    _shiftable_date(dataset, invoice)
    return Scenario(
        scenario_id=_validate_scenario_id(scenario_id),
        dataset_version=dataset.snapshot.dataset_version,
        invoice_id=invoice.invoice_id,
        delay_days=_validate_delay_days(delay_days),
        created_at=_validate_created_at(created_at),
    )


def apply_scenario(dataset: Dataset, scenario: Scenario, horizon_end: date) -> ScenarioResult:
    """Compute baseline and scenario forecasts for ``scenario`` on ``dataset``.

    Raises ``StaleScenarioError`` if the dataset version differs, and
    ``ScenarioError`` if the invoice is missing, not open, or has no usable
    base date. ``DateError`` propagates for an invalid horizon.
    """
    if scenario.dataset_version != dataset.snapshot.dataset_version:
        raise StaleScenarioError(scenario.dataset_version, dataset.snapshot.dataset_version)
    _validate_scenario_id(scenario.scenario_id)
    _validate_created_at(scenario.created_at)
    delay_days = _validate_delay_days(scenario.delay_days)
    invoice = _find_invoice(dataset, scenario.invoice_id)
    original_date = _shiftable_date(dataset, invoice)
    shifted_date = original_date + timedelta(days=delay_days)

    base_movements, unresolved = baseline_movements(dataset)
    baseline = compute_forecast(dataset, horizon_end, base_movements, unresolved)

    adjusted = tuple(
        _shift(m, shifted_date, scenario.assumption_origin)
        if m.record_type == RECORD_INVOICE and m.record_id == invoice.invoice_id
        else m
        for m in base_movements
    )
    forecast = compute_forecast(dataset, horizon_end, adjusted, unresolved)

    return ScenarioResult(
        scenario=scenario,
        baseline=baseline,
        forecast=forecast,
        original_date=original_date,
        shifted_date=shifted_date,
        shifted_amount=invoice.remaining_amount,
    )


def _shift(movement: Movement, new_date: date, origin: str) -> Movement:
    assert movement.direction == DIRECTION_INFLOW
    return Movement(
        record_type=movement.record_type,
        record_id=movement.record_id,
        direction=movement.direction,
        amount=movement.amount,
        effective_date=new_date,
        currency=movement.currency,
        dataset_version=movement.dataset_version,
        assumption_origin=origin,
        source=movement.source,
    )
