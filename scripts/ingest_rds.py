from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.app.ingestion import WorkbookIngestor


DEFAULT_CONFIG = {
    "SPEC_CACHE": "./.cache/spec/rds_spec.json",
}


def load_config(config_path: Path | None):
    config = DEFAULT_CONFIG.copy()
    if config_path and config_path.exists():
        config.update(json.loads(config_path.read_text()))
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest RDS Sales Tool workbook")
    parser.add_argument("workbook", type=Path, help="Path to RDS Sales Tool workbook (.xlsm)")
    parser.add_argument("--config", type=Path, default=None, help="Path to config JSON")
    args = parser.parse_args()

    config = load_config(args.config)
    output = Path(config["SPEC_CACHE"])
    ingestor = WorkbookIngestor(args.workbook)
    spec = ingestor.dump(output)
    print(f"Wrote spec to {output} ({len(spec['sheets'])} sheets)")
