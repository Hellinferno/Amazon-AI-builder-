"""Fixtures for the application layer. Everything runs offline in mock mode."""

import pytest

from cashflow_app.config import AppConfig
from cashflow_app.service import AppService
from cashflow_app.storage import InMemoryScenarioStore
from cashflow_app.tools import ToolContext

from app.helpers import FIXED_NOW, FIXTURE_DIR, FRIDAY, fixed_clock


@pytest.fixture
def app_config(tmp_path) -> AppConfig:
    cfg = AppConfig(
        storage_backend="memory",
        data_dir=tmp_path / "local",
        fixture_dir=FIXTURE_DIR,
        default_horizon_days=30,
        max_tool_calls=4,
    )
    cfg.validate()
    return cfg


@pytest.fixture
def service(app_config) -> AppService:
    svc = AppService(app_config, scenario_store=InMemoryScenarioStore(), clock=fixed_clock)
    svc.load_fixture()
    return svc


@pytest.fixture
def make_service(app_config):
    def _make(provider=None, **overrides) -> AppService:
        cfg = AppConfig(**{**app_config.__dict__, **overrides})
        cfg.validate()
        svc = AppService(cfg, provider=provider, scenario_store=InMemoryScenarioStore(), clock=fixed_clock)
        svc.load_fixture()
        return svc

    return _make


@pytest.fixture
def golden_ctx(service) -> ToolContext:
    return ToolContext(
        dataset=service.dataset, default_horizon_end=FRIDAY, created_at=FIXED_NOW, business_name="Demo Business"
    )
