"""Application service: the one place that resolves business context.

Routes call these methods; tests call them directly. The service owns the
dataset store, saved scenarios, sessions, and the model provider. Business
identity comes from configuration, never from a request or a model argument.
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

from cashflow.dates import MAX_HORIZON_DAYS, DateError, parse_date, validate_horizon
from cashflow.importer import DatasetStore, ImportResult
from cashflow.models import Dataset
from cashflow.scenario import MAX_DELAY_DAYS

from .agent.mock import MockProvider
from .agent.orchestrator import Orchestrator
from .agent.provider import ModelProvider
from .config import AppConfig
from .envelope import (
    E_INVALID_ARGUMENT,
    E_NO_DATASET,
    E_STALE_DATASET,
    E_UNKNOWN_RECORD,
    STATUS_OK,
)
from .session import SessionStore
from .storage import SavedScenario, ScenarioStore, build_scenario_store, new_scenario_id
from .tools import (
    TOOL_DRAFT_REMINDER,
    TOOL_GET_CASHFLOW,
    TOOL_GET_EVIDENCE,
    TOOL_LIST_OPEN_INVOICES,
    TOOL_LIST_OVERDUE,
    TOOL_SIMULATE_DELAY,
    ToolContext,
    run_tool,
)

SIMULATION_LABEL = "Simulated Alexa+ experience with synthetic demo data"


class ServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400, details: object = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details

    def as_dict(self) -> dict:
        error = {"code": self.code, "message": self.message}
        if self.details is not None:
            error["details"] = self.details
        return {"status": "error", "error": error}


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class FixtureFiles:
    snapshot: dict
    invoices_csv: bytes
    obligations_csv: bytes


def read_fixture(fixture_dir: Path) -> FixtureFiles:
    return FixtureFiles(
        snapshot=json.loads((fixture_dir / "snapshot.json").read_text(encoding="utf-8")),
        invoices_csv=(fixture_dir / "invoices.csv").read_bytes(),
        obligations_csv=(fixture_dir / "obligations.csv").read_bytes(),
    )


def build_provider(config: AppConfig) -> ModelProvider:
    if config.is_live:
        from .agent.bedrock import BedrockConverseProvider

        return BedrockConverseProvider(
            region=config.aws_region or "",
            model_id=config.bedrock_model_id or "",
            timeout=config.model_timeout_seconds,
        )
    return MockProvider()


class AppService:
    def __init__(
        self,
        config: AppConfig,
        *,
        provider: ModelProvider | None = None,
        scenario_store: ScenarioStore | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ):
        self.config = config
        self.datasets = DatasetStore()
        self.scenarios = scenario_store or build_scenario_store(config)
        self.sessions = SessionStore()
        self.provider = provider or build_provider(config)
        self.orchestrator = Orchestrator(self.provider, config)
        self.clock = clock
        self.business_name = "Demo Business"

    # --- dataset -------------------------------------------------------------

    def load_fixture(self) -> ImportResult:
        files = read_fixture(self.config.fixture_dir)
        result = self.import_dataset(files.snapshot, files.invoices_csv, files.obligations_csv)
        if not result.ok:
            raise RuntimeError(f"fixture failed to import: {[e.reason for e in result.errors]}")
        return result

    @property
    def dataset(self) -> Dataset:
        current = self.datasets.current
        if current is None:
            raise ServiceError(E_NO_DATASET, "no dataset is loaded; reset the demo or import one", 409)
        return current

    def default_horizon(self, dataset: Dataset) -> date:
        days = min(self.config.default_horizon_days, MAX_HORIZON_DAYS)
        return dataset.snapshot.as_of_date + timedelta(days=days)

    def import_dataset(self, snapshot: object, invoices_csv: object, obligations_csv: object) -> ImportResult:
        if isinstance(snapshot, dict) and snapshot.get("business_id") not in (None, self.config.business_id):
            raise ServiceError(
                "forbidden_business",
                f"this workspace is bound to business {self.config.business_id}",
                403,
            )
        return self.datasets.import_dataset(snapshot, invoices_csv, obligations_csv)

    def reset_demo(self) -> dict:
        if not self.config.demo_reset_enabled:
            raise ServiceError("reset_disabled", "demo reset is disabled in this environment", 403)
        self.datasets = DatasetStore()
        self.sessions.clear()
        cleared = self.scenarios.clear(self.config.business_id)
        result = self.load_fixture()
        return {
            "status": STATUS_OK,
            "dataset_version": result.dataset.snapshot.dataset_version,
            "scenarios_cleared": cleared,
            "warnings": [f"{w.file} row {w.row_number}: {w.reason}" for w in result.warnings],
        }

    def state(self) -> dict:
        current = self.datasets.current
        info = {
            "mode": self.provider.mode,
            "model_id": self.provider.model_id,
            "simulation_label": SIMULATION_LABEL,
            "storage_backend": self.scenarios.backend,
            "business_id": self.config.business_id,
            "business_name": self.business_name,
            "demo_reset_enabled": self.config.demo_reset_enabled,
            "dataset": None,
        }
        if current is not None:
            snap = current.snapshot
            info["dataset"] = {
                "dataset_version": snap.dataset_version,
                "as_of_date": snap.as_of_date.isoformat(),
                "currency": snap.currency,
                "timezone": snap.timezone,
                "opening_cash": _money(snap.opening_cash),
                "invoice_count": len(current.invoices),
                "obligation_count": len(current.obligations),
                "default_horizon_end": self.default_horizon(current).isoformat(),
                "fingerprint": current.fingerprint,
            }
        return info

    # --- tool-backed reads -----------------------------------------------------

    def _ctx(self, dataset: Dataset, horizon_end: date | None = None) -> ToolContext:
        return ToolContext(
            dataset=dataset,
            default_horizon_end=horizon_end or self.default_horizon(dataset),
            created_at=self.clock(),
            business_name=self.business_name,
        )

    def _run(self, name: str, arguments: dict, horizon_end: date | None = None) -> dict:
        envelope = run_tool(self._ctx(self.dataset, horizon_end), name, arguments)
        if envelope["status"] != STATUS_OK:
            err = envelope["error"]
            status = 404 if err["code"] in (E_UNKNOWN_RECORD, "unknown_invoice") else 400
            raise ServiceError(err["code"], err["message"], status, {"field": err.get("field")})
        return envelope

    def forecast(self, horizon_end: str | None = None) -> dict:
        return self._run(TOOL_GET_CASHFLOW, {"horizon_end": horizon_end} if horizon_end else {})

    def open_invoices(self) -> dict:
        return self._run(TOOL_LIST_OPEN_INVOICES, {})

    def overdue(self) -> dict:
        return self._run(TOOL_LIST_OVERDUE, {})

    def record(self, record_type: str, record_id: str) -> dict:
        return self._run(TOOL_GET_EVIDENCE, {"record_type": record_type, "record_id": record_id})

    def simulate(self, invoice_id: str, delay_days: int, horizon_end: str | None = None) -> dict:
        args: dict = {"invoice_id": invoice_id, "delay_days": delay_days}
        if horizon_end:
            args["horizon_end"] = horizon_end
        return self._run(TOOL_SIMULATE_DELAY, args)

    def draft_reminder(self, invoice_id: str, tone: str | None = None) -> dict:
        args: dict = {"invoice_id": invoice_id}
        if tone:
            args["tone"] = tone
        return self._run(TOOL_DRAFT_REMINDER, args)

    # --- conversation ----------------------------------------------------------

    def chat(self, message: str, session_id: str | None = None, horizon_end: str | None = None) -> dict:
        if not isinstance(message, str) or not message.strip():
            raise ServiceError(E_INVALID_ARGUMENT, "message must be a non-empty string", 400)
        if len(message) > 2000:
            raise ServiceError(E_INVALID_ARGUMENT, "message is too long (max 2000 characters)", 400)
        dataset = self.dataset
        warnings: list[str] = []
        session = self.sessions.get(session_id)
        if session is None:
            session = self.sessions.create(
                self.config.business_id, dataset.snapshot.dataset_version, self.default_horizon(dataset)
            )
        elif session.dataset_version != dataset.snapshot.dataset_version:
            warnings.append(
                f"The dataset changed from {session.dataset_version} to "
                f"{dataset.snapshot.dataset_version}; earlier scenario context was dropped."
            )
            self.sessions.rebind(session, dataset.snapshot.dataset_version, self.default_horizon(dataset))
        if horizon_end:
            try:
                parsed = parse_date(horizon_end)
                validate_horizon(dataset.snapshot.as_of_date, parsed)
            except DateError as exc:
                raise ServiceError(E_INVALID_ARGUMENT, f"horizon_end: {exc}", 400) from None
            session.horizon_end = parsed

        result = self.orchestrator.chat(
            session,
            dataset,
            message.strip(),
            created_at=self.clock(),
            business_name=self.business_name,
        )
        payload = result.as_dict()
        payload["warnings"] = warnings + payload["warnings"]
        payload["session_id"] = session.session_id
        payload["dataset_version"] = dataset.snapshot.dataset_version
        payload["as_of_date"] = dataset.snapshot.as_of_date.isoformat()
        payload["currency"] = dataset.snapshot.currency
        payload["simulation_label"] = SIMULATION_LABEL
        return payload

    # --- saved scenarios -------------------------------------------------------

    def save_scenario(self, invoice_id: str, delay_days: object, name: str | None = None) -> dict:
        if isinstance(delay_days, bool) or not isinstance(delay_days, int) or not 0 <= delay_days <= MAX_DELAY_DAYS:
            raise ServiceError(E_INVALID_ARGUMENT, f"delay_days must be an integer 0-{MAX_DELAY_DAYS}", 400)
        dataset = self.dataset
        result = self.simulate(invoice_id, delay_days)  # validates the invoice on this version
        saved = SavedScenario(
            scenario_id=new_scenario_id(),
            business_id=self.config.business_id,
            dataset_version=dataset.snapshot.dataset_version,
            invoice_id=invoice_id,
            delay_days=delay_days,
            name=(name or "").strip()[:80] or f"{invoice_id} delayed {delay_days} days",
            created_at=self.clock(),
        )
        self.scenarios.save(saved)
        return {"status": STATUS_OK, "scenario": self._describe(saved), "result": result}

    def _describe(self, saved: SavedScenario) -> dict:
        current = self.datasets.current
        data = saved.as_dict()
        data["stale"] = current is None or current.snapshot.dataset_version != saved.dataset_version
        data["current_dataset_version"] = current.snapshot.dataset_version if current else None
        return data

    def list_scenarios(self) -> list[dict]:
        return [self._describe(s) for s in self.scenarios.list(self.config.business_id)]

    def get_scenario(self, scenario_id: str) -> dict:
        saved = self.scenarios.get(self.config.business_id, scenario_id)
        if saved is None:
            raise ServiceError(E_UNKNOWN_RECORD, f"scenario {scenario_id} not found", 404)
        described = self._describe(saved)
        if described["stale"]:
            raise ServiceError(
                E_STALE_DATASET,
                f"scenario {scenario_id} was saved for dataset {saved.dataset_version}; the current "
                f"dataset is {described['current_dataset_version']}. Recompute it explicitly.",
                409,
                {"scenario": described},
            )
        return {"status": STATUS_OK, "scenario": described, "result": self.simulate(saved.invoice_id, saved.delay_days)}

    def recompute_scenario(self, scenario_id: str) -> dict:
        saved = self.scenarios.get(self.config.business_id, scenario_id)
        if saved is None:
            raise ServiceError(E_UNKNOWN_RECORD, f"scenario {scenario_id} not found", 404)
        fresh = self.save_scenario(saved.invoice_id, saved.delay_days, saved.name)
        fresh["recomputed_from"] = saved.scenario_id
        return fresh

    def delete_scenario(self, scenario_id: str) -> dict:
        if not self.scenarios.delete(self.config.business_id, scenario_id):
            raise ServiceError(E_UNKNOWN_RECORD, f"scenario {scenario_id} not found", 404)
        return {"status": STATUS_OK, "deleted": scenario_id}


def _money(paise: int) -> str:
    from cashflow.money import format_money

    return format_money(paise)
