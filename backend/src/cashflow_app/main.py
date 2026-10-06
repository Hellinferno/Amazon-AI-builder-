"""Entry point: ``uvicorn cashflow_app.main:app``.

Reads ``.env`` (if present) and the environment. Defaults to mock mode on
127.0.0.1:8000 with the synthetic fixture loaded.
"""

from .api import create_app
from .config import config_from_env, load_dotenv

load_dotenv()
config = config_from_env()
app = create_app(config)


def run() -> None:  # pragma: no cover - convenience for ``python -m cashflow_app.main``
    import uvicorn

    uvicorn.run(app, host=config.bind_host, port=config.bind_port)


if __name__ == "__main__":  # pragma: no cover
    run()
