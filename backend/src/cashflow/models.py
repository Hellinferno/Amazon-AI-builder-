"""Validated, immutable domain objects. Field names follow docs/DATA_MODEL.md.

Money fields are integer paise; date fields are business calendar dates.
"""

from dataclasses import dataclass
from datetime import date

STATUS_OPEN = "open"
STATUS_SETTLED = "settled"
STATUS_CANCELLED = "cancelled"
STATUSES = (STATUS_OPEN, STATUS_SETTLED, STATUS_CANCELLED)

RECORD_INVOICE = "invoice"
RECORD_OBLIGATION = "obligation"


@dataclass(frozen=True)
class SourceReference:
    """Import provenance for one record.

    ``row_number`` is the spreadsheet-style row: the header is row 1, so the
    first data row is row 2.
    """

    source_file_id: str
    row_number: int
    record_type: str
    record_id: str


@dataclass(frozen=True)
class BusinessSnapshot:
    business_id: str
    dataset_version: str
    currency: str
    timezone: str
    as_of_date: date
    opening_cash: int


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer_name: str
    total_amount: int
    settled_before_as_of: int
    due_date: date
    expected_receipt_date: date | None
    status: str
    currency: str
    source: SourceReference

    @property
    def remaining_amount(self) -> int:
        return self.total_amount - self.settled_before_as_of


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    payee_name: str
    category: str
    total_amount: int
    settled_before_as_of: int
    due_date: date
    expected_payment_date: date | None
    status: str
    currency: str
    source: SourceReference

    @property
    def remaining_amount(self) -> int:
        return self.total_amount - self.settled_before_as_of


@dataclass(frozen=True)
class Dataset:
    """One committed import. ``fingerprint`` identifies the exact input content."""

    snapshot: BusinessSnapshot
    invoices: tuple[Invoice, ...]
    obligations: tuple[Obligation, ...]
    fingerprint: str
