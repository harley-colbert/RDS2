# Phase 00 — BOOTSTRAP — GATES (Fix/Polish)

If any acceptance fails, apply these gates:

1. **Run orchestration**: `python run.py` must bind :5580 and :5581; add logging on bind; handle Ctrl‑C.
2. **CORS**: 200 preflight for Origin http://localhost:5580; add allowed methods/headers.
3. **Health**: Ensure /api/health returns 200 JSON and logs trace_id.
4. **Frontend**: index.html loads /assets/app.css and /app.js without 404s; avoid relative path bugs.
5. **README**: Include exact run steps and ports; reference `.env` copy step.
