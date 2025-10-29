# Phase 00 — Bootstrap & Orchestrator — EXECUTE

Include the contents of `_shared/guardrails.md` verbatim at the top of your reasoning.

## Objective
Create a working scaffold where `python run.py` launches **frontend on :5580** and **backend on :5581** with CORS for :5580, and a minimal UI + health endpoint.

## Deliver
1. **Files & Layout**
```
/app/backend/main.py
/app/backend/core/{
  config.py, db.py, logging.py
}
/app/frontend/{
  index.html, assets/app.css, app.js, views/, vm/, lib/
}
/run.py
/requirements.txt
/.env.example
/README.md
/data/.gitkeep
```
2. `run.py` starts Uvicorn (FastAPI 5581) + static server (5580) with graceful shutdown.
3. Backend `GET /api/health -> {"status":"ok"}` and structured logs (with `trace_id`).  
4. CORS allows `http://localhost:5580` and `http://127.0.0.1:5580`.
5. README documents run steps and ports.

## Implementation Notes
- Static server can be `http.server` or a tiny Starlette app; must serve `/app/frontend` root.
- `.env.example` keys: BACKEND_PORT, FRONTEND_PORT, DATABASE_URL (sqlite:///./app.db).
- `requirements.txt` minimal but complete: fastapi, uvicorn, sqlalchemy, python-dotenv, python-multipart, starlette.

## Output Rules
- **No placeholders or TODOs.** Provide full, runnable code.
- Ensure `python run.py` works immediately.
