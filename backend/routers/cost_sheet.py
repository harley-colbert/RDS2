from __future__ import annotations

import os
import string
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..app.cost_sheet_service import cost_sheet_service
from ..app.config import get_cost_settings
from ..services import settings_db

router = APIRouter(prefix="/api/cost-sheet", tags=["cost-sheet"])


class PathBody(BaseModel):
    path: str


EXCEL_EXTENSIONS = {".xlsm", ".xlsb", ".xlsx", ".xls"}


def _serialize_entry(path: Path) -> Dict[str, Any]:
    is_dir = path.is_dir()
    is_file = path.is_file()
    suffix = path.suffix.lower()
    return {
        "name": path.name or str(path),
        "path": str(path),
        "isDir": is_dir,
        "isFile": is_file,
        "isExcel": is_file and suffix in EXCEL_EXTENSIONS,
    }


def _default_browse_root() -> Path:
    stored = settings_db.get_cost_sheet_path()
    if stored and stored.exists():
        return stored if stored.is_dir() else stored.parent
    home = Path.home()
    if home.exists():
        return home
    return Path.cwd()


def _list_roots() -> List[Dict[str, Any]]:
    if os.name == "nt":
        roots: List[Dict[str, Any]] = []
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:\\")
            if drive.exists():
                roots.append(
                    {
                        "name": f"{letter}:\\",
                        "path": str(drive),
                        "isDir": True,
                        "isFile": False,
                        "isExcel": False,
                    }
                )
        return roots
    root = Path("/")
    return [
        {
            "name": str(root),
            "path": str(root),
            "isDir": True,
            "isFile": False,
            "isExcel": False,
        }
    ]


def _normalize_target(raw: Optional[str]) -> Optional[Path]:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    path = Path(text).expanduser()
    # Handle bare Windows drive letters ("C:") which Path treats as current drive.
    if os.name == "nt" and len(text) == 2 and text.endswith(":"):
        path = Path(text + "\\")
    return path


@router.get("/summary")
def get_summary() -> Dict[str, Any]:
    """Return raw table for Summary!C4:K55 as a 2D list."""
    cfg = get_cost_settings()
    stored = settings_db.get_cost_sheet_path()
    path = stored or cfg.cost_sheet_path
    if path is None:
        raise HTTPException(status_code=400, detail="No cost sheet path configured.")
    try:
        # ensure opened
        cost_sheet_service.ensure_open(str(path))
        return cost_sheet_service.read_summary_raw()
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to read summary: {e}")


@router.post("/path")
def set_path(body: PathBody) -> Dict[str, Any]:
    p = Path(body.path)
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {p}")
    try:
        cost_sheet_service.ensure_open(str(p))
        settings_db.set_cost_sheet_path(p)
        return {"ok": True, "path": str(p)}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to open workbook: {e}")


@router.get("/path")
def get_path() -> Dict[str, Optional[str]]:
    stored = settings_db.get_cost_sheet_path()
    return {"path": str(stored) if stored else None}


@router.get("/browse")
def browse(path: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    target = _normalize_target(path)
    if target is None:
        base = _default_browse_root()
    else:
        if target.is_file():
            base = target.parent
        else:
            base = target
        if not base.exists():
            raise HTTPException(status_code=400, detail="Specified path does not exist.")
    try:
        entries: List[Dict[str, Any]] = []
        for child in sorted(base.iterdir(), key=lambda c: (0 if c.is_dir() else 1, c.name.lower())):
            entries.append(_serialize_entry(child))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied for directory.")
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Specified path does not exist.")

    parent: Optional[str]
    if base.parent == base:
        parent = None
    else:
        parent = str(base.parent)

    return {
        "cwd": str(base),
        "parent": parent,
        "entries": entries,
        "roots": _list_roots(),
    }
