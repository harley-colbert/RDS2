from __future__ import annotations

from typing import Any, Dict, Optional

from .config import get_cost_settings
from .excel_xlwings import excel_manager


class CostSheetService:
    """Facade for opening the cost sheet and reading the Summary block."""
    def __init__(self) -> None:
        self._ready = False

    def ensure_open(self, explicit_path: Optional[str] = None) -> None:
        cfg = get_cost_settings()
        path = explicit_path or cfg.cost_sheet_path
        if not path:
            return
        excel_manager.open_if_needed(path, visible=cfg.xlwings_visible)
        self._ready = True

    def read_summary_raw(self) -> Dict[str, Any]:
        cfg = get_cost_settings()
        data = excel_manager.read_range(cfg.summary_sheet_name, cfg.summary_read_range, calculate=True)
        return {
            "sheet": cfg.summary_sheet_name,
            "range": cfg.summary_read_range,
            "values": data,
        }


cost_sheet_service = CostSheetService()
