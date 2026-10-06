"""Saved scenarios: explicit save, dataset-version binding, stale handling,
local JSON persistence, and demo reset."""

import json

import pytest

from cashflow_app.service import AppService, ServiceError
from cashflow_app.storage import InMemoryScenarioStore, LocalJsonScenarioStore, SavedScenario

from app.helpers import FIXTURE_DIR, csv_bytes, fixed_clock, INVOICE_HEADER, OBLIGATION_HEADER


def test_chat_never_saves_a_scenario(service):
    service.chat("What if Customer A pays two weeks late?")
    assert service.list_scenarios() == []


def test_save_list_get(service):
    saved = service.save_scenario("INV-001", 14, "Customer A late")
    assert saved["status"] == "ok"
    scenario = saved["scenario"]
    assert scenario["scenario_id"].startswith("scn_")
    assert scenario["dataset_version"] == "demo-v1" and scenario["stale"] is False
    assert scenario["created_at"] == fixed_clock()
    assert saved["result"]["facts"]["scenario"]["closing_cash"] == "25000.00"  # 30-day default horizon
    listed = service.list_scenarios()
    assert [s["scenario_id"] for s in listed] == [scenario["scenario_id"]]
    fetched = service.get_scenario(scenario["scenario_id"])
    assert fetched["result"]["facts"]["shifted_date"] == "2026-10-21"


def test_default_name_and_validation(service):
    saved = service.save_scenario("INV-002", 3)
    assert saved["scenario"]["name"] == "INV-002 delayed 3 days"
    with pytest.raises(ServiceError) as info:
        service.save_scenario("INV-404", 3)
    assert info.value.http_status == 404
    with pytest.raises(ServiceError):
        service.save_scenario("INV-001", 400)
    with pytest.raises(ServiceError):
        service.save_scenario("INV-001", "14")


def _new_version_files(snapshot):
    snap = dict(snapshot, dataset_version="demo-v2")
    invoices = csv_bytes(INVOICE_HEADER, "INV-001,Customer A,40000.00,0.00,2026-10-07,2026-10-14,open,INR")
    obligations = csv_bytes(OBLIGATION_HEADER, "PAY-001,Staff Payroll,payroll,70000.00,0.00,2026-10-09,2026-10-09,open,INR")
    return snap, invoices, obligations


def test_reimport_marks_saved_scenarios_stale_and_requires_recompute(service, snapshot):
    saved = service.save_scenario("INV-001", 14)
    sid = saved["scenario"]["scenario_id"]
    result = service.import_dataset(*_new_version_files(snapshot))
    assert result.ok
    listed = service.list_scenarios()[0]
    assert listed["stale"] is True and listed["current_dataset_version"] == "demo-v2"
    with pytest.raises(ServiceError) as info:
        service.get_scenario(sid)
    assert info.value.code == "stale_dataset" and info.value.http_status == 409
    fresh = service.recompute_scenario(sid)
    assert fresh["recomputed_from"] == sid
    assert fresh["scenario"]["dataset_version"] == "demo-v2" and fresh["scenario"]["stale"] is False
    assert fresh["result"]["facts"]["original_date"] == "2026-10-14"
    # The stale one is kept for the audit trail; the fresh one is separate.
    assert len(service.list_scenarios()) == 2


def test_chat_session_is_rebound_when_dataset_changes(service, snapshot):
    first = service.chat("What if Customer A pays two weeks late?")
    sid = first["session_id"]
    assert first["session"]["active_scenario"] is not None
    service.import_dataset(*_new_version_files(snapshot))
    second = service.chat("What is the cash position?", sid)
    assert any("dataset changed from demo-v1 to demo-v2" in w for w in second["warnings"])
    assert second["dataset_version"] == "demo-v2"
    assert second["session"]["active_scenario"] is None


def test_delete_scenario(service):
    sid = service.save_scenario("INV-001", 1)["scenario"]["scenario_id"]
    assert service.delete_scenario(sid)["deleted"] == sid
    with pytest.raises(ServiceError):
        service.delete_scenario(sid)


