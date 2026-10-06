"""HTTP surface through the FastAPI test client (no network, mock mode)."""

import json

import pytest
from fastapi.testclient import TestClient

from cashflow_app.api import create_app

from app.helpers import INVOICE_HEADER, OBLIGATION_HEADER, csv_bytes


@pytest.fixture
def client(service):
    app = create_app(service.config, service)
    with TestClient(app) as c:
        yield c


def test_health_and_state(client):
    health = client.get("/health").json()
    assert health["status"] == "ok" and health["mode"] == "mock" and health["dataset_loaded"] is True
    assert health["model_configured"] is False
    state = client.get("/api/state").json()
    assert state["mode"] == "mock"
    assert "Simulated Alexa+" in state["simulation_label"]
    assert state["dataset"]["dataset_version"] == "demo-v1"
    assert state["dataset"]["as_of_date"] == "2026-10-05"
    assert state["dataset"]["opening_cash"] == "50000.00"


def test_forecast_and_overdue_endpoints(client):
    r = client.get("/api/forecast", params={"horizon_end": "2026-10-09"})
    assert r.status_code == 200
    assert r.json()["facts"]["closing_cash"] == "25000.00"
    bad = client.get("/api/forecast", params={"horizon_end": "2026-10-01"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_argument"
    assert client.get("/api/overdue").json()["facts"]["invoices"] == []
    assert len(client.get("/api/invoices").json()["facts"]["invoices"]) == 2


def test_simulate_endpoint(client):
    r = client.post("/api/simulate", json={"invoice_id": "INV-001", "delay_days": 14, "horizon_end": "2026-10-09"})
    assert r.status_code == 200
    assert r.json()["facts"]["scenario"]["closing_cash"] == "-15000.00"
    assert client.post("/api/simulate", json={"invoice_id": "INV-001", "delay_days": 999}).status_code == 422
    assert client.post("/api/simulate", json={"invoice_id": "INV-404", "delay_days": 1}).status_code == 404


def test_records_endpoint(client):
    r = client.get("/api/records/invoice/INV-001")
    assert r.status_code == 200 and r.json()["facts"]["record"]["customer_name"] == "Customer A"
    assert client.get("/api/records/invoice/NOPE").status_code == 404
    assert client.get("/api/records/bank/NOPE").status_code == 400


def test_reminder_endpoint(client):
    r = client.post("/api/reminders/draft", json={"invoice_id": "INV-002", "tone": "friendly"})
    assert r.status_code == 200
    assert r.json()["facts"]["draft"]["sent"] is False
    assert client.post("/api/reminders/draft", json={"invoice_id": "INV-002", "tone": "shouty"}).status_code == 400


def test_chat_endpoint_keeps_session(client):
    first = client.post("/api/chat", json={"message": "What if Customer A pays two weeks late?"})
    assert first.status_code == 200
    body = first.json()
    assert body["mode"] == "mock" and body["grounded"] is True
    assert body["session_id"]
    assert body["tool_trace"][0]["tool"] == "simulate_payment_delay"
    second = client.post("/api/chat", json={"message": "and three weeks?", "session_id": body["session_id"]})
    assert second.json()["tool_trace"][0]["arguments"]["delay_days"] == 21
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_scenario_endpoints(client, snapshot):
    created = client.post("/api/scenarios", json={"invoice_id": "INV-001", "delay_days": 14, "name": "late A"})
    assert created.status_code == 201
    sid = created.json()["scenario"]["scenario_id"]
    assert client.get("/api/scenarios").json()["scenarios"][0]["stale"] is False
    assert client.get(f"/api/scenarios/{sid}").status_code == 200
    assert client.get("/api/scenarios/scn_missing").status_code == 404

    files = {
        "invoices": ("invoices.csv", csv_bytes(INVOICE_HEADER, "INV-001,Customer A,40000.00,0.00,2026-10-07,2026-10-14,open,INR"), "text/csv"),
        "obligations": ("obligations.csv", csv_bytes(OBLIGATION_HEADER), "text/csv"),
    }
    imported = client.post(
        "/api/datasets/import",
        data={"snapshot": json.dumps(dict(snapshot, dataset_version="demo-v2"))},
        files=files,
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["stale_scenarios"] == [sid]

    stale = client.get(f"/api/scenarios/{sid}")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "stale_dataset"
    recomputed = client.post(f"/api/scenarios/{sid}/recompute")
    assert recomputed.status_code == 201 and recomputed.json()["scenario"]["dataset_version"] == "demo-v2"
    assert client.delete(f"/api/scenarios/{sid}").status_code == 200
    assert client.delete(f"/api/scenarios/{sid}").status_code == 404


def test_invalid_import_returns_row_errors_and_changes_nothing(client, snapshot):
    files = {
        "invoices": ("invoices.csv", csv_bytes(INVOICE_HEADER, "INV-001,Customer A,40000.00,0.00,07/10/2026,2026-10-07,open,INR"), "text/csv"),
        "obligations": ("obligations.csv", csv_bytes(OBLIGATION_HEADER), "text/csv"),
    }
    r = client.post("/api/datasets/import", data={"snapshot": json.dumps(dict(snapshot, dataset_version="demo-v9"))}, files=files)
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "invalid_import"
    assert body["errors"][0]["row_number"] == 2 and body["errors"][0]["field"] == "due_date"
    assert client.get("/api/state").json()["dataset"]["dataset_version"] == "demo-v1"
    bad_json = client.post("/api/datasets/import", data={"snapshot": "{nope"}, files=files)
    assert bad_json.status_code == 400


def test_import_for_other_business_is_forbidden(client, snapshot):
    files = {
        "invoices": ("invoices.csv", csv_bytes(INVOICE_HEADER), "text/csv"),
        "obligations": ("obligations.csv", csv_bytes(OBLIGATION_HEADER), "text/csv"),
    }
    r = client.post("/api/datasets/import", data={"snapshot": json.dumps(dict(snapshot, business_id="other"))}, files=files)
    assert r.status_code == 403


def test_demo_reset(client):
    client.post("/api/scenarios", json={"invoice_id": "INV-001", "delay_days": 1})
    r = client.post("/api/demo/reset")
    assert r.status_code == 200 and r.json()["scenarios_cleared"] == 1
    assert client.get("/api/scenarios").json()["scenarios"] == []


def test_cors_allows_the_vite_dev_server(client):
    r = client.options(
        "/api/chat",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
