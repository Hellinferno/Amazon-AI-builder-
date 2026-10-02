"""Dated baseline forecast with running end-of-day balances.

Closing cash on date d = opening cash + expected receipts through d
                       - unpaid obligations through d.

Everything here is pure: the only inputs are an imported ``Dataset`` and an
explicit horizon end. Nothing reads the clock. Every projected movement keeps
its source record so an answer can cite the row it came from.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from .dates import validate_horizon
from .models import (
    RECORD_INVOICE,
    RECORD_OBLIGATION,
    STATUS_OPEN,
    Dataset,
    Invoice,
    Obligation,
    SourceReference,
)
from .money import format_money

DIRECTION_INFLOW = "inflow"
DIRECTION_OUTFLOW = "outflow"
ORIGIN_BASELINE = "baseline"

REASON_NO_EXPECTED_DATE = "open item has no expected date"
REASON_EXPECTED_DATE_BEFORE_AS_OF = "open item's expected date is before the as-of date"


@dataclass(frozen=True)
class Movement:
    """One projected cash movement derived from an open record.

    ``amount`` is the positive remaining amount in paise; the sign comes from
    ``direction``. ``assumption_origin`` is ``"baseline"`` for the record's own
    expected date, or ``"scenario:<scenario_id>"`` when a scenario moved it.
    """

    record_type: str
    record_id: str
    direction: str
    amount: int
    effective_date: date
    currency: str
    dataset_version: str
    assumption_origin: str
    source: SourceReference

    @property
    def signed_amount(self) -> int:
        return self.amount if self.direction == DIRECTION_INFLOW else -self.amount

    def as_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "direction": self.direction,
            "amount": format_money(self.amount),
            "effective_date": self.effective_date.isoformat(),
            "currency": self.currency,
            "dataset_version": self.dataset_version,
            "assumption_origin": self.assumption_origin,
            "source": _source_dict(self.source),
        }


@dataclass(frozen=True)
class UnresolvedItem:
    """An open item with money outstanding that cannot be placed on a date.

    It is excluded from the timed forecast and must be shown to the user; it is
    never silently moved to the as-of date.
    """

    record_type: str
    record_id: str
    direction: str
    amount: int
    expected_date: date | None
    reason: str
    source: SourceReference

    def as_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "direction": self.direction,
            "amount": format_money(self.amount),
            "expected_date": _iso_or_none(self.expected_date),
            "reason": self.reason,
            "source": _source_dict(self.source),
        }


@dataclass(frozen=True)
class DailyBalance:
    """End-of-day figures for one calendar date inside the horizon."""

    date: date
    inflows: int
    outflows: int
    closing: int

    def as_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "inflows": format_money(self.inflows),
            "outflows": format_money(self.outflows),
            "closing": format_money(self.closing),
        }


@dataclass(frozen=True)
class Forecast:
    """Dated balances for the inclusive interval ``[as_of_date, horizon_end]``.

    ``movements`` are the counted movements inside the horizon.
    ``beyond_horizon`` are dated movements after ``horizon_end``; they are not
    counted but are kept so scenarios can report where a receipt went.
    """

    dataset_version: str
    as_of_date: date
    horizon_end: date
    currency: str
    opening_cash: int
    daily: tuple[DailyBalance, ...]
    movements: tuple[Movement, ...]
    beyond_horizon: tuple[Movement, ...]
    unresolved: tuple[UnresolvedItem, ...]

    @property
    def closing_cash(self) -> int:
        return self.daily[-1].closing

    @property
    def total_inflows(self) -> int:
        return sum(d.inflows for d in self.daily)

    @property
    def total_outflows(self) -> int:
        return sum(d.outflows for d in self.daily)

    @property
    def minimum_balance(self) -> int:
        return min(d.closing for d in self.daily)

    @property
    def minimum_date(self) -> date:
        """Earliest date on which the lowest end-of-day balance occurs."""
        return min(self.daily, key=lambda d: (d.closing, d.date)).date

    @property
    def first_negative_date(self) -> date | None:
        for day in self.daily:
            if day.closing < 0:
                return day.date
        return None

    @property
    def shortfall_below_zero(self) -> int:
        """Cash needed at the start of the period to keep every end-of-day balance >= 0."""
        return max(0, -self.minimum_balance)

    @property
    def warnings(self) -> tuple[str, ...]:
        notes = [
            f"{item.record_type} {item.record_id}: {item.reason}; "
            f"{format_money(item.amount)} {self.currency} excluded from the timed forecast"
            for item in self.unresolved
        ]
        notes.extend(
            f"{m.record_type} {m.record_id}: expected on {m.effective_date.isoformat()}, "
            f"after the horizon end {self.horizon_end.isoformat()}; not counted"
            for m in self.beyond_horizon
        )
        return tuple(notes)

    def as_dict(self) -> dict:
        return {
            "dataset_version": self.dataset_version,
            "as_of_date": self.as_of_date.isoformat(),
            "horizon_end": self.horizon_end.isoformat(),
            "currency": self.currency,
            "opening_cash": format_money(self.opening_cash),
            "daily_closing": {d.date.isoformat(): format_money(d.closing) for d in self.daily},
            "daily": [d.as_dict() for d in self.daily],
            "closing_cash": format_money(self.closing_cash),
            "total_inflows": format_money(self.total_inflows),
            "total_outflows": format_money(self.total_outflows),
            "minimum_balance": format_money(self.minimum_balance),
            "minimum_date": self.minimum_date.isoformat(),
            "first_negative_date": _iso_or_none(self.first_negative_date),
            "shortfall_below_zero": format_money(self.shortfall_below_zero),
            "movements": [m.as_dict() for m in self.movements],
            "beyond_horizon": [m.as_dict() for m in self.beyond_horizon],
            "unresolved": [u.as_dict() for u in self.unresolved],
            "warnings": list(self.warnings),
        }


def _source_dict(source: SourceReference) -> dict:
    return {
        "source_file_id": source.source_file_id,
        "row_number": source.row_number,
        "record_type": source.record_type,
        "record_id": source.record_id,
    }


def _iso_or_none(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _record_fields(record: Invoice | Obligation):
    if isinstance(record, Invoice):
        return RECORD_INVOICE, record.invoice_id, DIRECTION_INFLOW, record.expected_receipt_date
    return RECORD_OBLIGATION, record.obligation_id, DIRECTION_OUTFLOW, record.expected_payment_date


def baseline_movements(
    dataset: Dataset,
) -> tuple[tuple[Movement, ...], tuple[UnresolvedItem, ...]]:
    """Derive dated movements from every open record with money outstanding.

    Fully settled and cancelled records produce nothing. Open records with no
    expected date, or one before the as-of date, are returned as unresolved.
    Movements are sorted by (date, record type, record ID) so identical records
    in a different input order give identical results.
    """
    as_of = dataset.snapshot.as_of_date
    version = dataset.snapshot.dataset_version
    movements: list[Movement] = []
    unresolved: list[UnresolvedItem] = []

    for record in (*dataset.invoices, *dataset.obligations):
        if record.status != STATUS_OPEN or record.remaining_amount <= 0:
            continue
        record_type, record_id, direction, expected = _record_fields(record)
        if expected is None or expected < as_of:
            reason = (
                REASON_NO_EXPECTED_DATE if expected is None else REASON_EXPECTED_DATE_BEFORE_AS_OF
            )
            unresolved.append(
                UnresolvedItem(
                    record_type,
                    record_id,
                    direction,
                    record.remaining_amount,
                    expected,
                    reason,
                    record.source,
                )
            )
            continue
        movements.append(
            Movement(
                record_type=record_type,
                record_id=record_id,
                direction=direction,
                amount=record.remaining_amount,
                effective_date=expected,
                currency=record.currency,
                dataset_version=version,
                assumption_origin=ORIGIN_BASELINE,
                source=record.source,
            )
        )

    return tuple(sorted(movements, key=_movement_key)), tuple(
        sorted(unresolved, key=lambda u: (u.record_type, u.record_id))
    )


def _movement_key(m: Movement):
    return (m.effective_date, m.record_type, m.record_id)


def compute_forecast(
    dataset: Dataset,
    horizon_end: date,
    movements: tuple[Movement, ...] | None = None,
    unresolved: tuple[UnresolvedItem, ...] | None = None,
) -> Forecast:
    """Build the dated balance series for ``[as_of_date, horizon_end]``.

    ``movements`` defaults to the baseline movements of the dataset; scenarios
    pass an adjusted tuple instead. Movements dated inside the horizon are
    counted exactly once on their effective date; later ones are retained in
    ``beyond_horizon``. Raises ``DateError`` for an invalid horizon.
    """
    snapshot = dataset.snapshot
    validate_horizon(snapshot.as_of_date, horizon_end)
    if movements is None or unresolved is None:
        base_movements, base_unresolved = baseline_movements(dataset)
        movements = base_movements if movements is None else movements
        unresolved = base_unresolved if unresolved is None else unresolved

    ordered = sorted(movements, key=_movement_key)
    for m in ordered:
        if m.effective_date < snapshot.as_of_date:
            raise ValueError(
                f"movement {m.record_type} {m.record_id} is dated before the as-of date"
            )
    counted = tuple(m for m in ordered if m.effective_date <= horizon_end)
    beyond = tuple(m for m in ordered if m.effective_date > horizon_end)

    inflows_by_date: dict[date, int] = {}
    outflows_by_date: dict[date, int] = {}
    for m in counted:
        bucket = inflows_by_date if m.direction == DIRECTION_INFLOW else outflows_by_date
        bucket[m.effective_date] = bucket.get(m.effective_date, 0) + m.amount

    daily: list[DailyBalance] = []
    balance = snapshot.opening_cash
    day = snapshot.as_of_date
    while day <= horizon_end:
        inflow = inflows_by_date.get(day, 0)
        outflow = outflows_by_date.get(day, 0)
        balance += inflow - outflow
        daily.append(DailyBalance(day, inflow, outflow, balance))
        day += timedelta(days=1)

    return Forecast(
        dataset_version=snapshot.dataset_version,
        as_of_date=snapshot.as_of_date,
        horizon_end=horizon_end,
        currency=snapshot.currency,
        opening_cash=snapshot.opening_cash,
        daily=tuple(daily),
        movements=counted,
        beyond_horizon=beyond,
        unresolved=tuple(unresolved),
    )
