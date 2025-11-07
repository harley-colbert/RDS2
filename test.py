import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from typing import List, Tuple, Optional
import math
import logging
import warnings
import sys
import time
import sqlite3

import xlwings as xw
from xlwings.constants import Calculation as XlCalc

# ===============================
# Constants
# ===============================

APP_TITLE = "Cost Sheet Viewer / Margin Controller"
WINDOW_MIN_WIDTH = 1300
WINDOW_MIN_HEIGHT = 800

SUMMARY_SHEET_NAME = "Summary"
READ_RANGE = "C4:K55"
WRITE_CELL = "M4"

DB_PATH = Path.home() / ".cost_sheet_app.sqlite3"


# ===============================
# Logging & Warnings Configuration
# ===============================

class _WarningsToLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def __call__(self, message, category, filename, lineno, file=None, line=None):
        msg = warnings.formatwarning(message, category, filename, lineno, line)
        sys.stderr.write(msg)


logger = logging.getLogger("CostSheetApp")
logger.setLevel(logging.DEBUG)
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.DEBUG)
_console_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(_console_handler)
warnings.showwarning = _WarningsToLogger(logger)


# ===============================
# Utility Functions
# ===============================

def to_number(val):
    """Robust numeric coercion used for reading quantities, costs, margins."""
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


def coalesce_description(values) -> str:
    """Merge description cells C..G into a single string."""
    parts = []
    for v in values:
        if v is not None:
            text = str(v).strip()
            if text:
                parts.append(text.replace("\n", " "))
    return " ".join(parts).strip()


# ===============================
# SQLite Database Helper
# ===============================

class AppDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS margin_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    changed_at TEXT DEFAULT (datetime('now')),
                    old_margin REAL,
                    new_margin REAL
                )
                """
            )
            conn.commit()

    def get_cost_sheet_path(self) -> Optional[Path]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = 'cost_sheet_path'")
            row = cur.fetchone()
            if not row:
                return None
            path_str = row[0]
            p = Path(path_str)
            return p

    def set_cost_sheet_path(self, path: Path) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO settings(key, value)
                VALUES('cost_sheet_path', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(path),),
            )
            conn.commit()

    def add_margin_change(self, old_margin: Optional[float], new_margin: Optional[float]) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO margin_log(old_margin, new_margin)
                VALUES (?, ?)
                """,
                (old_margin, new_margin),
            )
            conn.commit()

    def get_margin_log(self, limit: Optional[int] = None):
        sql = "SELECT changed_at, old_margin, new_margin FROM margin_log ORDER BY id DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return cur.fetchall()

    def clear_margin_log(self) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM margin_log")
            conn.commit()


# ===============================
# Tk Log Handler
# ===============================

class TkTextHandler(logging.Handler):
    def __init__(self, text_widget: ScrolledText):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))

    def emit(self, record):
        msg = self.format(record)
        try:
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.configure(state="disabled")
            self.text_widget.yview_moveto(1.0)
        except Exception:
            pass


# ===============================
# Main Tkinter App
# ===============================

class XlsmViewerWriterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Database
        self.db = AppDatabase(DB_PATH)

        # Excel state
        self.cost_sheet_path: Optional[Path] = self.db.get_cost_sheet_path()
        self.xw_app: Optional[xw.App] = None
        self.xw_book: Optional[xw.Book] = None
        self.book_dirty: bool = False

        # UI state
        self.splash: Optional[tk.Toplevel] = None

        # Build UI skeleton
        self._build_widgets()
        self._attach_gui_logger()
        self._configure_layout()
        self._load_margin_log_sidebar()
        self._init_cost_sheet_path_entry()

        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        logger.info("Application created.")
        # Startup processing: splash + auto-open if a cost sheet is configured
        self._startup_process()

    # ---------- UI building ----------

    def _build_widgets(self):
        # Top settings frame: cost sheet path + browse + process
        self.settings_frame = ttk.LabelFrame(self, text="Cost Sheet Settings")
        self.lbl_cost_path = ttk.Label(self.settings_frame, text="Cost Sheet Path:")
        self.var_cost_path = tk.StringVar(value="")
        self.ent_cost_path = ttk.Entry(self.settings_frame, textvariable=self.var_cost_path, width=80)
        self.btn_browse = ttk.Button(self.settings_frame, text="Browse...", command=self.on_browse_cost_sheet)
        self.btn_process = ttk.Button(self.settings_frame, text="Process Cost Sheet Now", command=self.on_process)

        # Margin input block
        self.margin_frame = ttk.LabelFrame(self, text=f"Margin Control ({SUMMARY_SHEET_NAME}!{WRITE_CELL})")
        self.lbl_margin = ttk.Label(self.margin_frame, text=f"Apply Margin to {SUMMARY_SHEET_NAME}!{WRITE_CELL}:")
        self.ent_margin = ttk.Entry(self.margin_frame, width=20)
        self.ent_margin.insert(0, "12.5%")
        self.btn_apply_margin = ttk.Button(self.margin_frame, text="Apply Margin", command=self.on_apply_margin)
        self.hint_margin = ttk.Label(
            self.margin_frame,
            foreground="#666666",
            text="Changes apply inside Excel only during the session. Workbook is saved on app close."
        )

        # Center area: table on left, margin change log sidebar on right
        self.center_frame = ttk.Frame(self)

        # Summary table
        self.table_frame = ttk.LabelFrame(self.center_frame, text=f"Summary Table ({SUMMARY_SHEET_NAME}!{READ_RANGE})")
        columns = ("Description", "Qty", "Cost", "Sell Price", "Margin")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.column("Description", width=700, anchor="w")
        self.tree.column("Qty", width=80, anchor="e")
        self.tree.column("Cost", width=120, anchor="e")
        self.tree.column("Sell Price", width=120, anchor="e")
        self.tree.column("Margin", width=120, anchor="e")
        self.v_scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.h_scroll = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        # Margin log sidebar
        self.sidebar_frame = ttk.LabelFrame(self.center_frame, text="Margin Change Log (from DB)")
        self.margin_log_list = tk.Listbox(self.sidebar_frame, height=20)
        self.margin_log_scroll = ttk.Scrollbar(self.sidebar_frame, orient="vertical", command=self.margin_log_list.yview)
        self.margin_log_list.configure(yscrollcommand=self.margin_log_scroll.set)
        self.btn_clear_margin_log = ttk.Button(self.sidebar_frame, text="Clear Log", command=self.on_clear_margin_log)

        # Verbose log at bottom
        self.log_frame = ttk.LabelFrame(self, text="Verbose Log")
        self.log_text = ScrolledText(self.log_frame, height=10, wrap="word", state="disabled")
        self.btn_clear_log = ttk.Button(self.log_frame, text="Clear Verbose Log", command=self._clear_verbose_log)

    def _attach_gui_logger(self):
        gui_handler = TkTextHandler(self.log_text)
        gui_handler.setLevel(logging.DEBUG)
        logger.addHandler(gui_handler)
        logger.debug("GUI log handler attached to Tk Text widget.")

    def _configure_layout(self):
        # Settings row
        self.settings_frame.pack(fill="x", padx=10, pady=(10, 6))
        self.lbl_cost_path.grid(row=0, column=0, sticky="w", padx=(6, 4), pady=4)
        self.ent_cost_path.grid(row=0, column=1, sticky="we", padx=(0, 4), pady=4)
        self.btn_browse.grid(row=0, column=2, sticky="w", padx=(0, 4), pady=4)
        self.btn_process.grid(row=0, column=3, sticky="w", padx=(0, 6), pady=4)
        self.settings_frame.columnconfigure(1, weight=1)

        # Margin row
        self.margin_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.lbl_margin.grid(row=0, column=0, sticky="w", padx=(6, 10), pady=4)
        self.ent_margin.grid(row=0, column=1, sticky="w", pady=4)
        self.btn_apply_margin.grid(row=0, column=2, sticky="w", padx=(10, 6), pady=4)
        self.hint_margin.grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 6))

        # Center area: summary table + margin log
        self.center_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.sidebar_frame.grid(row=0, column=1, sticky="ns", padx=(6, 0))

        self.center_frame.rowconfigure(0, weight=1)
        self.center_frame.columnconfigure(0, weight=3)
        self.center_frame.columnconfigure(1, weight=1)

        # Table layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.table_frame.rowconfigure(0, weight=1)
        self.table_frame.columnconfigure(0, weight=1)

        # Sidebar layout
        self.margin_log_list.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self.margin_log_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)
        self.btn_clear_margin_log.grid(row=1, column=0, columnspan=2, sticky="e", padx=6, pady=(0, 6))
        self.sidebar_frame.rowconfigure(0, weight=1)
        self.sidebar_frame.columnconfigure(0, weight=1)

        # Verbose log at bottom
        self.log_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10))
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.btn_clear_log.pack(anchor="e", padx=8, pady=(0, 8))

    def _clear_verbose_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ---------- Splash Screens ----------

    def _show_splash(self, title_text: str, message_text: str):
        if self.splash is not None:
            return
        self.splash = tk.Toplevel(self)
        self.splash.title(title_text)
        self.splash.geometry("500x200")
        self.splash.resizable(False, False)
        self.splash.transient(self)
        self.splash.grab_set()

        lbl_title = ttk.Label(self.splash, text=title_text, font=("Segoe UI", 14, "bold"))
        lbl_title.pack(pady=(20, 10))
        lbl_msg = ttk.Label(self.splash, text=message_text, font=("Segoe UI", 11))
        lbl_msg.pack(pady=(0, 20))

        # Simple "dashing bar" text (static)
        bar = ttk.Label(self.splash, text=">>>>>>>>>>>>>>>>>>>>>>>>", foreground="#0078D4")
        bar.pack()

        self.splash.update_idletasks()

    def _hide_splash(self):
        if self.splash is not None:
            try:
                self.splash.destroy()
            except Exception:
                pass
            self.splash = None

    # ---------- DB-related UI ----------

    def _init_cost_sheet_path_entry(self):
        if self.cost_sheet_path is not None:
            self.var_cost_path.set(str(self.cost_sheet_path))
        else:
            self.var_cost_path.set("")

    def _load_margin_log_sidebar(self):
        self.margin_log_list.delete(0, "end")
        rows = self.db.get_margin_log(limit=200)
        for changed_at, old_margin, new_margin in rows:
            old_text = "" if old_margin is None else f"{old_margin:.6f}"
            new_text = "" if new_margin is None else f"{new_margin:.6f}"
            display = f"{changed_at}: {old_text} -> {new_text}"
            self.margin_log_list.insert("end", display)

    def on_clear_margin_log(self):
        if messagebox.askyesno("Clear Margin Log", "Clear all margin change log entries from the database?"):
            self.db.clear_margin_log()
            self._load_margin_log_sidebar()
            logger.info("Margin log cleared from DB.")

    # ---------- Excel Helpers ----------

    def _ensure_excel_app(self):
        if self.xw_app is not None:
            return
        logger.info("Starting hidden Excel instance via xlwings.")
        app = xw.App(visible=False, add_book=False)
        # Reduce popups and events
        try:
            app.display_alerts = False
        except Exception:
            pass
        try:
            app.screen_updating = False
        except Exception:
            pass
        try:
            app.api.EnableEvents = False
        except Exception:
            pass
        try:
            # 3 = ForceDisable macros
            app.api.AutomationSecurity = 3
        except Exception:
            pass
        self.xw_app = app

    def _open_workbook_excel(self, path: Path):
        self._ensure_excel_app()
        logger.info(f"Opening cost sheet in Excel via xlwings: {path}")
        open_start = time.perf_counter()
        try:
            book = self.xw_app.books.open(
                fullname=str(path),
                update_links=False,
                read_only=False,
                ignore_read_only_recommended=True,
                notify=False,
                add_to_mru=False,
                local=True,
            )
        except Exception as e:
            logger.exception("Failed to open workbook in Excel.")
            raise

        open_ms = (time.perf_counter() - open_start) * 1000.0
        logger.info(f"Workbook OPEN completed in {open_ms:.2f} ms.")
        self.xw_book = book
        self.book_dirty = False

    def _close_excel(self):
        logger.info("Closing Excel workbook and application.")
        try:
            if self.xw_book is not None:
                try:
                    self.xw_book.close()
                except Exception as e:
                    logger.warning(f"Error closing workbook: {e}")
                self.xw_book = None
        finally:
            if self.xw_app is not None:
                try:
                    self.xw_app.quit()
                except Exception as e:
                    logger.warning(f"Error quitting Excel app: {e}")
                self.xw_app = None

    def _read_summary_from_excel(self) -> List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]]:
        if self.xw_book is None:
            raise RuntimeError("Workbook is not open; cannot read Summary.")
        ws = self.xw_book.sheets[SUMMARY_SHEET_NAME]
        logger.info(f"Reading {SUMMARY_SHEET_NAME}!{READ_RANGE} from Excel.")
        t0 = time.perf_counter()
        values = ws.range(READ_RANGE).value  # 2D list
        read_ms = (time.perf_counter() - t0) * 1000.0
        logger.info(f"Summary range read from Excel in {read_ms:.2f} ms.")

        rows: List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]] = []
        total = 0
        skipped = 0
        for row in values:
            total += 1
            desc_vals = row[0:5]
            qty_val = row[5]
            cost_val = row[6]
            sell_val = row[7]
            margin_val = row[8]

            description = coalesce_description(desc_vals)
            qty = to_number(qty_val)
            cost = to_number(cost_val)
            sell = to_number(sell_val)
            margin = to_number(margin_val)

            if not description and all(x is None for x in (qty, cost, sell, margin)):
                skipped += 1
                continue

            rows.append((description, qty, cost, sell, margin))

        logger.info(f"Summary parsed: {len(rows)} row(s) returned, {skipped} skipped as empty, {total} scanned.")
        return rows

    def _write_margin_and_recalc(self, margin_input: str, save_to_disk: bool) -> Tuple[Optional[float], Optional[float]]:
        """
        Write margin to Summary!M24, recalc, and optionally save workbook.

        Returns (old_margin, new_margin) as floats or None.
        """
        if self.xw_book is None:
            raise RuntimeError("Workbook is not open; cannot write margin.")

        ws = self.xw_book.sheets[SUMMARY_SHEET_NAME]

        # Read before
        try:
            before_raw = ws.range(WRITE_CELL).value
            before_margin = to_number(before_raw)
        except Exception as e:
            before_raw = None
            before_margin = None
            logger.warning(f"Could not read {SUMMARY_SHEET_NAME}!{WRITE_CELL} before write: {e}")

        logger.info(
            f"BEFORE write: {SUMMARY_SHEET_NAME}!{WRITE_CELL} raw={before_raw!r}, parsed={before_margin}"
        )

        # Parse input
        raw = margin_input.strip()
        margin_val = to_number(raw)
        if margin_val is None:
            raise ValueError(f"Could not parse margin value from '{margin_input}'")

        # Write new value
        logger.info(f"Writing {SUMMARY_SHEET_NAME}!{WRITE_CELL} = {float(margin_val)} (parsed from '{margin_input}')")
        ws.range(WRITE_CELL).value = float(margin_val)

        # Sheet-only recalc, then fallback to app-wide if needed
        t_calc0 = time.perf_counter()
        sheet_calc_ok = False
        try:
            ws.api.Calculate()
            sheet_calc_ok = True
            logger.info("Called Summary.Calculate() (sheet-only recalc).")
        except Exception as e:
            logger.warning(f"Summary.Calculate() failed with {e}. Falling back to Application.Calculate().")
            try:
                self.xw_app.api.Calculation = XlCalc.xlCalculationAutomatic
                self.xw_app.calculate()
                logger.info("Called Application.Calculate() (full workbook recalc).")
            except Exception as e2:
                logger.error(f"Application.Calculate() also failed: {e2}")
        calc_ms = (time.perf_counter() - t_calc0) * 1000.0
        logger.info(f"Recalculation finished in {calc_ms:.2f} ms (sheet_only={sheet_calc_ok}).")

        # Read after
        try:
            after_raw = ws.range(WRITE_CELL).value
            after_margin = to_number(after_raw)
        except Exception as e:
            after_raw = None
            after_margin = None
            logger.warning(f"Could not read {SUMMARY_SHEET_NAME}!{WRITE_CELL} after calc: {e}")

        logger.info(
            f"AFTER calc: {SUMMARY_SHEET_NAME}!{WRITE_CELL} raw={after_raw!r}, parsed={after_margin}"
        )

        # Save decision
        if save_to_disk:
            t_save0 = time.perf_counter()
            self.xw_book.save()
            save_ms = (time.perf_counter() - t_save0) * 1000.0
            logger.info(f"Workbook SAVE completed in {save_ms:.2f} ms.")
            self.book_dirty = False
        else:
            if after_margin is not None and after_margin != before_margin:
                self.book_dirty = True
                logger.info("Workbook marked dirty (changes will be saved on app close).")
            else:
                logger.info("Margin did not change; workbook not marked dirty.")

        return before_margin, after_margin

    # ---------- App startup and main workflow ----------

    def _startup_process(self):
        """
        At app launch:
          - If a cost sheet path is configured and exists, show splash and open it.
          - Read Summary table and populate UI.
        """
        path = self.cost_sheet_path
        if path is None:
            logger.info("No cost sheet path configured in DB. Waiting for user to set one.")
            return

        if not path.exists():
            logger.warning(f"Configured cost sheet path does not exist: {path}")
            messagebox.showwarning(
                "Cost Sheet Not Found",
                f"The configured cost sheet file does not exist:\n{path}\n\n"
                "Please use Browse to set a valid file and click Process."
            )
            return

        # Show splash and open workbook
        self._show_splash("Opening Cost Sheet", "Opening cost sheet in background Excel instance.\nThis may take several seconds.")
        try:
            self._open_workbook_excel(path)
            rows = self._read_summary_from_excel()
            self._populate_table(rows)
        except Exception as e:
            logger.exception("Startup processing failed.")
            messagebox.showerror("Error Opening Cost Sheet", f"Failed to open or read cost sheet:\n{e}")
        finally:
            self._hide_splash()

    # ---------- UI Event Handlers ----------

    def on_browse_cost_sheet(self):
        filetypes = [("Excel Macro-Enabled Workbook", "*.xlsm"), ("All files", "*.*")]
        path_str = filedialog.askopenfilename(title="Select Cost Sheet (.xlsm)", filetypes=filetypes)
        if not path_str:
            logger.info("Browse cost sheet canceled by user.")
            return
        path = Path(path_str)
        if not path.exists():
            messagebox.showerror("File Not Found", f"The selected file does not exist:\n{path}")
            logger.error(f"User selected path that does not exist: {path}")
            return
        self.cost_sheet_path = path
        self.var_cost_path.set(str(path))
        self.db.set_cost_sheet_path(path)
        logger.info(f"Cost sheet path updated via Browse and saved to DB: {path}")

    def on_process(self):
        """
        Process Cost Sheet Now:
          - If Excel workbook is already open for the same path, just re-read Summary.
          - If open for a different path, close and reopen.
          - If not open, open fresh.
        """
        if not self.var_cost_path.get().strip():
            messagebox.showinfo("Set Cost Sheet", "Please select a cost sheet file first (Browse).")
            return

        path = Path(self.var_cost_path.get().strip())
        if not path.exists():
            messagebox.showerror("File Not Found", f"The cost sheet file does not exist:\n{path}")
            return

        self.cost_sheet_path = path
        self.db.set_cost_sheet_path(path)

        # If workbook is already open for a different file, close it
        if self.xw_book is not None:
            try:
                current_fullname = Path(self.xw_book.fullname)
            except Exception:
                current_fullname = None
            if current_fullname is not None and current_fullname != path:
                logger.info(f"Closing existing workbook {current_fullname} before opening new cost sheet {path}.")
                self._close_excel()

        # Show splash while processing
        self._show_splash("Processing Cost Sheet", "Opening cost sheet and loading Summary.\nPlease wait.")
        try:
            if self.xw_book is None:
                self._open_workbook_excel(path)
            rows = self._read_summary_from_excel()
            self._populate_table(rows)
        except Exception as e:
            logger.exception("Processing cost sheet failed.")
            messagebox.showerror("Process Error", f"Failed to process cost sheet:\n{e}")
        finally:
            self._hide_splash()

    def on_apply_margin(self):
        if self.cost_sheet_path is None:
            messagebox.showinfo("Set Cost Sheet", "Please select a cost sheet and click Process first.")
            return

        if self.xw_book is None:
            messagebox.showinfo("Workbook Not Open", "Please click 'Process Cost Sheet Now' to open the workbook.")
            return

        margin_input = self.ent_margin.get().strip()
        if not margin_input:
            messagebox.showinfo("Enter Margin", "Please enter a margin value (e.g., 12.5% or 0.125).")
            return

        logger.info(f"Applying margin '{margin_input}' to {SUMMARY_SHEET_NAME}!{WRITE_CELL} (no immediate disk save).")
        try:
            old_margin, new_margin = self._write_margin_and_recalc(margin_input, save_to_disk=False)
        except Exception as e:
            logger.exception("Margin write and recalc failed.")
            messagebox.showerror("Margin Error", f"Failed to write margin:\n{e}")
            return

        # Log margin change in DB if changed
        if new_margin is not None and new_margin != old_margin:
            try:
                self.db.add_margin_change(old_margin, new_margin)
                self._load_margin_log_sidebar()
                logger.info(f"Margin change logged to DB: {old_margin} -> {new_margin}")
            except Exception as e:
                logger.exception("Failed to log margin change to DB.")

        # Read Summary again from Excel (live values)
        try:
            rows = self._read_summary_from_excel()
        except Exception as e:
            logger.exception("Failed to read Summary from Excel after margin change.")
            messagebox.showerror("Read Error", f"Failed to read Summary after margin change:\n{e}")
            return

        self._populate_table(rows)

    def _populate_table(self, rows: List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float]]]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        def fmt(val: Optional[float], decimals: int = 2) -> str:
            if val is None:
                return ""
            if decimals == 0:
                return f"{int(round(val))}"
            return f"{val:,.{decimals}f}"

        inserted = 0
        for (desc, qty, cost, sell, margin) in rows:
            if qty is not None and abs(qty - round(qty)) < 1e-9:
                qty_s = fmt(qty, 0)
            else:
                qty_s = fmt(qty, 3) if qty is not None else ""
            cost_s = fmt(cost, 2)
            sell_s = fmt(sell, 2)
            margin_s = fmt(margin, 2)
            self.tree.insert("", "end", values=(desc, qty_s, cost_s, sell_s, margin_s))
            inserted += 1

        logger.info(f"UI table refreshed: {inserted} row(s) displayed.")

    def on_app_close(self):
        """
        App close sequence:
          1) If workbook is dirty, show splash "Saving cost grid" and save.
          2) Close workbook and Excel.
          3) Destroy Tk root.
        """
        logger.info("Application closing; checking whether workbook needs save.")
        # Save if dirty
        if self.xw_book is not None and self.book_dirty:
            self._show_splash("Saving Cost Grid", "Saving cost sheet to disk.\nPlease wait.")
            try:
                t_save0 = time.perf_counter()
                self.xw_book.save()
                save_ms = (time.perf_counter() - t_save0) * 1000.0
                logger.info(f"Workbook SAVE on app close completed in {save_ms:.2f} ms.")
            except Exception as e:
                logger.exception("Failed to save workbook on app close.")
                messagebox.showerror(
                    "Save Error",
                    f"Failed to save workbook on app close:\n{e}\n\n"
                    "Your changes in this session may not be written to disk."
                )
            finally:
                self._hide_splash()
        # Close Excel
        self._close_excel()
        logger.info("Tk application destroy.")
        self.destroy()


# ===============================
# Main Entry
# ===============================

if __name__ == "__main__":
    app = XlsmViewerWriterApp()
    try:
        app.mainloop()
    finally:
        logger.info("Application closed.")
