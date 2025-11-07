from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, Optional

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
_DB_PATH = os.path.join(_DB_DIR, "app.db")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class AppSettings:
    """Lightweight SQLite-backed key-value store for app settings."""

    _lock = threading.Lock()

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._lock, self._connect() as conn:
            cur = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row[0] if row else default

    def set(self, key: str, value: str) -> None:
        ts = datetime.utcnow().isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO app_settings(key, value, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, value, ts),
            )
            conn.commit()

    def all(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        with self._lock, self._connect() as conn:
            cur = conn.execute("SELECT key, value FROM app_settings ORDER BY key")
            for key, value in cur.fetchall():
                out[key] = value
        return out
