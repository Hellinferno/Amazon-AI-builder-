"""Overdue reporting.

An item is overdue when its due date is before the as-of date and it is still
open with money outstanding. An item due on the as-of date is not overdue.
Overdue status is about the due date only: an overdue invoice may still carry
a future expected receipt date and appear in the timed forecast.
"""

from dataclasses import dataclass
from datetime import date

from .forecast import DIRECTION_INFLOW, DIRECTION_OUTFLOW, _iso_or_none, _source_dict
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


@dataclass(frozen=True)
class OverdueItem:
    record_type: str
    record_id: str
    counterparty: str
    direction: str
    due_date: date
    days_overdue: int
    remaining_amount: int
    expected_date: date | None
    currency: str
    source: SourceReference

    def as_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "counterparty": self.counterparty,
            "direction": self.direction,
            "due_date": self.due_date.isoformat(),
            "days_overdue": self.days_overdue,
            "remaining_amount": format_money(self.remaining_amount),
            "expected_date": _iso_or_none(self.expected_date),
            "currency": self.currency,
            "source": _source_dict(self.source),
        }


@dataclass(frozen=True)
class OverdueReport:
    dataset_version: str
    as_of_date: date
    currency: str
    invoices: tuple[OverdueItem, ...]
    obligations: tuple[OverdueItem, ...]

    @property
    def total_overdue_receivable(self) -> int:
        return sum(i.remaining_amount for i in self.invoices)

    @property
    def total_overdue_payable(self) -> int:
        return sum(o.remaining_amount for o in self.obligations)

    def as_dict(self) -> dict:
        return {
            "dataset_version": self.dataset_version,
            "as_of_date": self.as_of_date.isoformat(),
            "currency": self.currency,
            "invoices": [i.as_dict() for i in self.invoices],
            "obligations": [o.as_dict() for o in self.obligations],
            "total_overdue_receivable": format_money(self.total_overdue_receivable),
            "total_overdue_payable": format_money(self.total_overdue_payable),
        }


def is_overdue(record: Invoice | Obligation, as_of_date: date) -> bool:
    return (
        record.status == STATUS_OPEN
        and record.remaining_amount > 0
        and record.due_date < as_of_date
    )


def _item(record: Invoice | Obligation, as_of_date: date) -> OverdueItem:
    if isinstance(record, Invoice):
        record_type, record_id = RECORD_INVOICE, record.invoice_id
        counterparty, direction = record.customer_name, DIRECTION_INFLOW
        expected = record.expected_receipt_date
    else:
        record_type, record_id = RECORD_OBLIGATION, record.obligation_id
        counterparty, direction = record.payee_name, DIRECTION_OUTFLOW
        expected = record.expected_payment_date
    return OverdueItem(
        record_type=record_type,
        record_id=record_id,
        counterparty=counterparty,
        direction=direction,
        due_date=record.due_date,
        days_overdue=(as_of_date - record.due_date).days,
        remaining_amount=record.remaining_amount,
        expected_date=expected,
        currency=record.currency,
        source=record.source,
    )


def overdue_report(dataset: Dataset) -> OverdueReport:
    """List open past-due invoices and obligations, oldest due date first."""
    as_of = dataset.snapshot.as_of_date
    invoices = [_item(i, as_of) for i in dataset.invoices if is_overdue(i, as_of)]
    obligations = [_item(o, as_of) for o in dataset.obligations if is_overdue(o, as_of)]
    order = lambda item: (item.due_date, item.record_id)  # noqa: E731
    return OverdueReport(
        dataset_version=dataset.snapshot.dataset_version,
        as_of_date=as_of,
        currency=dataset.snapshot.currency,
        invoices=tuple(sorted(invoices, key=order)),
        obligations=tuple(sorted(obligations, key=order)),
    )
