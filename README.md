# RDS Local Sales Tool

Local-first replacement for the legacy `RDS Sales Tool.xlsm` + `Costing.xlsb` workflow. The application exposes a browser UI for quote configuration, emulates the Costing workbook, and generates the required Excel/Word outputs.

## Features

* **Workbook A ingestion** via `scripts/ingest_rds.py` – produces `./.cache/spec/rds_spec.json` for traceability.
* **Costing Emulation Layer (CEL)** replicates the Summary/Sell Price List interface required by Workbook A, including toggle enforcement and margin rollups.
* **Live pricing** view for Tab 1 (Inputs & Pricing) and **Costing grid** for Tab 2.
* **Output generators** for Costing Excel (`.xlsb` when COM is available, `.xlsx` fallback) and Word proposal (`.docx` + `.pdf` when `docx2pdf` is installed).
* **Usage log** persists every major operation in SQLite.

## Getting Started

1. **Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configuration**
   Copy `config.example.json` to `config.json` and adjust template/output directories if desired. Default folders:
   * Templates: `./data/templates`
   * Outputs: `./output`

3. **Ingest Workbook A**
   Copy your local copy of `RDS Sales Tool.xlsm` into the repository (the file is not tracked in git) or provide an absolute path, then run:
   ```bash
   python scripts/ingest_rds.py "/path/to/RDS Sales Tool.xlsm"
   ```

4. **Run the App**
   ```bash
   flask --app backend.app:create_app run
   ```
   Navigate to `http://127.0.0.1:5000/frontend/index.html` (or serve the frontend via Flask static routes).

5. **Generate Outputs** (to be wired to a backend endpoint)
   * Costing workbook: `backend.app.excel.CostingWorkbookWriter`
   * Proposal: `backend.app.word.ProposalWriter`

## Tests

Run the automated tests with:

```bash
pytest
```

## Templates & Sample Data

Place proprietary template files under `./data/templates` (folder retained with a README, templates themselves are gitignored):

* `costing_template.xlsx` – minimal workbook used for fallback output.
* `proposal_template.docx` – contains bookmarks such as `[QuoteNum]`, `[Customer]`, `[BasePrice]`, etc.

Seed data can be inserted via `RDSService.ensure_seed_costing()` to pre-populate costing items.

## Windows Notes

* `.xlsb` export requires Microsoft Excel with COM automation enabled.
* PDF export via `docx2pdf` also relies on Word. When unavailable, the `.pdf` output is skipped and a warning is logged.

## Logging

All generation events are appended to the `usage_log` table. A future enhancement can expose this log via the UI or a CSV export.
