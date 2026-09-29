import codecs

import pytest

from cashflow import importer
from cashflow.importer import DatasetStore, import_dataset, source_file_id

from conftest import INVOICE_HEADER, OBLIGATION_HEADER, csv_bytes

GOOD_INVOICE = "INV-001,Customer A,40000.00,0.00,2026-10-07,2026-10-07,open,INR"
GOOD_INVOICE_2 = "INV-002,Customer B,15000.00,0.00,2026-10-09,2026-10-09,open,INR"


def import_invoices(snapshot, empty_obligations, *rows, header=INVOICE_HEADER):
    return import_dataset(snapshot, csv_bytes(header, *rows), empty_obligations)


def issue_keys(issues):
    return [(i.file, i.row_number, i.field) for i in issues]


# --- parsing ----------------------------------------------------------------


def test_source_references_point_at_file_and_row(
    snapshot, invoices_csv, obligations_csv
):
    dataset = import_dataset(snapshot, invoices_csv, obligations_csv).dataset

    refs = [i.source for i in dataset.invoices] + [o.source for o in dataset.obligations]
    assert [(r.record_type, r.record_id, r.row_number) for r in refs] == [
        ("invoice", "INV-001", 2),
        ("invoice", "INV-002", 3),
        ("obligation", "BILL-001", 2),
        ("obligation", "PAY-001", 3),
    ]
    assert {r.source_file_id for r in refs[:2]} == {source_file_id(invoices_csv)}
    assert {r.source_file_id for r in refs[2:]} == {source_file_id(obligations_csv)}
    assert source_file_id(invoices_csv) != source_file_id(obligations_csv)


def test_utf8_bom_is_accepted(snapshot, invoices_csv, obligations_csv):
    result = import_dataset(snapshot, codecs.BOM_UTF8 + invoices_csv, obligations_csv)
    assert result.ok
    assert [i.invoice_id for i in result.dataset.invoices] == ["INV-001", "INV-002"]


def test_quoted_commas_and_crlf(snapshot, empty_obligations):
    content = (
        INVOICE_HEADER
        + '\r\nINV-001,"Sharma, Gupta & Sons",40000.00,0.00,2026-10-07,2026-10-07,open,INR\r\n'
    ).encode("utf-8")
    result = import_dataset(snapshot, content, empty_obligations)
    assert result.ok
    assert result.dataset.invoices[0].customer_name == "Sharma, Gupta & Sons"


def test_non_ascii_names(snapshot, empty_obligations):
    row = "INV-001,श्री ट्रेडर्स,40000.00,0.00,2026-10-07,2026-10-07,open,INR"
    result = import_invoices(snapshot, empty_obligations, row)
    assert result.ok
    assert result.dataset.invoices[0].customer_name == "श्री ट्रेडर्स"


def test_blank_lines_are_skipped_and_row_numbers_preserved(snapshot, empty_obligations):
    result = import_invoices(snapshot, empty_obligations, GOOD_INVOICE, "", GOOD_INVOICE_2)
    assert result.ok
    assert [i.source.row_number for i in result.dataset.invoices] == [2, 4]


def test_header_order_does_not_matter(snapshot, empty_obligations):
    header = "currency,status,invoice_id,customer_name,total_amount,settled_before_as_of,due_date,expected_receipt_date"
    row = "INR,open,INV-001,Customer A,40000.00,0.00,2026-10-07,2026-10-07"
    result = import_invoices(snapshot, empty_obligations, row, header=header)
    assert result.ok
    assert result.dataset.invoices[0].total_amount == 4_000_000


def test_header_only_files_give_an_empty_dataset(snapshot, empty_obligations):
    result = import_invoices(snapshot, empty_obligations)
    assert result.ok
    assert result.dataset.invoices == () and result.dataset.obligations == ()


def test_empty_expected_date_imports_with_warning(snapshot, empty_obligations):
    row = "INV-001,Customer A,40000.00,0.00,2026-10-07,,open,INR"
    result = import_invoices(snapshot, empty_obligations, row)
    assert result.ok
    assert issue_keys(result.warnings) == [("invoices", 2, "expected_receipt_date")]


# --- rejection --------------------------------------------------------------


def test_unknown_and_missing_headers(snapshot, empty_obligations):
    header = INVOICE_HEADER.replace("customer_name", "customer")
    result = import_invoices(snapshot, empty_obligations, GOOD_INVOICE, header=header)
    assert not result.ok
    assert {(i.field, i.reason) for i in result.errors} == {
        ("customer", "unknown header"),
        ("customer_name", "required header is missing"),
    }


