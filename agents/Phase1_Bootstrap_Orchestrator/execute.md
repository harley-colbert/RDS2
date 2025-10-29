# Phase1_Bootstrap_Orchestrator — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your Codex prompt.

## Context (from plan.md)
### Goal
`python run.py` launches **backend (FastAPI) on :5581** and **frontend (static) on :5580** with CORS configured and a minimal skeleton.

### Scope
- Backend app factory with health check.
- Static frontend server (Python) serving `/app/frontend`.
- CORS allowlist for `http://localhost:5580` (and localhost variants).
- Repo files: `requirements.txt`, `.env.example`, `README.md`.


## Single‑Shot Codex Prompt


