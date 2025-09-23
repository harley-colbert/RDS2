# RDS Local Sales Tool Architecture

## Overview

The solution replaces the legacy dual-workbook workflow with a local-first web application. It consists of a Flask backend, a SQLite database managed through SQLAlchemy, and a static HTMX/Tailwind frontend served by Flask. All generated outputs and templates live on the local filesystem so that the application can run completely offline on Windows.

## Directory Layout

```
backend/
  app/
    __init__.py        # Flask application factory
    api.py             # REST endpoints
    cel.py             # Costing Emulation Layer (CEL)
    config.py          # Configuration loader
    database.py        # SQLAlchemy engine/session helpers
    excel.py           # Costing workbook exporter
    formula.py         # Minimal Excel formula interpreter
    ingestion.py       # Workbook A ingestion utilities
    models.py          # ORM models
    services.py        # Quote orchestration service
frontend/
  index.html           # HTMX/Tailwind single-page shell
  static/
    js/app.js          # UI interaction logic
    css/tailwind.css   # Tailwind CDN reference
scripts/
  ingest_rds.py        # CLI ingestion helper
.tests/
  test_cel.py          # Unit tests for CEL rollups
  test_outputs.py      # Golden output checks
```

## Backend Components

* **Configuration:** `config.py` reads `config.json` or environment overrides, ensuring that template/output directories exist.
* **Database:** `database.py` provisions the SQLite database (`data/rds.db`) and exposes a `session_scope()` context manager for transactional operations.
* **Models:** The schema captures user inputs, pricing snapshots, the costing summary, individual costing items (mapped to `Summary!J*` cells), and a usage log that mirrors the historical Excel log behaviour.
* **Costing Emulation Layer:** `cel.py` builds a context for all `Summary!J*` cells, evaluates rollups, and enforces toggle semantics (H18/H19/...). It exposes helpers for Margin Change / Reset Margin operations and for exporting grid data to the UI.
* **Services:** `services.py` orchestrates quotes—loading/saving input data, recomputing totals, and logging usage. It also exposes `export_summary_for_workbook()` used by the Excel exporter.
* **Formula Engine:** `formula.py` provides a minimal interpreter capable of `SUM` and arithmetic operators, sufficient for the known `J*` rollups.
* **Outputs:** `excel.py` and `word.py` produce the Costing workbook and Proposal documents. The Excel writer prefers `.xlsb` via COM (when available) and falls back to `.xlsx` everywhere else. The Word writer replaces bookmarks and optionally produces a PDF using `docx2pdf` when installed.
* **Ingestion:** `ingestion.py`/`scripts/ingest_rds.py` parse Workbook A and cache the structure under `./.cache/spec/rds_spec.json` for traceability.

## Frontend

The frontend uses a lightweight HTMX-like interaction model implemented in plain JavaScript. Two tabs mirror the original Excel experience:

1. **Inputs & Pricing:** Allows editing of the quote metadata and raw configuration JSON, triggers recomputation, and shows live pricing totals.
2. **Costing Grid:** Displays the emulated `Summary!J*` values, toggle states, and derived margin/sell price. Toggles are interactive and dispatch updates back to the backend.

Buttons for **Margin Change**, **Reset Margin**, and **Generate Outputs** interact with dedicated backend routes (the generate endpoint is stubbed in the UI and ready to be wired into the backend service).

## Data Flow

1. User edits inputs or toggles → frontend POSTs to `/api`.
2. Backend service updates `rds_inputs`, recomputes the costing summary via the CEL, updates `pricing`, and persists toggles/margin.
3. Response returns updated totals/toggles/pricing for real-time UI refresh.
4. When generation is invoked, the backend will produce:
   * Costing workbook (`01 - Q#<Quote> - Costing.xlsx` fallback) via `CostingWorkbookWriter`.
   * Word proposal and optional PDF via `ProposalWriter`.
   * Usage log entry in `usage_log`.

## Cell Map

| Workbook Cell | Database Field / Key       | Source | Notes |
| ------------- | -------------------------- | ------ | ----- |
| `Summary!H18` | `costing_summary.toggles`   | UI     | Infeed conveyor toggle 1 |
| `Summary!H19` | `costing_summary.toggles`   | UI     | Infeed conveyor toggle 2 |
| `Summary!H20` | `costing_summary.toggles`   | UI     | Infeed conveyor toggle 3 |
| `Summary!H32` | `costing_summary.toggles`   | UI     | Guarding standard |
| `Summary!H33` | `costing_summary.toggles`   | UI     | Guarding custom |
| `Summary!H38` | `costing_summary.toggles`   | UI     | Spare blades |
| `Summary!H39` | `costing_summary.toggles`   | UI     | Spare foam |
| `Summary!H40` | `costing_summary.toggles`   | UI     | Spare misc |
| `Summary!H45` | `costing_summary.toggles`   | UI     | Misc install |
| `Summary!H46` | `costing_summary.toggles`   | UI     | Misc training |
| `Summary!H47` | `costing_summary.toggles`   | UI     | Misc freight |
| `Summary!M4`  | `costing_summary.margin`    | UI/API | Margin Change/Reset |
| `Summary!J*`  | `costing_items.metadata_json.summary_cell` | CEL | Stored per costing item |
| `Sheet3!B2`   | `pricing.subtotal`          | CEL    | `SUM(J4:J10,J14,J17,J24,J31)` |
| `Sheet3!B3:B5`| `totals[J38:J40]`           | CEL    | Spare parts costing |
| `Sheet3!B6:B7`| `totals[J32:J33]`           | CEL    | Guarding costing |
| `Sheet3!B8:B10`| `totals[J18:J20]`          | CEL    | Infeed conveyor costing |
| `Sheet3!B11:B13`| `totals[J45:J47]`         | CEL    | Misc costing |
| `Sheet1!B12`  | `pricing.margin`            | CEL    | Mirror of Summary!M4 |

## Runbook

1. **Create virtual environment:** `python -m venv .venv` and `source .venv/bin/activate` (or `Scripts\activate` on Windows).
2. **Install dependencies:** `pip install -r requirements.txt` (see README for the list). Windows users who need `.xlsb`/PDF exports must also install Microsoft Office (for COM automation) and `docx2pdf`.
3. **Configure (optional):** Copy `config.example.json` to `config.json` and adjust paths for templates/output.
4. **Ingest Workbook A:** `python scripts/ingest_rds.py "RDS Sales Tool -hrc.xlsm"` to populate `./.cache/spec/rds_spec.json`.
5. **Run the app:** `flask --app backend.app:create_app run` (set `FLASK_ENV=development` for autoreload).
6. **Run tests:** `pytest`.

Outputs are written under `./output` following the naming convention described in the spec.
