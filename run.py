from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
os.chdir(ROOT)

from backend.app import create_app


DEFAULT_CONFIG = ROOT / "config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the RDS Local Sales Tool backend")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG if DEFAULT_CONFIG.exists() else None,
        help=(
            "Optional path to a JSON config file (defaults to config.json when present, "
            "otherwise relies on the RDS_CONFIG environment variable or built-in defaults)"
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode (includes auto-reload)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_arg: Path | None = args.config
    config_path = str(config_arg) if config_arg else None
    app = create_app(config_path)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
