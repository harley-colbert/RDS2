from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Optional readers
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore


class AttrDict(dict):
    """Dict with attribute access (x.y)."""
    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e
    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value
    def __delattr__(self, name: str) -> None:
        del self[name]


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


# ------------------------------------------------------------------
# DEFAULT_CONFIG with BOTH shapes:
# - Flat, UPPERCASE keys (legacy code like database.py expects)
# - Nested sections (newer code expects)
# ------------------------------------------------------------------
DEFAULT_CONFIG: AttrDict = AttrDict({
    # Flat (legacy) ------------------------
    "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
    "DATABASE_ECHO": _env_flag("DATABASE_ECHO", "false"),
    "EXCEL_TEMPLATE": os.getenv("EXCEL_TEMPLATE", "./data/templates/costing_template.xlsx"),
    "ALLOW_XLSB": _env_flag("ALLOW_XLSB", "false"),
    "COST_SHEET_PATH": os.getenv("RDS_COST_SHEET_PATH") or os.getenv("COST_SHEET_PATH"),
    "XLWINGS_VISIBLE": _env_flag("RDS_XLWINGS_VISIBLE", "false"),
    "SUMMARY_SHEET_NAME": os.getenv("RDS_SUMMARY_SHEET_NAME", "Summary"),
    "SUMMARY_READ_RANGE": os.getenv("RDS_SUMMARY_READ_RANGE", "C4:K55"),
    "SERVER_HOST": os.getenv("SERVER_HOST", "0.0.0.0"),
    "SERVER_PORT": int(os.getenv("SERVER_PORT", "7600")),
    "DEBUG": _env_flag("DEBUG", "false"),
    # Nested (modern) ----------------------
    "server": {
        "host": os.getenv("SERVER_HOST", "0.0.0.0"),
        "port": int(os.getenv("SERVER_PORT", "7600")),
        "debug": _env_flag("DEBUG", "false"),
    },
    "database": {
        "url": os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
        "echo": _env_flag("DATABASE_ECHO", "false"),
    },
    "excel": {
        "template": os.getenv("EXCEL_TEMPLATE", "./data/templates/costing_template.xlsx"),
        "allow_xlsb": _env_flag("ALLOW_XLSB", "false"),
    },
    "cost_sheet": {
        "path": os.getenv("RDS_COST_SHEET_PATH") or os.getenv("COST_SHEET_PATH"),
        "visible": _env_flag("RDS_XLWINGS_VISIBLE", "false"),
        "summary_sheet_name": os.getenv("RDS_SUMMARY_SHEET_NAME", "Summary"),
        "summary_read_range": os.getenv("RDS_SUMMARY_READ_RANGE", "C4:K55"),
    },
})


def _read_config_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    ext = path.suffix.lower()
    if ext == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if ext in {".yml", ".yaml"} and yaml is not None:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if ext == ".toml" and tomllib is not None:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    # Fallback: try JSON
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Unsupported config format for {path}. {e}")


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def _ensure_compat_keys(cfg: Dict[str, Any]) -> None:
    """Ensure both flat and nested keys exist based on whichever are provided.
    This keeps old and new modules happy without changing their imports."""
    # If nested present but flat missing -> synthesize flat
    if "database" in cfg:
        db = cfg["database"]
        cfg.setdefault("DATABASE_URL", db.get("url"))
        cfg.setdefault("DATABASE_ECHO", db.get("echo"))
    if "excel" in cfg:
        ex = cfg["excel"]
        cfg.setdefault("EXCEL_TEMPLATE", ex.get("template"))
        cfg.setdefault("ALLOW_XLSB", ex.get("allow_xlsb"))
    if "cost_sheet" in cfg:
        cs = cfg["cost_sheet"]
        cfg.setdefault("COST_SHEET_PATH", cs.get("path"))
        cfg.setdefault("XLWINGS_VISIBLE", cs.get("visible"))
        cfg.setdefault("SUMMARY_SHEET_NAME", cs.get("summary_sheet_name"))
        cfg.setdefault("SUMMARY_READ_RANGE", cs.get("summary_read_range"))
    if "server" in cfg:
        sv = cfg["server"]
        cfg.setdefault("SERVER_HOST", sv.get("host"))
        cfg.setdefault("SERVER_PORT", sv.get("port"))
        cfg.setdefault("DEBUG", sv.get("debug"))
    # If flat present but nested missing -> synthesize nested
    cfg.setdefault("database", {})
    cfg["database"].setdefault("url", cfg.get("DATABASE_URL"))
    cfg["database"].setdefault("echo", cfg.get("DATABASE_ECHO"))
    cfg.setdefault("excel", {})
    cfg["excel"].setdefault("template", cfg.get("EXCEL_TEMPLATE"))
    cfg["excel"].setdefault("allow_xlsb", cfg.get("ALLOW_XLSB"))
    cfg.setdefault("cost_sheet", {})
    cfg["cost_sheet"].setdefault("path", cfg.get("COST_SHEET_PATH"))
    cfg["cost_sheet"].setdefault("visible", cfg.get("XLWINGS_VISIBLE"))
    cfg["cost_sheet"].setdefault("summary_sheet_name", cfg.get("SUMMARY_SHEET_NAME"))
    cfg["cost_sheet"].setdefault("summary_read_range", cfg.get("SUMMARY_READ_RANGE"))
    cfg.setdefault("server", {})
    cfg["server"].setdefault("host", cfg.get("SERVER_HOST"))
    cfg["server"].setdefault("port", cfg.get("SERVER_PORT"))
    cfg["server"].setdefault("debug", cfg.get("DEBUG"))


def load_config(config_path: Optional[str] = None) -> AttrDict:
    """Backward-compatible loader used by run.py and other modules.
    - Start from DEFAULT_CONFIG
    - If a config file is provided, deep-merge it on top
    - Ensure both flat and nested keys are present
    - Return an AttrDict for dict+attribute access
    """
    base = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_CONFIG.items()}
    if config_path:
        p = Path(config_path)
        if p.exists():
            _deep_merge(base, _read_config_file(p) or {})
    _ensure_compat_keys(base)
    return AttrDict(base)


# New helper used by the cost-sheet endpoints / services.
@dataclass(frozen=True)
class CostSettings:
    cost_sheet_path: Optional[str] = None
    xlwings_visible: bool = False
    summary_sheet_name: str = "Summary"
    summary_read_range: str = "C4:K55"


def get_cost_settings() -> CostSettings:
    cfg = load_config()  # prefer values from file/env merged with defaults
    cs = cfg.get("cost_sheet", {})
    return CostSettings(
        cost_sheet_path=cs.get("path"),
        xlwings_visible=bool(cs.get("visible", False)),
        summary_sheet_name=str(cs.get("summary_sheet_name", "Summary")),
        summary_read_range=str(cs.get("summary_read_range", "C4:K55")),
    )
