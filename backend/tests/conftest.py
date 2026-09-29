import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "demo-v1"

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


@pytest.fixture
def snapshot() -> dict:
    return json.loads((FIXTURE_DIR / "snapshot.json").read_text(encoding="utf-8"))


@pytest.fixture
def invoices_csv() -> bytes:
    return (FIXTURE_DIR / "invoices.csv").read_bytes()


@pytest.fixture
def obligations_csv() -> bytes:
    return (FIXTURE_DIR / "obligations.csv").read_bytes()


@pytest.fixture
def empty_obligations() -> bytes:
    return csv_bytes(OBLIGATION_HEADER)
