"""Response envelope shared by tools and the HTTP API (docs/TOOLS_AND_API.md).

Every financial result carries ``dataset_version``, ``as_of_date`` and
``currency``. Money is a two-decimal string. Evidence entries point at a
record and its import source. A tool error never carries invented facts.
"""

from dataclasses import dataclass
from datetime import date

from cashflow.models import Dataset, SourceReference

STATUS_OK = "ok"
STATUS_ERROR = "error"

# Stable error codes used by tools, the orchestrator and the API.
E_INVALID_ARGUMENT = "invalid_argument"
E_UNKNOWN_TOOL = "unknown_tool"
E_UNKNOWN_RECORD = "unknown_record"
E_UNKNOWN_INVOICE = "unknown_invoice"
E_STALE_DATASET = "stale_dataset"
E_NO_DATASET = "no_dataset"
E_PROVIDER = "provider_error"
E_PROVIDER_TIMEOUT = "provider_timeout"
E_TOOL_LIMIT = "tool_limit_exceeded"
E_UNGROUNDED = "ungrounded_answer"
E_UNSUPPORTED_ACTION = "unsupported_action"
E_AMBIGUOUS = "ambiguous_reference"


@dataclass(frozen=True)
class ToolError(Exception):
    """Raised inside a tool; converted to an error envelope by ``run_tool``."""

    code: str
    message: str
    field: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def evidence_entry(source: SourceReference) -> dict:
    return {
        "record_type": source.record_type,
        "record_id": source.record_id,
        "source_file_id": source.source_file_id,
        "row_number": source.row_number,
    }


def dedupe_evidence(entries: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for e in entries:
        key = (e["record_type"], e["record_id"], e["source_file_id"], e["row_number"])
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def ok_envelope(
    dataset: Dataset,
    *,
    tool: str,
    facts: dict,
    evidence: list[dict],
    warnings: list[str],
) -> dict:
    snap = dataset.snapshot
    return {
        "status": STATUS_OK,
        "tool": tool,
        "dataset_version": snap.dataset_version,
        "as_of_date": snap.as_of_date.isoformat(),
        "currency": snap.currency,
        "facts": facts,
        "evidence": dedupe_evidence(evidence),
        "warnings": list(warnings),
        "error": None,
    }


def error_envelope(
    *,
    tool: str | None,
    code: str,
    message: str,
    field: str | None = None,
    dataset: Dataset | None = None,
) -> dict:
    snap = dataset.snapshot if dataset is not None else None
    error = {"code": code, "message": message}
    if field:
        error["field"] = field
    return {
        "status": STATUS_ERROR,
        "tool": tool,
        "dataset_version": snap.dataset_version if snap else None,
        "as_of_date": snap.as_of_date.isoformat() if snap else None,
        "currency": snap.currency if snap else None,
        "facts": {},
        "evidence": [],
        "warnings": [],
        "error": error,
    }


def iso(value: date | None) -> str | None:
    return None if value is None else value.isoformat()
