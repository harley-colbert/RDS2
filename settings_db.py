import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional
import datetime

DB_PATH = Path.home() / ".xlsm_viewer.db"


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """
    Create DB and tables if they don't exist.
    Tables:
      - settings(key TEXT PRIMARY KEY, value TEXT)
      - margin_changes(id INTEGER PRIMARY KEY AUTOINCREMENT,
                       ts TEXT, old_margin REAL, new_margin REAL)
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS margin_changes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT NOT NULL,
                old_margin REAL,
                new_margin REAL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# ---------- cost sheet path ----------

def get_cost_sheet_path() -> Optional[Path]:
    """Return stored cost sheet path, or None if not set."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'cost_sheet_path'")
        row = cur.fetchone()
        if not row:
            return None
        p = Path(row[0])
        return p
    finally:
        conn.close()


def set_cost_sheet_path(path: Path) -> None:
    """Store/update the cost sheet path."""
    conn = _get_conn()
    try:
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
    finally:
        conn.close()


# ---------- margin change log ----------

def add_margin_change(old_margin: Optional[float], new_margin: Optional[float]) -> None:
    """
    Add a new margin change record.
    old_margin / new_margin are stored as REAL or NULL.
    """
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO margin_changes(ts, old_margin, new_margin)
            VALUES(?, ?, ?)
            """,
            (ts, old_margin, new_margin),
        )
        conn.commit()
    finally:
        conn.close()


def get_margin_changes() -> List[Tuple[int, str, Optional[float], Optional[float]]]:
    """
    Return list of (id, ts, old_margin, new_margin) ordered by id ASC.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ts, old_margin, new_margin
            FROM margin_changes
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in rows]
    finally:
        conn.close()


def clear_margin_changes() -> None:
    """Delete all margin change records."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM margin_changes")
        conn.commit()
    finally:
        conn.close()