def test_duplicate_header(snapshot, empty_obligations):
    result = import_invoices(
        snapshot, empty_obligations, header=INVOICE_HEADER + ",currency"
    )
    assert [(i.field, i.reason) for i in result.errors] == [("currency", "duplicate header")]


def test_empty_file(snapshot, empty_obligations):
    result = import_dataset(snapshot, b"", empty_obligations)
    assert issue_keys(result.errors) == [("invoices", None, None)]


def test_wrong_column_count(snapshot, empty_obligations):
    result = import_invoices(
        snapshot, empty_obligations, GOOD_INVOICE, GOOD_INVOICE_2 + ",extra", "INV-003,short"
    )
    assert issue_keys(result.errors) == [("invoices", 3, None), ("invoices", 4, None)]


def test_unquoted_comma_in_name_is_a_column_error(snapshot, empty_obligations):
    row = "INV-001,Sharma, Gupta,40000.00,0.00,2026-10-07,2026-10-07,open,INR"
    result = import_invoices(snapshot, empty_obligations, row)
    assert issue_keys(result.errors) == [("invoices", 2, None)]


def test_unterminated_quote(snapshot, empty_obligations):
    row = 'INV-001,"Customer A,40000.00,0.00,2026-10-07,2026-10-07,open,INR'
    result = import_invoices(snapshot, empty_obligations, row)
    assert not result.ok
    assert "malformed CSV" in result.errors[0].reason


def test_invalid_utf8(snapshot, empty_obligations):
    result = import_dataset(snapshot, b"\xff\xfe\x00bad", empty_obligations)
    assert [i.reason for i in result.errors] == ["file is not valid UTF-8"]


def test_content_must_be_bytes(snapshot, empty_obligations):
    result = import_dataset(snapshot, INVOICE_HEADER, empty_obligations)
    assert [i.reason for i in result.errors] == ["file content must be bytes"]


def test_duplicate_ids(snapshot, empty_obligations):
    result = import_invoices(
        snapshot, empty_obligations, GOOD_INVOICE, GOOD_INVOICE_2, GOOD_INVOICE
    )
    assert issue_keys(result.errors) == [("invoices", 4, "invoice_id")]
    assert "first used on row 2" in result.errors[0].reason


def test_same_id_in_different_record_types_is_allowed(snapshot):
    obligations = csv_bytes(
        OBLIGATION_HEADER,
        "INV-001,Office Landlord,rent,10000.00,0.00,2026-10-06,2026-10-06,open,INR",
    )
    result = import_dataset(snapshot, csv_bytes(INVOICE_HEADER, GOOD_INVOICE), obligations)
    assert result.ok


def test_errors_are_collected_across_rows_and_files(snapshot):
    invoices = csv_bytes(
        INVOICE_HEADER,
        GOOD_INVOICE,
        "INV-002,Customer B,15000.005,0.00,2026-10-09,2026-10-09,open,INR",
        "INV-003,Customer C,100.00,200.00,2026-13-09,,open,USD",
    )
    obligations = csv_bytes(
        OBLIGATION_HEADER,
        "PAY-001,Staff Payroll,payroll,70000.00,0.00,2026-10-09,2026-10-09,pending,INR",
    )
    result = import_dataset(snapshot, invoices, obligations)
    assert result.dataset is None
    assert result.warnings == ()
    assert sorted(issue_keys(result.errors)) == [
        ("invoices", 3, "total_amount"),
        ("invoices", 4, "currency"),
        ("invoices", 4, "due_date"),
        ("invoices", 4, "settled_before_as_of"),
        ("obligations", 2, "status"),
    ]


def test_invalid_snapshot_stops_the_import(snapshot, invoices_csv, obligations_csv):
    snapshot["currency"] = "USD"
    result = import_dataset(snapshot, invoices_csv, obligations_csv)
    assert issue_keys(result.errors) == [("snapshot", None, "currency")]


def test_file_size_limit(snapshot, empty_obligations, monkeypatch):
    content = csv_bytes(INVOICE_HEADER, GOOD_INVOICE)
    monkeypatch.setattr(importer, "MAX_FILE_BYTES", len(content) - 1)
    result = import_dataset(snapshot, content, empty_obligations)
    assert not result.ok and "limit" in result.errors[0].reason

    monkeypatch.setattr(importer, "MAX_FILE_BYTES", len(content))
    assert import_dataset(snapshot, content, empty_obligations).ok


