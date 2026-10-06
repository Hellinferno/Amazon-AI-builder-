"""Application configuration read from the environment.

Names follow docs/AWS_SETUP.md. Nothing here contains a secret: AWS credentials
come from the standard credential chain, never from this module.
"""

import os
from dataclasses import dataclass
from pathlib import Path

MODE_MOCK = "mock"
MODE_LIVE = "live"
MODES = (MODE_MOCK, MODE_LIVE)

STORAGE_MEMORY = "memory"
STORAGE_LOCAL = "local"
STORAGE_BACKENDS = (STORAGE_MEMORY, STORAGE_LOCAL)

# Repository root: backend/src/cashflow_app/config.py -> three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]


class ConfigError(ValueError):
    """The environment does not describe a runnable configuration."""


@dataclass(frozen=True)
class AppConfig:
    app_mode: str = MODE_MOCK
    aws_region: str | None = None
    bedrock_model_id: str | None = None
    storage_backend: str = STORAGE_LOCAL
    data_dir: Path = _REPO_ROOT / "data" / "local"
    fixture_dir: Path = _REPO_ROOT / "data" / "synthetic" / "demo-v1"
    business_id: str = "demo-business"
    default_horizon_days: int = 30
    max_tool_calls: int = 6
    model_timeout_seconds: float = 30.0
    max_output_tokens: int = 800
    demo_reset_enabled: bool = True
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @property
    def is_live(self) -> bool:
        return self.app_mode == MODE_LIVE

    def validate(self) -> None:
        if self.app_mode not in MODES:
            raise ConfigError(f"APP_MODE must be one of {', '.join(MODES)}")
        if self.storage_backend not in STORAGE_BACKENDS:
            raise ConfigError(f"STORAGE_BACKEND must be one of {', '.join(STORAGE_BACKENDS)}")
        if self.is_live and not (self.aws_region and self.bedrock_model_id):
            raise ConfigError(
                "APP_MODE=live requires AWS_REGION and BEDROCK_MODEL_ID; "
                "set APP_MODE=mock to run without a model"
            )
        if self.default_horizon_days < 0 or self.default_horizon_days > 90:
            raise ConfigError("DEFAULT_HORIZON_DAYS must be between 0 and 90")
        if self.max_tool_calls < 1:
            raise ConfigError("MAX_TOOL_CALLS must be at least 1")
        if not self.fixture_dir.is_dir():
            raise ConfigError(f"FIXTURE_DIR does not exist: {self.fixture_dir}")


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load ``KEY=value`` lines from ``.env`` into the environment without
    overriding variables that are already set. Returns what was loaded.
    """
    path = path or (_REPO_ROOT / ".env")
    loaded: dict[str, str] = {}
    if not path.is_file():
        return loaded
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded


def config_from_env(env: dict[str, str] | None = None) -> AppConfig:
    e = os.environ if env is None else env
    defaults = AppConfig()
    cfg = AppConfig(
        app_mode=(e.get("APP_MODE") or defaults.app_mode).strip().lower(),
        aws_region=e.get("AWS_REGION") or None,
        bedrock_model_id=e.get("BEDROCK_MODEL_ID") or None,
        storage_backend=(e.get("STORAGE_BACKEND") or defaults.storage_backend).strip().lower(),
        data_dir=Path(e["DATA_DIR"]) if e.get("DATA_DIR") else defaults.data_dir,
        fixture_dir=Path(e["FIXTURE_DIR"]) if e.get("FIXTURE_DIR") else defaults.fixture_dir,
        business_id=e.get("BUSINESS_ID") or defaults.business_id,
        default_horizon_days=int(e.get("DEFAULT_HORIZON_DAYS") or defaults.default_horizon_days),
        max_tool_calls=int(e.get("MAX_TOOL_CALLS") or defaults.max_tool_calls),
        model_timeout_seconds=float(
            e.get("MODEL_TIMEOUT_SECONDS") or defaults.model_timeout_seconds
        ),
        max_output_tokens=int(e.get("MAX_OUTPUT_TOKENS") or defaults.max_output_tokens),
        demo_reset_enabled=_env_bool(e.get("DEMO_RESET_ENABLED"), defaults.demo_reset_enabled),
        bind_host=e.get("BIND_HOST") or defaults.bind_host,
        bind_port=int(e.get("BIND_PORT") or defaults.bind_port),
    )
    cfg.validate()
    return cfg
