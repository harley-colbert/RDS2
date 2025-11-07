import json
from pathlib import Path

import pytest

import settings_db as root_settings_db
from backend.routers import panel3_cost
from backend.services import settings_db


@pytest.fixture(autouse=True)
def isolate_settings_db(tmp_path, monkeypatch):
    db_path = tmp_path / "settings.db"
    monkeypatch.setattr(root_settings_db, "DB_PATH", db_path)
    settings_db.init_db()
    yield


def test_connect_requires_configured_path() -> None:
    response = panel3_cost.connect_cost_grid()
    assert response.status_code == 400
    payload = json.loads(response.body.decode())
    assert payload["error"] == "COST_SHEET_PATH_MISSING"


def test_connect_opens_configured_workbook(tmp_path: Path, monkeypatch) -> None:
    workbook = tmp_path / "Costing.xlsm"
    workbook.write_text("dummy")
    settings_db.set_cost_sheet_path(workbook)

    recorded: dict[str, Path] = {}

    def fake_set_cost_sheet_path(path: Path) -> None:
        recorded["path"] = path

    monkeypatch.setattr(panel3_cost.cost_grid, "set_cost_sheet_path", fake_set_cost_sheet_path)

    payload = panel3_cost.connect_cost_grid()

    assert payload["ok"] is True
    assert payload["path"] == str(workbook)
    assert recorded["path"] == workbook


def test_connect_handles_missing_workbook(tmp_path: Path, monkeypatch) -> None:
    workbook = tmp_path / "missing.xlsm"
    settings_db.set_cost_sheet_path(workbook)

    def fake_set_cost_sheet_path(path: Path) -> None:
        raise FileNotFoundError(path)

    monkeypatch.setattr(panel3_cost.cost_grid, "set_cost_sheet_path", fake_set_cost_sheet_path)

    response = panel3_cost.connect_cost_grid()

    assert response.status_code == 400
    payload = json.loads(response.body.decode())
    assert payload["error"] == "COST_SHEET_PATH_MISSING"
