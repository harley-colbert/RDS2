# Phase 1 — Bootstrap & Orchestrator

## Goal
`python run.py` launches **backend (FastAPI) on :5581** and **frontend (static) on :5580** with CORS configured and a minimal skeleton.

## Scope
- Backend app factory with health check.
- Static frontend server (Python) serving `/app/frontend`.
- CORS allowlist for `http://localhost:5580` (and localhost variants).
- Repo files: `requirements.txt`, `.env.example`, `README.md`.

## Deliverables
- Working `run.py` orchestrating both servers (threads/processes + graceful shutdown).
- Backend FastAPI with `GET /api/health -> {"status":"ok"}`.
- Frontend: `index.html`, `assets/app.css`, `app.js`.
- Logging baseline.

## APIs & DTOs
- `GET /api/health`:
```json
{"status": "ok"}
```

## Acceptance Tests
- `curl http://localhost:5581/api/health` returns 200.
- Navigate to `http://localhost:5580/` shows index page without console errors.
- Ctrl‑C stops both servers cleanly.

## Success Criteria
- One command brings up both servers on the specified ports with no CORS issues.

## Single‑Shot Codex Prompt
Create the following working project scaffold **with code (no placeholders)**:

- Python 3.12+ only; **no Node, no npm, no CDNs**.
- Backend: FastAPI app on **port 5581** with `GET /api/health`.
- Frontend: Python static server on **port 5580** serving `/app/frontend`.
- Orchestrator `run.py`: starts both servers, handles Ctrl‑C, reads `.env` (`BACKEND_PORT`, `FRONTEND_PORT`).
- CORS: allow `http://localhost:5580` and `http://127.0.0.1:5580`.
- Files to create:
```
/app/backend/main.py
/app/backend/core/{config.py,db.py}
/app/frontend/{index.html, assets/app.css, app.js, views/, vm/, lib/}
/run.py
/requirements.txt
/.env.example
/README.md
```
- Minimal README with run instructions.
- `requirements.txt` minimal: fastapi, uvicorn, sqlalchemy, python-dotenv, python-multipart, starlette.

Ensure `python run.py` works end‑to‑end with no TODOs.
