from __future__ import annotations

import threading
from typing import Any, List, Optional

try:
    import xlwings as xw  # type: ignore
except Exception as e:  # pragma: no cover
    xw = None  # lazy import error until actually used


class ExcelNotAvailable(RuntimeError):
    pass


class ExcelManager:
    """xlwings manager that opens a workbook and can read ranges (with calculate)."""
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._app: Optional['xw.App'] = None
        self._book: Optional['xw.Book'] = None
        self._path: Optional[str] = None

    # ------------- lifecycle -------------
    def open_if_needed(self, path: str, *, visible: bool = False) -> None:
        if not path:
            raise ValueError("Cost sheet path is empty.")
        with self._lock:
            if self._book is not None and self._path == path:
                return
            self.close()  # close anything open
            if xw is None:
                raise ExcelNotAvailable("xlwings is not available in this environment")
            self._app = xw.App(visible=visible, add_book=False)
            self._app.screen_updating = False
            self._app.display_alerts = False
            self._app.enable_events = False
            try:
                # Prefer automatic calculation for live grid
                self._app.api.Calculation = -4105  # xlCalculationAutomatic
            except Exception:
                pass
            self._book = self._app.books.open(
                path,
                update_links=False,
                read_only=False,
                ignore_read_only_recommended=True,
            )
            self._path = path

    def close(self) -> None:
        with self._lock:
            try:
                if self._book is not None:
                    try:
                        self._book.save()
                    except Exception:
                        pass
                    self._book.close()
            finally:
                self._book = None
                self._path = None
                if self._app is not None:
                    try:
                        self._app.quit()
                    except Exception:
                        pass
                    self._app = None

    # ------------- operations -------------
    def _calculate(self) -> None:
        if self._app is None:
            return
        try:
            # Try a full calc, fall back to lightweight calc
            self._app.api.CalculateFullRebuild()
        except Exception:
            try:
                self._app.calculate()
            except Exception:
                pass

    def read_range(self, sheet_name: str, addr: str, *, calculate: bool = True) -> List[List[Any]]:
        with self._lock:
            if self._book is None:
                raise RuntimeError("Workbook not open. Call open_if_needed() first.")
            if calculate:
                self._calculate()
            sht = self._book.sheets[sheet_name]
            values = sht.range(addr).value
            if values is None:
                return []
            if isinstance(values, list) and values and isinstance(values[0], list):
                return values  # 2D already
            if isinstance(values, list):
                return [values]
            return [[values]]


excel_manager = ExcelManager()