def test_real_size_limit_is_5_mb(snapshot, empty_obligations):
    assert importer.MAX_FILE_BYTES == 5 * 1024 * 1024
    oversized = INVOICE_HEADER.encode() + b"\n" * importer.MAX_FILE_BYTES
    result = import_dataset(snapshot, oversized, empty_obligations)
    assert [i.reason for i in result.errors] == ["file exceeds the 5 MB limit"]


def test_row_limit(snapshot, empty_obligations):
    assert importer.MAX_DATA_ROWS == 10_000
    template = "INV-{:05d},Customer,1.00,0.00,2026-10-07,2026-10-07,open,INR"

    rows = [template.format(n) for n in range(importer.MAX_DATA_ROWS)]
    at_limit = import_invoices(snapshot, empty_obligations, *rows)
    assert at_limit.ok and len(at_limit.dataset.invoices) == 10_000

    over = import_invoices(snapshot, empty_obligations, *rows, template.format(10_000))
    assert [i.reason for i in over.errors] == ["file exceeds the 10000 data-row limit"]


# --- atomic commit ----------------------------------------------------------


def test_store_commits_valid_import(snapshot, invoices_csv, obligations_csv):
    store = DatasetStore()
    assert store.current is None
    result = store.import_dataset(snapshot, invoices_csv, obligations_csv)
    assert result.ok
    assert store.current is result.dataset
    assert store.get("demo-v1") is result.dataset


@pytest.mark.parametrize(
    "bad_row",
    [
        "INV-003,Customer C,100.001,0.00,2026-10-09,2026-10-09,open,INR",
        GOOD_INVOICE,  # duplicate ID
    ],
)
def test_invalid_import_leaves_existing_dataset_untouched(
    snapshot, invoices_csv, obligations_csv, bad_row
):
    store = DatasetStore()
    original = store.import_dataset(snapshot, invoices_csv, obligations_csv).dataset

    # The new file has valid rows before the bad one; none of them may land.
    bad_file = csv_bytes(INVOICE_HEADER, GOOD_INVOICE, GOOD_INVOICE_2, bad_row)
    result = store.import_dataset(
        {**snapshot, "dataset_version": "demo-v2"}, bad_file, obligations_csv
    )

    assert not result.ok and result.errors
    assert store.current is original
    assert store.get("demo-v2") is None
    assert [i.invoice_id for i in store.current.invoices] == ["INV-001", "INV-002"]


def test_exact_replay_does_not_duplicate(snapshot, invoices_csv, obligations_csv):
    store = DatasetStore()
    first = store.import_dataset(snapshot, invoices_csv, obligations_csv)
    second = store.import_dataset(snapshot, invoices_csv, obligations_csv)
    assert second.ok
    assert second.dataset is first.dataset
    assert len(store.current.invoices) == 2


def test_changed_content_under_same_version_is_rejected(
    snapshot, invoices_csv, obligations_csv
):
    store = DatasetStore()
    original = store.import_dataset(snapshot, invoices_csv, obligations_csv).dataset

    changed = csv_bytes(INVOICE_HEADER, GOOD_INVOICE)
    result = store.import_dataset(snapshot, changed, obligations_csv)
    assert issue_keys(result.errors) == [("snapshot", None, "dataset_version")]
    assert store.current is original

    changed_cash = {**snapshot, "opening_cash": "1.00"}
    assert not store.import_dataset(changed_cash, invoices_csv, obligations_csv).ok
    assert store.current is original


def test_new_version_becomes_current_and_old_is_retained(
    snapshot, invoices_csv, obligations_csv
):
    store = DatasetStore()
    v1 = store.import_dataset(snapshot, invoices_csv, obligations_csv).dataset
    v2 = store.import_dataset(
        {**snapshot, "dataset_version": "demo-v2"},
        csv_bytes(INVOICE_HEADER, GOOD_INVOICE),
        obligations_csv,
    ).dataset
    assert store.current is v2
    assert store.get("demo-v1") is v1
    assert v1.fingerprint != v2.fingerprint
    assert len(v1.invoices) == 2  # imported datasets are immutable


def test_records_are_immutable(snapshot, invoices_csv, obligations_csv):
    dataset = import_dataset(snapshot, invoices_csv, obligations_csv).dataset
    with pytest.raises(AttributeError):
        dataset.invoices[0].total_amount = 0
    with pytest.raises(AttributeError):
        dataset.snapshot.opening_cash = 0