def test_import_for_another_business_is_refused(service, snapshot):
    with pytest.raises(ServiceError) as info:
        service.import_dataset(dict(snapshot, business_id="someone-else"), b"", b"")
    assert info.value.http_status == 403
    assert service.dataset.snapshot.dataset_version == "demo-v1"


def test_invalid_import_changes_nothing(service, snapshot):
    service.save_scenario("INV-001", 2)
    bad = csv_bytes(INVOICE_HEADER, "INV-001,Customer A,not-money,0.00,2026-10-07,2026-10-07,open,INR")
    result = service.import_dataset(dict(snapshot, dataset_version="demo-v3"), bad, csv_bytes(OBLIGATION_HEADER))
    assert not result.ok and result.errors[0].row_number == 2
    assert service.dataset.snapshot.dataset_version == "demo-v1"
    assert service.list_scenarios()[0]["stale"] is False


def test_reset_restores_fixture_and_clears_state(service):
    service.save_scenario("INV-001", 2)
    chat = service.chat("What if Customer A pays late by a week?")
    out = service.reset_demo()
    assert out["status"] == "ok" and out["scenarios_cleared"] == 1
    assert service.list_scenarios() == []
    assert service.sessions.get(chat["session_id"]) is None
    assert service.dataset.snapshot.dataset_version == "demo-v1"
    assert service.forecast("2026-10-09")["facts"]["closing_cash"] == "25000.00"


def test_reset_can_be_disabled(make_service):
    svc = make_service(demo_reset_enabled=False)
    with pytest.raises(ServiceError) as info:
        svc.reset_demo()
    assert info.value.http_status == 403


# --- local JSON store ------------------------------------------------------


def _scenario(scenario_id="scn_1", business="demo-business", version="demo-v1"):
    return SavedScenario(scenario_id, business, version, "INV-001", 14, "name", fixed_clock())


def test_local_json_store_round_trips_and_is_atomic(tmp_path):
    path = tmp_path / "nested" / "scenarios.json"
    store = LocalJsonScenarioStore(path)
    store.save(_scenario())
    store.save(_scenario("scn_2"))
    assert path.is_file()
    assert not list(path.parent.glob(".scenarios-*.tmp"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format"] == "cashflow-scenarios/1" and len(data["scenarios"]) == 2

    reopened = LocalJsonScenarioStore(path)
    assert [s.scenario_id for s in reopened.list("demo-business")] == ["scn_1", "scn_2"]
    assert reopened.get("demo-business", "scn_2").delay_days == 14
    assert reopened.get("other-business", "scn_2") is None
    assert reopened.delete("demo-business", "scn_1") is True
    assert [s.scenario_id for s in LocalJsonScenarioStore(path).list("demo-business")] == ["scn_2"]
    assert LocalJsonScenarioStore(path).clear("demo-business") == 1
    assert LocalJsonScenarioStore(path).list("demo-business") == []


def test_local_json_store_rejects_corrupt_file(tmp_path):
    path = tmp_path / "scenarios.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError):
        LocalJsonScenarioStore(path)


def test_store_is_scoped_by_business():
    store = InMemoryScenarioStore()
    store.save(_scenario("a", business="one"))
    store.save(_scenario("b", business="two"))
    assert [s.scenario_id for s in store.list("one")] == ["a"]
    assert store.clear("one") == 1 and store.list("two")


def test_saved_scenario_survives_service_restart(tmp_path, app_config):
    from cashflow_app.config import AppConfig

    cfg = AppConfig(**{**app_config.__dict__, "storage_backend": "local", "data_dir": tmp_path})
    cfg.validate()
    first = AppService(cfg, clock=fixed_clock)
    first.load_fixture()
    sid = first.save_scenario("INV-001", 14, "persisted")["scenario"]["scenario_id"]

    second = AppService(cfg, clock=fixed_clock)
    second.load_fixture()
    fetched = second.get_scenario(sid)
    assert fetched["scenario"]["name"] == "persisted"
    assert fetched["result"]["facts"]["scenario"]["closing_cash"] == "25000.00"
    assert (tmp_path / "scenarios.json").is_file()
    assert FIXTURE_DIR.is_dir()
