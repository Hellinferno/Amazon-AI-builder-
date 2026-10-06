"""Shared helpers for the application-layer tests (offline, mock mode)."""

from datetime import date
from pathlib import Path

from cashflow.importer import import_dataset

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "demo-v1"
FIXED_NOW = "2026-10-05T09:00:00Z"
AS_OF = date(2026, 10, 5)
FRIDAY = date(2026, 10, 9)

INVOICE_HEADER = (
    "invoice_id,customer_name,total_amount,settled_before_as_of,"
    "due_date,expected_receipt_date,status,currency"
)
OBLIGATION_HEADER = (
    "obligation_id,payee_name,category,total_amount,settled_before_as_of,"
    "due_date,expected_payment_date,status,currency"
)


def csv_bytes(header: str, *rows: str) -> bytes:
    return "\n".join((header, *rows, "")).encode("utf-8")


def make_dataset(snapshot: dict, invoices=(), obligations=()):
    result = import_dataset(
        snapshot, csv_bytes(INVOICE_HEADER, *invoices), csv_bytes(OBLIGATION_HEADER, *obligations)
    )
    assert result.ok, result.errors
    return result.dataset


def fixed_clock() -> str:
    return FIXED_NOW
