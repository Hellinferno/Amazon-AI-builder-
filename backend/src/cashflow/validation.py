"""Schema validation for snapshots and imported rows.

Validators never raise on bad input: they return the issues found so an import
can report every problem at once. Imported text is data, never instructions.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from .dates import BUSINESS_TIMEZONE, DateError, parse_date
from .models import (
    RECORD_INVOICE,
    RECORD_OBLIGATION,
    STATUS_OPEN,
    STATUS_SETTLED,
    STATUSES,
    BusinessSnapshot,
    Invoice,
    Obligation,
    SourceReference,
)
from .money import CURRENCY, MoneyError, parse_money

FILE_SNAPSHOT = "snapshot"
FILE_INVOICES = "invoices"
FILE_OBLIGATIONS = "obligations"

SNAPSHOT_FIELDS = (
    "business_id",
    "dataset_version",
    "currency",
    "timezone",
    "as_of_date",
    "opening_cash",
)
INVOICE_HEADERS = (
    "invoice_id",
    "customer_name",
    "total_amount",
    "settled_before_as_of",
    "due_date",
    "expected_receipt_date",
    "status",
    "currency",
)
OBLIGATION_HEADERS = (
    "obligation_id",
    "payee_name",
    "category",
    "total_amount",
    "settled_before_as_of",
    "due_date",
    "expected_payment_date",
    "status",
    "currency",
)

MAX_TEXT_LENGTH = 200
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


@dataclass(frozen=True)
class ImportIssue:
    """One error or warning. ``row_number`` is None for file-level issues."""

    file: str
    row_number: int | None
    field: str | None
    reason: str


class _Collector:
    """Parses fields of one record, accumulating issues instead of raising."""

    def __init__(self, file: str, row_number: int | None, raw: Mapping[str, object]):
        self.file = file
        self.row_number = row_number
        self.raw = raw
        self.issues: list[ImportIssue] = []

    def fail(self, field: str | None, reason: str) -> None:
        self.issues.append(ImportIssue(self.file, self.row_number, field, reason))

    def identifier(self, field: str) -> str | None:
        value = self.raw.get(field)
        if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
            self.fail(
                field,
                "must be 1-64 characters of letters, digits, '.', '_' or '-', "
                "starting with a letter or digit",
            )
            return None
        return value

    def text(self, field: str) -> str | None:
        value = self.raw.get(field)
        if not isinstance(value, str) or not value.strip():
            self.fail(field, "must not be empty")
            return None
        value = value.strip()
        if len(value) > MAX_TEXT_LENGTH:
            self.fail(field, f"must be at most {MAX_TEXT_LENGTH} characters")
            return None
        if any(not ch.isprintable() for ch in value):
            self.fail(field, "must not contain control characters")
            return None
        return value

    def money(self, field: str, *, allow_negative: bool = False) -> int | None:
        try:
            return parse_money(self.raw.get(field), allow_negative=allow_negative)
        except MoneyError as exc:
            self.fail(field, str(exc))
            return None

    def required_date(self, field: str) -> date | None:
        try:
            return parse_date(self.raw.get(field))
        except DateError as exc:
            self.fail(field, str(exc))
            return None

    def optional_date(self, field: str) -> date | None:
        if self.raw.get(field) == "":
            return None
        return self.required_date(field)

    def choice(self, field: str, allowed: tuple[str, ...]) -> str | None:
        value = self.raw.get(field)
        if value not in allowed:
            self.fail(field, f"must be one of: {', '.join(allowed)}")
            return None
        return value  # type: ignore[return-value]


def validate_snapshot(
    raw: object,
) -> tuple[BusinessSnapshot | None, list[ImportIssue]]:
    if not isinstance(raw, Mapping):
        return None, [ImportIssue(FILE_SNAPSHOT, None, None, "snapshot must be an object")]

    c = _Collector(FILE_SNAPSHOT, None, raw)
    for key in raw:
        if key not in SNAPSHOT_FIELDS:
            c.fail(str(key), "unknown field")
    for key in SNAPSHOT_FIELDS:
        if key not in raw:
            c.fail(key, "required field is missing")
    if c.issues:
        return None, c.issues

    business_id = c.identifier("business_id")
    dataset_version = c.identifier("dataset_version")
    currency = c.choice("currency", (CURRENCY,))
    timezone = c.choice("timezone", (BUSINESS_TIMEZONE,))
    as_of_date = c.required_date("as_of_date")
    opening_cash = c.money("opening_cash", allow_negative=True)
    if c.issues:
        return None, c.issues

    return (
        BusinessSnapshot(
            business_id=business_id,
            dataset_version=dataset_version,
            currency=currency,
            timezone=timezone,
            as_of_date=as_of_date,
            opening_cash=opening_cash,
        ),
        [],
    )


def _validate_common(c: _Collector, snapshot_currency: str, expected_field: str):
    """Fields shared by invoices and obligations. Returns None if any are invalid."""
    total = c.money("total_amount")
    settled = c.money("settled_before_as_of")
    due_date = c.required_date("due_date")
    expected_date = c.optional_date(expected_field)
    status = c.choice("status", STATUSES)
    currency = c.choice("currency", (CURRENCY,))

    if currency is not None and currency != snapshot_currency:
        c.fail("currency", f"must match the snapshot currency {snapshot_currency}")
    if total is not None and total == 0:
        c.fail("total_amount", "must be greater than zero")
    if total is not None and settled is not None:
        if settled > total:
            c.fail("settled_before_as_of", "must not exceed total_amount")
        elif status == STATUS_OPEN and settled == total and total > 0:
            c.fail("status", "is open but the item is fully settled; use settled")
        elif status == STATUS_SETTLED and settled != total:
            c.fail("status", "is settled but settled_before_as_of is less than total_amount")

    if c.issues:
        return None
    return total, settled, due_date, expected_date, status, currency


def _timing_warnings(
    c: _Collector, expected_field: str, status: str, expected_date, as_of_date: date
) -> list[ImportIssue]:
    if status != STATUS_OPEN:
        return []
    if expected_date is None:
        reason = "open item has no expected date; excluded from the timed forecast"
    elif expected_date < as_of_date:
        reason = (
            "open item's expected date is before the as-of date; "
            "excluded from the timed forecast as unresolved"
        )
    else:
        return []
    return [ImportIssue(c.file, c.row_number, expected_field, reason)]


def validate_invoice_row(
    raw: Mapping[str, str],
    row_number: int,
    snapshot: BusinessSnapshot,
    source_file_id: str,
) -> tuple[Invoice | None, list[ImportIssue], list[ImportIssue]]:
    """Returns (invoice, errors, warnings)."""
    c = _Collector(FILE_INVOICES, row_number, raw)
    invoice_id = c.identifier("invoice_id")
    customer_name = c.text("customer_name")
    common = _validate_common(c, snapshot.currency, "expected_receipt_date")
    if common is None:
        return None, c.issues, []
    total, settled, due_date, expected_date, status, currency = common

    invoice = Invoice(
        invoice_id=invoice_id,
        customer_name=customer_name,
        total_amount=total,
        settled_before_as_of=settled,
        due_date=due_date,
        expected_receipt_date=expected_date,
        status=status,
        currency=currency,
        source=SourceReference(source_file_id, row_number, RECORD_INVOICE, invoice_id),
    )
    warnings = _timing_warnings(
        c, "expected_receipt_date", status, expected_date, snapshot.as_of_date
    )
    return invoice, [], warnings


def validate_obligation_row(
    raw: Mapping[str, str],
    row_number: int,
    snapshot: BusinessSnapshot,
    source_file_id: str,
) -> tuple[Obligation | None, list[ImportIssue], list[ImportIssue]]:
    """Returns (obligation, errors, warnings)."""
    c = _Collector(FILE_OBLIGATIONS, row_number, raw)
    obligation_id = c.identifier("obligation_id")
    payee_name = c.text("payee_name")
    category = c.text("category")
    common = _validate_common(c, snapshot.currency, "expected_payment_date")
    if common is None:
        return None, c.issues, []
    total, settled, due_date, expected_date, status, currency = common

    obligation = Obligation(
        obligation_id=obligation_id,
        payee_name=payee_name,
        category=category,
        total_amount=total,
        settled_before_as_of=settled,
        due_date=due_date,
        expected_payment_date=expected_date,
        status=status,
        currency=currency,
        source=SourceReference(
            source_file_id, row_number, RECORD_OBLIGATION, obligation_id
        ),
    )
    warnings = _timing_warnings(
        c, "expected_payment_date", status, expected_date, snapshot.as_of_date
    )
    return obligation, [], warnings
