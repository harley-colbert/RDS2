from __future__ import annotations

import logging
import math
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import xlwings as xw  # type: ignore
    from xlwings.constants import Calculation as XlCalc  # type: ignore
except Exception:  # pragma: no cover - xlwings missing on non-Windows CI
    xw = None  # type: ignore
    XlCalc = None  # type: ignore


logger = logging.getLogger(__name__)

SUMMARY_SHEET_NAME = "Summary"
READ_RANGE = "C4:K55"
WRITE_CELL = "M4"


class ExcelUnavailable(RuntimeError):
    """Raised when xlwings/Excel cannot be used."""


_lock = threading.RLock()
_app: Optional["xw.App"] = None
_book: Optional["xw.Book"] = None
_book_path: Optional[Path] = None
_book_dirty: bool = False
_last_margin_change: Tuple[Optional[float], Optional[float]] = (None, None)
_last_read_at: Optional[datetime] = None


def _ensure_xlwings() -> None:
    if xw is None:  # pragma: no cover - handled in runtime environment
        raise ExcelUnavailable("xlwings is not available in this environment")


def _ensure_app() -> "xw.App":
    global _app
    if _app is None:
        _ensure_xlwings()
        _app = xw.App(visible=False, add_book=False)
        _app.screen_updating = False
        _app.display_alerts = False
        _app.enable_events = False
        try:
            if XlCalc is not None:
                _app.api.Calculation = XlCalc.xlCalculationAutomatic
        except Exception:  # pragma: no cover - non-critical
            logger.debug("Unable to set Calculation mode on Excel app.")
    return _app


def _open_workbook(path: Path) -> None:
    global _book, _book_path, _book_dirty
    app = _ensure_app()
    if _book is not None and _book_path and _book_path == path:
        return

    _close_book(save=False)

    logger.info("Opening cost grid workbook at %s", path)
    try:
        book = app.books.open(
            fullname=str(path),
            update_links=False,
            read_only=False,
            ignore_read_only_recommended=True,
            notify=False,
            add_to_mru=False,
            local=True,
        )
    except Exception as exc:  # pragma: no cover - real Excel interaction
        logger.exception("Failed to open workbook via xlwings: %s", exc)
        raise

    _book = book
    _book_path = path
    _book_dirty = False


def _close_book(save: bool) -> None:
    global _book, _book_path, _book_dirty
    if _book is None:
        return
    try:
        if save and _book_dirty:
            logger.info("Saving dirty workbook before closing.")
            _book.save()
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Failed to save workbook on close: %s", exc)
    finally:
        try:
            _book.close()
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Failed to close workbook: %s", exc)
        _book = None
        _book_path = None
        _book_dirty = False


def _ensure_workbook(path: Optional[Path]) -> None:
    if path is None:
        raise ValueError("Cost sheet path is not configured")
    if not path.exists():
        raise FileNotFoundError(path)
    _open_workbook(path)


def _ensure_active_book() -> None:
    if _book is None:
        raise RuntimeError("Workbook is not open; call open_and_read_summary first")


def _to_number(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and math.isnan(val):
            return None
        return float(val)

    s = str(val).strip()
    if not s:
        return None

    is_percent = s.endswith("%")
    if is_percent:
        s = s[:-1].strip()

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()

    s = s.replace(",", "")
    try:
        num = float(s)
        if negative:
            num = -num
        if is_percent:
            num /= 100.0
        return num
    except ValueError:
        return None


def _coalesce_description(values) -> str:
    parts: List[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text.replace("\n", " "))
    return " ".join(parts).strip()


def _read_summary_rows() -> List[Dict[str, Optional[float]]]:
    global _last_read_at
    _ensure_active_book()
    assert _book is not None
    ws = _book.sheets[SUMMARY_SHEET_NAME]
    logger.debug("Reading %s!%s", SUMMARY_SHEET_NAME, READ_RANGE)
    values = ws.range(READ_RANGE).value
    if values is None:
        values = []
    if isinstance(values, list) and values and not isinstance(values[0], list):
        values = [values]
    if not isinstance(values, list):
        values = [[values]]

    rows: List[Dict[str, Optional[float]]] = []
    for raw_row in values:
        if not isinstance(raw_row, list):
            raw_row = [raw_row]
        padded = list(raw_row) + [None] * max(0, 9 - len(raw_row))
        description = _coalesce_description(padded[0:5])
        qty = _to_number(padded[5])
        cost = _to_number(padded[6])
        sell = _to_number(padded[7])
        margin = _to_number(padded[8])
        if not description and all(val is None for val in (qty, cost, sell, margin)):
            continue
        rows.append(
            {
                "description": description,
                "qty": qty,
                "cost": cost,
                "sellPrice": sell,
                "margin": margin,
            }
        )

    _last_read_at = datetime.utcnow()
    return rows


def open_and_read_summary(xlsm_path: Path) -> List[Dict[str, Optional[float]]]:
    with _lock:
        _ensure_workbook(xlsm_path)
        return _read_summary_rows()


def apply_margin_and_read(margin_text: str) -> List[Dict[str, Optional[float]]]:
    global _book_dirty, _last_margin_change
    if not margin_text or not margin_text.strip():
        raise ValueError("Margin text is required")

    with _lock:
        if _book is None:
            if _book_path is None:
                raise RuntimeError("Workbook is not open; call open_and_read_summary first")
            _ensure_workbook(_book_path)
        _ensure_active_book()
        assert _book is not None
        ws = _book.sheets[SUMMARY_SHEET_NAME]

        before_raw = ws.range(WRITE_CELL).value
        before_margin = _to_number(before_raw)

        parsed = _to_number(margin_text)
        if parsed is None:
            raise ValueError(f"Could not parse margin value from '{margin_text}'")

        ws.range(WRITE_CELL).value = float(parsed)

        try:
            ws.api.Calculate()
            logger.debug("Executed sheet-level recalc for %s", WRITE_CELL)
        except Exception:
            logger.debug("Sheet.Calculate failed; attempting workbook calculate.")
            try:
                app = _ensure_app()
                if XlCalc is not None:
                    try:
                        app.api.Calculation = XlCalc.xlCalculationAutomatic
                    except Exception:
                        logger.debug("Unable to set Calculation mode on Application.")
                app.calculate()
            except Exception as exc:  # pragma: no cover - Excel specific
                logger.warning("Excel recalculation failed: %s", exc)

        after_raw = ws.range(WRITE_CELL).value
        after_margin = _to_number(after_raw)

        if after_margin is not None and after_margin != before_margin:
            _book_dirty = True
        _last_margin_change = (before_margin, after_margin)

        return _read_summary_rows()


def set_cost_sheet_path(path: Path) -> None:
    with _lock:
        _ensure_workbook(path)


def get_current_path() -> Optional[Path]:
    with _lock:
        return _book_path


def get_last_read_at() -> Optional[datetime]:
    with _lock:
        return _last_read_at


def consume_last_margin_change() -> Tuple[Optional[float], Optional[float]]:
    global _last_margin_change
    with _lock:
        result = _last_margin_change
        _last_margin_change = (None, None)
        return result


def close_excel_and_save_if_dirty() -> None:
    global _app
    with _lock:
        _close_book(save=True)
        if _app is not None:
            try:
                _app.quit()
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("Failed to quit Excel app: %s", exc)
            finally:
                _app = None
