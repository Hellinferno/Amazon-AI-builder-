"""HTTP API (docs/TOOLS_AND_API.md). Thin routes over ``AppService``.

Binds to localhost by default. Errors are JSON envelopes with a stable code.
"""

import json
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cashflow.scenario import MAX_DELAY_DAYS

from . import __version__
from .config import AppConfig
from .service import AppService, ServiceError


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    horizon_end: str | None = None


class SaveScenarioRequest(BaseModel):
    invoice_id: str = Field(min_length=1, max_length=64)
    delay_days: int = Field(ge=0, le=MAX_DELAY_DAYS)
    name: str | None = Field(default=None, max_length=80)


class ReminderRequest(BaseModel):
    invoice_id: str = Field(min_length=1, max_length=64)
    tone: str | None = None


class SimulateRequest(BaseModel):
    invoice_id: str = Field(min_length=1, max_length=64)
    delay_days: int = Field(ge=0, le=MAX_DELAY_DAYS)
    horizon_end: str | None = None


def _issues(issues) -> list[dict]:
    return [
        {"file": i.file, "row_number": i.row_number, "field": i.field, "reason": i.reason}
        for i in issues
    ]


def create_app(config: AppConfig, service: AppService | None = None) -> FastAPI:
    svc = service or AppService(config)
    if svc.datasets.current is None:
        svc.load_fixture()

    app = FastAPI(title="Cashflow Assistant API", version=__version__, docs_url="/docs")
    app.state.service = svc
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError):
        return JSONResponse(status_code=exc.http_status, content=exc.as_dict())

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "version": __version__,
            "mode": svc.provider.mode,
            "model_configured": bool(config.bedrock_model_id) if config.is_live else False,
            "dataset_loaded": svc.datasets.current is not None,
        }

    @app.get("/api/state")
    def state():
        return svc.state()

    @app.post("/api/demo/reset")
    def demo_reset():
        return svc.reset_demo()

    @app.post("/api/datasets/import")
    async def import_dataset(
        snapshot: Annotated[str, Form()],
        invoices: Annotated[UploadFile, File()],
        obligations: Annotated[UploadFile, File()],
    ):
        try:
            snapshot_obj = json.loads(snapshot)
        except ValueError:
            raise ServiceError("invalid_argument", "snapshot must be a JSON object", 400) from None
        result = svc.import_dataset(snapshot_obj, await invoices.read(), await obligations.read())
        if not result.ok:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "error",
                    "error": {"code": "invalid_import", "message": "the import was rejected; nothing changed"},
                    "errors": _issues(result.errors),
                    "warnings": _issues(result.warnings),
                },
            )
        return {
            "status": "ok",
            "dataset_version": result.dataset.snapshot.dataset_version,
            "invoice_count": len(result.dataset.invoices),
            "obligation_count": len(result.dataset.obligations),
            "warnings": _issues(result.warnings),
            "stale_scenarios": [s["scenario_id"] for s in svc.list_scenarios() if s["stale"]],
        }

    @app.get("/api/forecast")
    def forecast(horizon_end: str | None = None):
        return svc.forecast(horizon_end)

    @app.get("/api/invoices")
    def invoices():
        return svc.open_invoices()

    @app.get("/api/overdue")
    def overdue():
        return svc.overdue()

    @app.post("/api/simulate")
    def simulate(body: SimulateRequest):
        return svc.simulate(body.invoice_id, body.delay_days, body.horizon_end)

    @app.get("/api/records/{record_type}/{record_id}")
    def record(record_type: str, record_id: str):
        return svc.record(record_type, record_id)

    @app.post("/api/reminders/draft")
    def reminder(body: ReminderRequest):
        return svc.draft_reminder(body.invoice_id, body.tone)

    @app.post("/api/chat")
    def chat(body: ChatRequest):
        return svc.chat(body.message, body.session_id, body.horizon_end)

    @app.get("/api/scenarios")
    def list_scenarios():
        return {"status": "ok", "scenarios": svc.list_scenarios()}

    @app.post("/api/scenarios", status_code=201)
    def save_scenario(body: SaveScenarioRequest):
        return svc.save_scenario(body.invoice_id, body.delay_days, body.name)

    @app.get("/api/scenarios/{scenario_id}")
    def get_scenario(scenario_id: str):
        return svc.get_scenario(scenario_id)

    @app.post("/api/scenarios/{scenario_id}/recompute", status_code=201)
    def recompute_scenario(scenario_id: str):
        return svc.recompute_scenario(scenario_id)

    @app.delete("/api/scenarios/{scenario_id}")
    def delete_scenario(scenario_id: str):
        return svc.delete_scenario(scenario_id)

    return app
