# Guardrails (Global) — 2025-10-29

**Hard Constraints**
- Python 3.12+, FastAPI + Uvicorn, SQLAlchemy + SQLite
- Frontend is pure HTML/CSS/ESM-JS — **no Node, no npm, no CDNs**
- Single runner: `python run.py` starts **frontend :5580** and **backend :5581**
- MVVM split: Frontend = Views + Thin VMs; Backend = Full VMs + Models
- Self-host all assets; no external fonts/CDNs
- LLM headers: one OpenRouter call (split ≤120k tokens), **strict fenced JSON**, TOC/Index hard-exclusion, **last occurrence** mapping
- Persistence & caching: artifacts/extractions keyed by `sha256` + version
- CORS: allow `http://localhost:5580` and `http://127.0.0.1:5580`
- Logs: structured with `trace_id` on every API response

**Quality Gates (every phase)**
- Runs clean with `python run.py` (no placeholders/TODOs)
- Health `/api/health` returns 200 and JSON
- JSON error envelopes with `trace_id`
- Deterministic results for unchanged inputs
