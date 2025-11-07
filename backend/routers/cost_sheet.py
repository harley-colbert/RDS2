from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..app.cost_sheet_service import cost_sheet_service
from ..app.config import get_cost_settings

router = APIRouter(prefix="/api/cost-sheet", tags=["cost-sheet"])


class PathBody(BaseModel):
    path: str


@router.get("/summary")
def get_summary() -> Dict[str, Any]:
    """Return raw table for Summary!C4:K55 as a 2D list."""
    cfg = get_cost_settings()
    if cfg.cost_sheet_path is None:
        raise HTTPException(status_code=400, detail="No cost sheet path configured.")
    try:
        # ensure opened
        cost_sheet_service.ensure_open(cfg.cost_sheet_path)
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
        return {"ok": True, "path": str(p)}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to open workbook: {e}")
