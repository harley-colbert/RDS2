from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..services import cost_grid, settings_db

router = APIRouter(prefix="/api/panel3", tags=["panel3"])
logger = logging.getLogger(__name__)


class MarginBody(BaseModel):
    margin_text: str = Field(..., alias="marginText")


class PathBody(BaseModel):
    path: str


def _summary_response(rows: list[dict[str, Any]], path: Path) -> Dict[str, Any]:
    last_read = cost_grid.get_last_read_at() or datetime.utcnow()
    return {
        "rows": rows,
        "meta": {
            "path": str(path),
            "lastReadAt": last_read.replace(microsecond=0).isoformat() + "Z",
        },
    }


@router.post("/connect")
def connect_cost_grid() -> Dict[str, Any]:
    """Ensure the stored cost sheet is connected via xlwings before use."""

    path = settings_db.get_cost_sheet_path()
    if path is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "COST_SHEET_PATH_MISSING"},
        )

    try:
        cost_grid.set_cost_sheet_path(path)
    except FileNotFoundError:
        logger.warning("Stored cost sheet path is missing on disk: %s", path)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "COST_SHEET_PATH_MISSING"},
        )
    except cost_grid.ExcelUnavailable as exc:
        logger.error("Excel is unavailable: %s", exc)
        raise HTTPException(status_code=500, detail="Excel is not available on this server.")
    except ValueError as exc:
        logger.error("Invalid cost sheet path configured: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "COST_SHEET_PATH_MISSING"},
        )
    except Exception as exc:  # pragma: no cover - Excel runtime errors
        logger.exception("Failed to connect cost grid: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to connect to cost grid.")

    return {"ok": True, "path": str(path)}


@router.get("/summary")
def get_summary() -> Dict[str, Any]:
    path = settings_db.get_cost_sheet_path()
    if path is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "COST_SHEET_PATH_MISSING"},
        )
    try:
        rows = cost_grid.open_and_read_summary(path)
        return _summary_response(rows, path)
    except FileNotFoundError:
        logger.warning("Stored cost sheet path is missing on disk: %s", path)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "COST_SHEET_PATH_MISSING"},
        )
    except cost_grid.ExcelUnavailable as exc:
        logger.error("Excel is unavailable: %s", exc)
        raise HTTPException(status_code=500, detail="Excel is not available on this server.")
    except ValueError as exc:
        logger.error("Invalid cost sheet path configured: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "COST_SHEET_PATH_MISSING"},
        )
    except Exception as exc:  # pragma: no cover - Excel runtime errors
        logger.exception("Failed to read cost grid summary: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read cost grid summary.")


@router.post("/margin")
def apply_margin(body: MarginBody) -> Dict[str, Any]:
    path = settings_db.get_cost_sheet_path()
    if path is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "COST_SHEET_PATH_MISSING"},
        )

    margin_text = body.margin_text.strip()
    if not margin_text:
        raise HTTPException(status_code=400, detail="Margin text is required.")

    try:
        rows = cost_grid.apply_margin_and_read(margin_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except cost_grid.ExcelUnavailable as exc:
        logger.error("Excel is unavailable: %s", exc)
        raise HTTPException(status_code=500, detail="Excel is not available on this server.")
    except Exception as exc:  # pragma: no cover - Excel runtime errors
        logger.exception("Failed to apply margin: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to apply margin.")

    old_margin, new_margin = cost_grid.consume_last_margin_change()
    if new_margin is not None and new_margin != old_margin:
        try:
            settings_db.add_margin_change(old_margin, new_margin)
        except Exception as exc:  # pragma: no cover - DB failures shouldn't crash API
            logger.warning("Failed to record margin change: %s", exc)

    return _summary_response(rows, path)


@router.post("/path")
def set_path(body: PathBody) -> Dict[str, Any]:
    raw = body.path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Path is required.")

    path = Path(raw)
    if not path.exists():
        raise HTTPException(status_code=400, detail="Specified path does not exist.")

    try:
        settings_db.set_cost_sheet_path(path)
        cost_grid.set_cost_sheet_path(path)
    except cost_grid.ExcelUnavailable as exc:
        logger.error("Excel is unavailable: %s", exc)
        raise HTTPException(status_code=500, detail="Excel is not available on this server.")
    except Exception as exc:  # pragma: no cover - Excel runtime errors
        logger.exception("Failed to open workbook: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to open workbook.")

    return {"ok": True}
