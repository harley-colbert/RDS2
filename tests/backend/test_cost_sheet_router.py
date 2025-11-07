from __future__ import annotations

from pathlib import Path

import pytest

import settings_db as root_settings_db
from backend.routers import cost_sheet as cost_sheet_router
from backend.services import settings_db


@pytest.fixture(autouse=True)
def isolate_settings_db(tmp_path, monkeypatch):
    db_path = tmp_path / "settings.db"
    monkeypatch.setattr(root_settings_db, "DB_PATH", db_path)
    settings_db.init_db()
    yield


@pytest.fixture(autouse=True)
def mock_excel(monkeypatch):
    monkeypatch.setattr(cost_sheet_router.cost_sheet_service, "ensure_open", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cost_sheet_router.cost_sheet_service,
        "read_summary_raw",
        lambda: {"sheet": "Summary", "range": "A1", "values": []},
    )


def test_get_path_returns_none_when_not_set() -> None:
    assert cost_sheet_router.get_path() == {"path": None}


def test_set_path_persists_to_db(tmp_path: Path) -> None:
    workbook = tmp_path / "Costing.xlsm"
    workbook.write_text("dummy")

    payload = cost_sheet_router.set_path(cost_sheet_router.PathBody(path=str(workbook)))
    assert payload["path"] == str(workbook)

    stored = settings_db.get_cost_sheet_path()
    assert stored is not None
    assert stored == workbook


def test_browse_lists_directory_contents(tmp_path: Path) -> None:
    subdir = tmp_path / "nested"
    subdir.mkdir()
    excel_file = tmp_path / "quote.xlsm"
    excel_file.write_text("dummy")
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("notes")

    payload = cost_sheet_router.browse(str(tmp_path))
    assert payload["cwd"] == str(tmp_path)
    paths = {entry["path"]: entry for entry in payload["entries"]}
    assert str(subdir) in paths and paths[str(subdir)]["isDir"] is True
    assert str(excel_file) in paths and paths[str(excel_file)]["isExcel"] is True
    assert str(txt_file) in paths and paths[str(txt_file)]["isExcel"] is False


def test_browse_invalid_path_raises_http_exception() -> None:
    with pytest.raises(cost_sheet_router.HTTPException) as exc:
        cost_sheet_router.browse("Z:/does/not/exist")
    assert exc.value.status_code == 400
