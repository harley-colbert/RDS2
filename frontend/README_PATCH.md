# Patch – Excel Cost Sheet Integration

This patch adds:
- Backend startup hook to optionally open the costing workbook
- `/api/cost-sheet/path` and `/api/cost-sheet/summary` endpoints
- A right-side UI panel that displays `Summary!C4:K55` as a live grid

## Configure
Set env vars (or .env) for defaults:
```bash
RDS_COST_SHEET_PATH="C:\\path\\to\\Costing.xlsb"
RDS_XLWINGS_VISIBLE=false
RDS_SUMMARY_SHEET_NAME=Summary
RDS_SUMMARY_READ_RANGE=C4:K55
```

## Backend
- `backend/app/config.py` – adds `get_cost_settings()`
- `backend/app/excel_xlwings.py` – Excel manager for open/read/close
- `backend/app/cost_sheet_service.py` – facade to read summary range
- `backend/routers/cost_sheet.py` – API endpoints
- `backend/routers/__init__.py` – includes the router
- `backend/server.py` – FastAPI app with lifespan (open at startup)

Install deps:
```bash
pip install -r requirements.txt
```

Run (example):
```bash
uvicorn backend.server:app --host 0.0.0.0 --port 7600 --reload
```

## Frontend
- `frontend/src/components/ExcelSummaryPanel.tsx` – new panel
- `frontend/src/components/CostSheetPathSelector.tsx` – optional path setter
- `frontend/src/pages/QuoteBuilder.tsx` – updated layout to 3 columns

Replace placeholders with your existing panels and import this page where appropriate.
