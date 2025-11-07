import threading
import queue
import time
import math
import logging
from pathlib import Path
from typing import List, Tuple, Optional

try:
    import xlwings as xw
    XLWINGS_AVAILABLE = True
    _XLWINGS_IMPORT_ERROR = None
except Exception as e:
    XLWINGS_AVAILABLE = False
    _XLWINGS_IMPORT_ERROR = e


logger = logging.getLogger("ExcelWorker")


def to_number(val):
    """
    Robust numeric coercion shared with the app:
    - Accepts int/float directly (NaN -> None)
    - Parses strings with commas
    - Parses percentages '12.3%' -> 0.123
    - Parentheses negatives '(1,234.5)' -> -1234.5
    - Returns None if not parseable or empty
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and math.isnan(val):
            return None
        return float(val)

    s = str(val).strip()
    if s == "":
        return None

    is_percent = s.endswith("%")
    if is_percent:
        s = s[:-1].strip()

    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()

    s = s.replace(",", "")
    try:
        num = float(s)
        if neg:
            num = -num
        if is_percent:
            num = num / 100.0
        return num
    except ValueError:
        return None


def coalesce_description(values_5) -> str:
    """
    Join 5 cells (C..G) into a single Description string.
    Used both for xlwings reads and openpyxl reads in the UI.
    """
    parts = []
    for v in values_5:
        if v is None:
            continue
        text = str(v).strip()
        if text:
            parts.append(text.replace("\n", " "))
    return " ".join(parts).strip()


class ExcelSessionWorker:
    """
    Background Excel worker that:
      - Starts a hidden Excel instance in its own thread
      - Opens a workbook read/write
      - Can write a margin to Summary!M24, recalc, and read Summary!C4:K55
      - Keeps Excel + workbook open while the app is running

    All Excel COM calls happen on the worker thread (required).
    UI thread talks to this via a command queue.
    """

    def __init__(self, read_range: str = "C4:K55", sheet_name: str = "Summary", write_cell: str = "M24"):
        if not XLWINGS_AVAILABLE:
            raise RuntimeError(f"xlwings failed to import: {_XLWINGS_IMPORT_ERROR!r}")

        self.read_range = read_range
        self.sheet_name = sheet_name
        self.write_cell = write_cell

        self._cmd_q: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._ready_event = threading.Event()

        self._path: Optional[Path] = None
        self._app: Optional["xw.App"] = None
        self._book: Optional["xw.Book"] = None

        self._alerts_original = None
        self._events_original = None
        self._auto_sec_original = None

        self._last_error: Optional[str] = None

    # ---------- public API (called from main/UI thread) ----------

    def start(self):
        """Start the worker thread (only once)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def open_workbook_async(self, path: Path):
        """
        Ask the worker to open this workbook read/write in the background.
        Returns immediately; use is_ready() to see when it is ready.
        """
        self._path = path
        self._ready_event.clear()
        self._cmd_q.put({"type": "open", "path": path})

    def is_ready(self) -> bool:
        """True if the workbook is open and ready for commands."""
        return self._ready_event.is_set()

    def get_last_error(self) -> Optional[str]:
        """Return last worker error (if any) as a string."""
        return self._last_error

    def write_margin_and_read_summary(self, margin_input: str) -> List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]]:
        """
        Synchronously:
          - write margin_input to Summary!M24
          - recalc
          - read Summary!C4:K55
        This blocks the caller until the worker finishes.
        """
        reply_q: "queue.Queue" = queue.Queue()
        self._cmd_q.put({
            "type": "write_and_read",
            "margin_input": margin_input,
            "reply_q": reply_q,
        })
        status, payload = reply_q.get()
        if status == "ok":
            return payload
        else:
            raise RuntimeError(payload)

    def read_summary_only(self) -> List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]]:
        """
        Synchronously read Summary!C4:K55 from the live Excel workbook.
        (No recalc or write.)
        """
        reply_q: "queue.Queue" = queue.Queue()
        self._cmd_q.put({
            "type": "read_only",
            "reply_q": reply_q,
        })
        status, payload = reply_q.get()
        if status == "ok":
            return payload
        else:
            raise RuntimeError(payload)

    def shutdown(self):
        """Ask the worker to close workbook + Excel and exit the thread."""
        self._stop_flag.set()
        self._cmd_q.put({"type": "stop"})
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    # ---------- internal worker-thread methods ----------

    def _run(self):
        """Worker thread main loop: owns Excel COM objects."""
        logger.info("[ExcelWorker] Thread started.")

        try:
            self._app = xw.App(visible=False, add_book=False)
            logger.info("[ExcelWorker] Excel App created (hidden).")

            # Capture original settings and harden against prompts/macros
            try:
                self._alerts_original = self._app.display_alerts
                self._app.display_alerts = False
                logger.debug("[ExcelWorker] display_alerts -> False")
            except Exception:
                self._alerts_original = None

            try:
                self._events_original = self._app.api.EnableEvents
                self._app.api.EnableEvents = False
                logger.debug("[ExcelWorker] EnableEvents -> False")
            except Exception as e:
                logger.warning(f"[ExcelWorker] Failed to disable events: {e}")
                self._events_original = None

            try:
                # 1=Low, 2=ByUI, 3=ForceDisable
                self._auto_sec_original = self._app.api.AutomationSecurity
                self._app.api.AutomationSecurity = 3
                logger.debug("[ExcelWorker] AutomationSecurity -> ForceDisable (3)")
            except Exception as e:
                logger.warning(f"[ExcelWorker] Failed to set AutomationSecurity: {e}")
                self._auto_sec_original = None

            # Command loop
            while not self._stop_flag.is_set():
                try:
                    cmd = self._cmd_q.get(timeout=0.5)
                except queue.Empty:
                    continue

                if cmd["type"] == "stop":
                    logger.info("[ExcelWorker] Stop command received.")
                    break
                elif cmd["type"] == "open":
                    self._handle_open(cmd["path"])
                elif cmd["type"] == "write_and_read":
                    self._handle_write_and_read(cmd["margin_input"], cmd["reply_q"])
                elif cmd["type"] == "read_only":
                    self._handle_read_only(cmd["reply_q"])
                else:
                    logger.warning(f"[ExcelWorker] Unknown command type: {cmd['type']}")

        finally:
            self._cleanup_excel()
            logger.info("[ExcelWorker] Thread exiting.")

    def _handle_open(self, path: Path):
        """Open workbook path in this Excel session."""
        logger.info(f"[ExcelWorker] Opening workbook: {path}")
        self._ready_event.clear()
        self._last_error = None

        # Close previous book if any
        if self._book is not None:
            try:
                self._book.close()
            except Exception as e:
                logger.warning(f"[ExcelWorker] Error closing existing workbook: {e}")
            self._book = None

        try:
            t0 = time.perf_counter()
            self._book = self._app.books.open(
                fullname=str(path),
                update_links=False,
                read_only=False,
                ignore_read_only_recommended=True,
                notify=False,
                add_to_mru=False,
                local=True,
            )
            ms = (time.perf_counter() - t0) * 1000.0
            logger.info(f"[ExcelWorker] Workbook OPEN completed in {ms:.2f} ms. Sheets: {[s.name for s in self._book.sheets]}")
            self._ready_event.set()
        except Exception as e:
            self._book = None
            self._last_error = f"Failed to open workbook: {e}"
            logger.exception("[ExcelWorker] Failed to open workbook.")

    def _handle_write_and_read(self, margin_input: str, reply_q: "queue.Queue"):
        """Write margin to Summary!M24, recalc, then read Summary!C4:K55."""
        if self._book is None:
            msg = "Workbook not open in Excel worker."
            logger.error(f"[ExcelWorker] {msg}")
            reply_q.put(("error", msg))
            return

        try:
            val = to_number(margin_input)
            if val is None:
                raise ValueError(f"Could not parse margin value {margin_input!r}")

            ws = self._book.sheets[self.sheet_name]
            logger.info(f"[ExcelWorker] Writing {self.sheet_name}!{self.write_cell} = {val}")
            ws[self.write_cell].value = float(val)

            # Recalculate workbook
            try:
                logger.info("[ExcelWorker] Calculating workbook (Application.Calculate)...")
                self._app.api.Calculate()
            except Exception as e:
                logger.warning(f"[ExcelWorker] Calculate() failed: {e}")

            # Read Summary range
            rows = self._read_summary_internal(ws)
            reply_q.put(("ok", rows))
        except Exception as e:
            logger.exception("[ExcelWorker] write_and_read failed.")
            reply_q.put(("error", str(e)))

    def _handle_read_only(self, reply_q: "queue.Queue"):
        """Read Summary!C4:K55 from the open workbook without writing."""
        if self._book is None:
            msg = "Workbook not open in Excel worker."
            logger.error(f"[ExcelWorker] {msg}")
            reply_q.put(("error", msg))
            return
        try:
            ws = self._book.sheets[self.sheet_name]
            rows = self._read_summary_internal(ws)
            reply_q.put(("ok", rows))
        except Exception as e:
            logger.exception("[ExcelWorker] read_only failed.")
            reply_q.put(("error", str(e)))

    def _read_summary_internal(self, ws) -> List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]]:
        """Internal: read Summary!C4:K55 with xlwings and coerce values."""
        logger.debug(f"[ExcelWorker] Reading {self.sheet_name}!{self.read_range}")
        t0 = time.perf_counter()
        values = ws.range(self.read_range).value

        if values is None:
            values = []
        if values and not isinstance(values[0], (list, tuple)):
            values = [values]

        rows: List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]] = []
        total = 0
        skipped = 0
        for row in values:
            total += 1
            if not isinstance(row, (list, tuple)):
                continue
            row_list = list(row)
            if len(row_list) < 9:
                row_list = row_list + [None] * (9 - len(row_list))

            desc = coalesce_description(row_list[0:5])
            qty = to_number(row_list[5])
            cost = to_number(row_list[6])
            sell = to_number(row_list[7])
            margin = to_number(row_list[8])

            if not desc and all(x is None for x in (qty, cost, sell, margin)):
                skipped += 1
                continue

            rows.append((desc, qty, cost, sell, margin))

        elapsed = (time.perf_counter() - t0) * 1000.0
        logger.info(f"[ExcelWorker] Read Summary {self.read_range}: {len(rows)} row(s) returned, {skipped} skipped, {total} scanned in {elapsed:.2f} ms.")
        return rows

    def _cleanup_excel(self):
        """Restore Excel settings and close App/Book."""
        logger.info("[ExcelWorker] Cleaning up Excel session...")
        try:
            if self._book is not None:
                try:
                    self._book.close()
                except Exception as e:
                    logger.warning(f"[ExcelWorker] Error closing workbook: {e}")
                self._book = None

            if self._app is not None:
                try:
                    if self._events_original is not None:
                        try:
                            self._app.api.EnableEvents = self._events_original
                        except Exception:
                            pass
                    if self._auto_sec_original is not None:
                        try:
                            self._app.api.AutomationSecurity = self._auto_sec_original
                        except Exception:
                            pass
                    if self._alerts_original is not None:
                        try:
                            self._app.display_alerts = self._alerts_original
                        except Exception:
                            pass
                except Exception:
                    pass

                try:
                    self._app.quit()
                except Exception as e:
                    logger.warning(f"[ExcelWorker] Error quitting Excel: {e}")
                self._app = None
        except Exception:
            pass
