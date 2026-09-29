"""Atomic CSV import.

Every file and every row is validated before anything is committed. A single
invalid row fails the whole import and leaves the previous dataset untouched.
"""

import csv
import hashlib
import io
from collections.abc import Callable
from dataclasses import dataclass

from .models import BusinessSnapshot, Dataset
from .money import format_money
from .validation import (
    FILE_INVOICES,
    FILE_OBLIGATIONS,
    FILE_SNAPSHOT,
    INVOICE_HEADERS,
    OBLIGATION_HEADERS,
    ImportIssue,
    validate_invoice_row,
    validate_obligation_row,
    validate_snapshot,
)

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_DATA_ROWS = 10_000


@dataclass(frozen=True)
class ImportResult:
    """Either a dataset with no errors, or errors with no dataset."""

    dataset: Dataset | None
    errors: tuple[ImportIssue, ...]
    warnings: tuple[ImportIssue, ...]

    @property
    def ok(self) -> bool:
        return self.dataset is not None


def source_file_id(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()[:16]


def _read_rows(
    file: str, content: object, headers: tuple[str, ...]
) -> tuple[list[tuple[int, dict[str, str]]], list[ImportIssue]]:
    """Parse one CSV into (row_number, row) pairs; the header is row 1."""

    def file_error(reason: str):
        return [], [ImportIssue(file, None, None, reason)]

    if not isinstance(content, bytes):
        return file_error("file content must be bytes")
    if len(content) > MAX_FILE_BYTES:
        return file_error(f"file exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB limit")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_error("file is not valid UTF-8")

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows: list[tuple[int, dict[str, str]]] = []
    issues: list[ImportIssue] = []
    found_headers: list[str] | None = None
    try:
        for row_number, cells in enumerate(reader, start=1):
            if found_headers is None:
                found_headers = cells
                header_issues = _check_headers(file, cells, headers)
                if header_issues:
                    return [], header_issues
                continue
            if not cells:
                continue  # blank line
            if len(rows) >= MAX_DATA_ROWS:
                return file_error(f"file exceeds the {MAX_DATA_ROWS} data-row limit")
            if len(cells) != len(found_headers):
                issues.append(
                    ImportIssue(
                        file,
                        row_number,
                        None,
                        f"expected {len(found_headers)} columns, found {len(cells)}",
                    )
                )
                continue
            rows.append((row_number, dict(zip(found_headers, cells))))
    except csv.Error as exc:
        return file_error(f"malformed CSV near line {reader.line_num}: {exc}")

    if found_headers is None:
        return file_error("file is empty; a header row is required")
    return rows, issues


def _check_headers(
    file: str, found: list[str], expected: tuple[str, ...]
) -> list[ImportIssue]:
    issues = []
    for name in dict.fromkeys(found):
        if name not in expected:
            issues.append(ImportIssue(file, 1, name, "unknown header"))
        elif found.count(name) > 1:
            issues.append(ImportIssue(file, 1, name, "duplicate header"))
    for name in expected:
        if name not in found:
            issues.append(ImportIssue(file, 1, name, "required header is missing"))
    return issues


def _validate_file(
    file: str,
    content: object,
    headers: tuple[str, ...],
    id_field: str,
    validate_row: Callable,
    snapshot: BusinessSnapshot,
):
    rows, errors = _read_rows(file, content, headers)
    records, warnings = [], []
    first_row_by_id: dict[str, int] = {}
    file_id = source_file_id(content) if isinstance(content, bytes) else ""
    for row_number, raw in rows:
        record, row_errors, row_warnings = validate_row(
            raw, row_number, snapshot, file_id
        )
        errors.extend(row_errors)
        if record is None:
            continue
        record_id = getattr(record, id_field)
        if record_id in first_row_by_id:
            errors.append(
                ImportIssue(
                    file,
                    row_number,
                    id_field,
                    f"duplicate ID {record_id}; first used on row "
                    f"{first_row_by_id[record_id]}",
                )
            )
            continue
        first_row_by_id[record_id] = row_number
        records.append(record)
        warnings.extend(row_warnings)
    return records, errors, warnings


def _fingerprint(
    snapshot: BusinessSnapshot, invoices_csv: bytes, obligations_csv: bytes
) -> str:
    digest = hashlib.sha256()
    for part in (
        snapshot.business_id,
        snapshot.dataset_version,
        snapshot.currency,
        snapshot.timezone,
        snapshot.as_of_date.isoformat(),
        format_money(snapshot.opening_cash),
        hashlib.sha256(invoices_csv).hexdigest(),
        hashlib.sha256(obligations_csv).hexdigest(),
    ):
        digest.update(part.encode("utf-8") + b"\x00")
    return digest.hexdigest()


def import_dataset(
    snapshot: object, invoices_csv: object, obligations_csv: object
) -> ImportResult:
    """Validate a snapshot and both CSV files; build a dataset only if all pass."""
    validated_snapshot, errors = validate_snapshot(snapshot)
    if validated_snapshot is None:
        # Rows cannot be checked against an invalid snapshot.
        return ImportResult(None, tuple(errors), ())

    invoices, invoice_errors, invoice_warnings = _validate_file(
        FILE_INVOICES,
        invoices_csv,
        INVOICE_HEADERS,
        "invoice_id",
        validate_invoice_row,
        validated_snapshot,
    )
    obligations, obligation_errors, obligation_warnings = _validate_file(
        FILE_OBLIGATIONS,
        obligations_csv,
        OBLIGATION_HEADERS,
        "obligation_id",
        validate_obligation_row,
        validated_snapshot,
    )
    errors = invoice_errors + obligation_errors
    if errors:
        return ImportResult(None, tuple(errors), ())

    dataset = Dataset(
        snapshot=validated_snapshot,
        invoices=tuple(invoices),
        obligations=tuple(obligations),
        fingerprint=_fingerprint(validated_snapshot, invoices_csv, obligations_csv),
    )
    return ImportResult(dataset, (), tuple(invoice_warnings + obligation_warnings))


class DatasetStore:
    """In-memory dataset store with atomic commit and idempotent replay.

    Persistence across restarts is a later milestone; this holds the commit rules.
    """

    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}
        self._current_version: str | None = None

    @property
    def current(self) -> Dataset | None:
        if self._current_version is None:
            return None
        return self._datasets[self._current_version]

    def get(self, dataset_version: str) -> Dataset | None:
        return self._datasets.get(dataset_version)

    def import_dataset(
        self, snapshot: object, invoices_csv: object, obligations_csv: object
    ) -> ImportResult:
        result = import_dataset(snapshot, invoices_csv, obligations_csv)
        if result.dataset is None:
            return result

        version = result.dataset.snapshot.dataset_version
        existing = self._datasets.get(version)
        if existing is not None:
            if existing.fingerprint != result.dataset.fingerprint:
                return ImportResult(
                    None,
                    (
                        ImportIssue(
                            FILE_SNAPSHOT,
                            None,
                            "dataset_version",
                            f"version {version} already exists with different "
                            "content; reimport requires a new dataset_version",
                        ),
                    ),
                    (),
                )
            # Exact replay: keep the stored dataset, create nothing new.
            result = ImportResult(existing, (), result.warnings)
        else:
            self._datasets[version] = result.dataset
        self._current_version = version
        return result
