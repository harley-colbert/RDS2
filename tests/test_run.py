from __future__ import annotations

import sys
import pytest
from flask import Flask

import run


@pytest.fixture(autouse=True)
def restore_sys_argv(monkeypatch):
    original = sys.argv[:]
    yield
    monkeypatch.setattr(sys, "argv", original, raising=False)


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run.py"], raising=False)
    args = run.parse_args()
    assert args.host == "0.0.0.0"
    assert args.port == 5234
    assert args.debug is False
    assert args.config is None


def test_main_registers_routes_and_runs(tmp_path, monkeypatch):
    frontend_dir = tmp_path / "frontend"
    static_dir = frontend_dir / "static"
    static_dir.mkdir(parents=True)
    index_file = frontend_dir / "index.html"
    index_file.write_text("<html>ok</html>")
    asset_file = static_dir / "style.css"
    asset_file.write_text("body { background: #fff; }")

    config_path = tmp_path / "config.json"
    config_path.write_text("{}")

    monkeypatch.setattr(run, "FRONTEND_DIR", frontend_dir)
    monkeypatch.setattr(sys, "argv", [
        "run.py",
        "--config",
        str(config_path),
        "--host",
        "0.0.0.0",
        "--port",
        "6000",
        "--debug",
    ], raising=False)

    created_app = Flask("test_app", static_folder=None)
    received = {}

    def fake_create_app(config: str | None):
        received["config"] = config
        return created_app

    monkeypatch.setattr(run, "create_app", fake_create_app)

    def fake_run(self, host, port, debug):
        received["run"] = {"host": host, "port": port, "debug": debug}

    monkeypatch.setattr(Flask, "run", fake_run, raising=False)

    run.main()

    assert received["config"] == str(config_path)
    assert received["run"] == {"host": "0.0.0.0", "port": 6000, "debug": True}

    client = created_app.test_client()
    index_response = client.get("/")
    assert index_response.status_code == 200
    assert "ok" in index_response.get_data(as_text=True)

    asset_response = client.get("/static/style.css")
    assert asset_response.status_code == 200
    assert "background" in asset_response.get_data(as_text=True)


def test_main_missing_frontend(tmp_path, monkeypatch):
    missing_frontend = tmp_path / "frontend"
    monkeypatch.setattr(run, "FRONTEND_DIR", missing_frontend)
    monkeypatch.setattr(sys, "argv", ["run.py"], raising=False)

    with pytest.raises(FileNotFoundError):
        run.main()
