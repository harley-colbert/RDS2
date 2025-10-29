# Guardrails (Global)

**Date:** 2025-10-29

## Hard Constraints (non‑negotiable)
- **Stack:** Python 3.12+, FastAPI, Uvicorn, SQLAlchemy, SQLite; Frontend is pure HTML/CSS/ESM‑JS.
- **No Node/npm/CDNs.** Do not add bundlers, React/Vue, Tailwind, Bootstrap CDN, etc.
- **Single runner:** `python run.py` must start *both* servers.
- **Ports:** Backend **5581**, Frontend **5580** (read from `.env`).
- **Architecture:** Frontend = **Views + Thin ViewModels**; Backend = **Full ViewModels + Models**.
- **Assets:** All local; fonts, icons, CSS self-hosted.
- **LLM Headers:** one OpenRouter call (split ≤120k tokens), **strict fenced JSON** only, TOC/Index hard‑exclusion, **last occurrence** mapping.
- **Persistence:** Cache all artifacts/extractions keyed by `sha256` + version; never re-send to LLM if unchanged.
- **CORS:** Allow `http://localhost:5580` and `http://127.0.0.1:5580`.
- **Logging:** Structured logs with `trace_id` on each API response.

## Quality Gates (apply every phase)
1. **Runs clean** with `python run.py` (no TODOs/placeholders).
2. **Static analysis**: no unused imports, no syntax warnings.
3. **APIs respond** with {"status":"ok"} health and JSON error envelopes with `trace_id`.
4. **Docs** updated: README phase notes + run steps.
5. **Determinism:** idempotent re-runs; stable IDs/paths for headers & chunks.
