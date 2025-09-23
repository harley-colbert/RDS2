from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from flask import Blueprint, Flask, send_from_directory
from werkzeug.exceptions import NotFound

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
os.chdir(ROOT)

from backend.app import create_app

DEFAULT_CONFIG = ROOT / "config.json"
FRONTEND_DIR = ROOT / "frontend"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the RDS Local Sales Tool backend and frontend"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG if DEFAULT_CONFIG.exists() else None,
        help=(
            "Optional path to a JSON config file (defaults to config.json when present, "
            "otherwise relies on the RDS_CONFIG environment variable or built-in defaults)"
        ),
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=5234, help="Port to listen on (default: 5234)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode (includes auto-reload)",
    )
    return parser.parse_args()


def configure_frontend(app: Flask, frontend_dir: Path) -> None:
    """Register routes for serving the built frontend alongside the API."""

    if not frontend_dir.exists():
        raise FileNotFoundError(
            "Frontend assets are missing. Expected to find the 'frontend' directory alongside run.py."
        )

    index_file = frontend_dir / "index.html"
    if not index_file.is_file():
        raise FileNotFoundError("Frontend index.html is missing from the frontend directory.")

    static_dir = frontend_dir / "static"
    if not static_dir.is_dir():
        raise FileNotFoundError("Frontend static assets directory is missing.")

    frontend_bp = Blueprint(
        "frontend",
        __name__,
        static_folder=str(static_dir),
        static_url_path="/static",
    )

    @frontend_bp.route("/")
    @frontend_bp.route("/index.html")
    def frontend_index():
        return send_from_directory(frontend_dir, "index.html")

    @frontend_bp.route("/<path:asset>")
    def frontend_assets(asset: str):
        candidate = frontend_dir / asset
        if candidate.is_file():
            return send_from_directory(frontend_dir, asset)
        raise NotFound()

    app.register_blueprint(frontend_bp)


def main() -> None:
    args = parse_args()
    config_arg: Path | None = args.config
    config_path = str(config_arg) if config_arg else None

    app = create_app(config_path)

    configure_frontend(app, FRONTEND_DIR)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
