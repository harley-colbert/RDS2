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
    from ..routes.settings import settings_bp
    """Application factory used by tests and runtime."""
    config = load_config(config_path)
    # The frontend is served by a blueprint that lives outside of the Flask
    # package used for the API.  Flask enables its own static file handling by
    # default which would intercept requests like ``/static/js/app.js`` before
    # the blueprint gets a chance to serve them.  Those requests would then be
    # looked up inside Flask's internal ``static`` folder (which we don't use),
    # resulting in confusing 404 responses for legitimate frontend assets.
    #
    # Disabling the built-in static handling ensures that the blueprint mounted
    # in ``run.configure_frontend`` is the sole owner of the ``/static``
    # namespace and fixes the missing asset issue observed in the browser.
    app = Flask(__name__, static_folder=None)
    app.config.update(config)

    init_db(app)
    register_api(app)
    app.register_blueprint(settings_bp)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
