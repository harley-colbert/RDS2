from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from settings_db import (  # type: ignore
    add_margin_change as _add_margin_change,
    clear_margin_changes as _clear_margin_changes,
    get_cost_sheet_path as _get_cost_sheet_path,
    get_margin_changes as _get_margin_changes,
    init_db as _init_db,
    set_cost_sheet_path as _set_cost_sheet_path,
)

_init_db()


def get_cost_sheet_path() -> Optional[Path]:
    return _get_cost_sheet_path()


def set_cost_sheet_path(path: Path) -> None:
    _set_cost_sheet_path(path)


def add_margin_change(old_margin: Optional[float], new_margin: Optional[float]) -> None:
    _add_margin_change(old_margin, new_margin)


def get_margin_changes() -> List[Tuple[int, str, Optional[float], Optional[float]]]:
    return _get_margin_changes()


def clear_margin_changes() -> None:
    _clear_margin_changes()


def init_db() -> None:
    _init_db()
