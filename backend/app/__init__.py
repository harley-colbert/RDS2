from __future__ import annotations

try:  # pragma: no cover - optional during ingestion
    from flask import Flask
except ImportError:  # pragma: no cover - allow ingestion without Flask installed
    Flask = None  # type: ignore

def create_app(config_path: str | None = None) -> Flask:
    if Flask is None:  # pragma: no cover - defensive
        raise RuntimeError("Flask is required to create the application")
    from .config import load_config
    from .database import init_db
    from .api import register_api
    """Application factory used by tests and runtime."""
    config = load_config(config_path)
    app = Flask(__name__)
    app.config.update(config)

    init_db(app)
    register_api(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
