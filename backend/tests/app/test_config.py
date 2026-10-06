import pytest

from cashflow_app.config import AppConfig, ConfigError, config_from_env, load_dotenv

from app.helpers import FIXTURE_DIR


def test_defaults_are_mock_and_local(monkeypatch):
    cfg = config_from_env({"FIXTURE_DIR": str(FIXTURE_DIR)})
    assert cfg.app_mode == "mock" and cfg.is_live is False
    assert cfg.storage_backend == "local"
    assert cfg.bind_host == "127.0.0.1"
    assert cfg.demo_reset_enabled is True


def test_live_needs_region_and_model():
    with pytest.raises(ConfigError, match="AWS_REGION"):
        config_from_env({"APP_MODE": "live", "FIXTURE_DIR": str(FIXTURE_DIR)})
    cfg = config_from_env(
        {"APP_MODE": "live", "AWS_REGION": "ap-south-1", "BEDROCK_MODEL_ID": "example", "FIXTURE_DIR": str(FIXTURE_DIR)}
    )
    assert cfg.is_live


@pytest.mark.parametrize(
    "env",
    [
        {"APP_MODE": "demo"},
        {"STORAGE_BACKEND": "dynamodb"},
        {"DEFAULT_HORIZON_DAYS": "91"},
        {"MAX_TOOL_CALLS": "0"},
        {"FIXTURE_DIR": "D:/does-not-exist"},
    ],
)
def test_invalid_values_are_rejected(env):
    with pytest.raises(ConfigError):
        config_from_env({"FIXTURE_DIR": str(FIXTURE_DIR), **env})


def test_dotenv_loader_does_not_override_existing(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('APP_MODE="live"\n# comment\nBEDROCK_MODEL_ID=abc\nEMPTY=\n', encoding="utf-8")
    monkeypatch.setenv("APP_MODE", "mock")
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    loaded = load_dotenv(env_file)
    assert loaded == {"BEDROCK_MODEL_ID": "abc", "EMPTY": ""}
    import os

    assert os.environ["APP_MODE"] == "mock"
    assert load_dotenv(tmp_path / "missing.env") == {}


def test_reset_flag_parsing():
    assert config_from_env({"FIXTURE_DIR": str(FIXTURE_DIR), "DEMO_RESET_ENABLED": "false"}).demo_reset_enabled is False
    assert config_from_env({"FIXTURE_DIR": str(FIXTURE_DIR), "DEMO_RESET_ENABLED": "1"}).demo_reset_enabled is True
    assert AppConfig().cors_origins[0].startswith("http://localhost")
