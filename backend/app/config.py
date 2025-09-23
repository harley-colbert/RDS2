from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG = {
    "DATABASE_URL": "sqlite:///./data/rds.db",
    "TEMPLATE_DIR": "./data/templates",
    "OUTPUT_DIR": "./output",
    "SPEC_CACHE": "./.cache/spec/rds_spec.json",
    "EXCEL_TEMPLATE": "./data/templates/costing_template.xlsx",
    "WORD_TEMPLATE": "./data/templates/proposal_template.docx",
    "ALLOW_XLSB": False,
}


class ConfigError(RuntimeError):
    pass


def load_config(config_path: str | None = None) -> Dict[str, Any]:
    """Load configuration from JSON file or environment variables."""
    config: Dict[str, Any] = DEFAULT_CONFIG.copy()

    env_path = config_path or os.getenv("RDS_CONFIG")
    if env_path:
        path = Path(env_path)
        if not path.exists():
            raise ConfigError(f"Config file {path} not found")
        with path.open("r", encoding="utf-8") as fh:
            config.update(json.load(fh))

    # Allow environment overrides for selected keys
    for key in list(config):
        if key in os.environ:
            config[key] = os.environ[key]

    Path(config["TEMPLATE_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(config["OUTPUT_DIR"]).mkdir(parents=True, exist_ok=True)

    return config
