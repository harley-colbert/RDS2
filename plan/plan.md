# Project Plan — MVVM (Thin Frontend VM / Full Backend VM) — Python FastAPI + HTML/CSS/ESM-JS
**Date:** 2025-10-29

## Non‑Negotiables
- **Backend:** Python 3.12+, FastAPI, Uvicorn, SQLAlchemy, SQLite (no external DB)
- **Frontend:** Pure HTML/CSS/ESM‑JS (no Node, no npm, no bundlers, no CDNs)
- **Run command:** `python run.py` (starts **frontend on :5580** and **backend on :5581**)
- **Architecture:** Frontend = **Views + Thin ViewModels**; Backend = **Full ViewModels + Models**
- **Persistence:** Cache all artifacts (headers, chunks, TOC spans, extractions) to avoid re‑calling LLM if unchanged
- **LLM headers:** Single OpenRouter call returning **only fenced JSON**; split inputs at ≤120k tokens; **TOC/index excluded**; **last occurrence** mapping
- **CORS:** Explicitly allow `http://localhost:5580` (and same‑LAN origin if applicable)
- **Self‑host everything** (fonts/icons/CSS—no CDNs)

## Ports & Environment
- Backend: **5581**; Frontend: **5580**
- `.env.example`:
```
BACKEND_PORT=5581
FRONTEND_PORT=5580
DATABASE_URL=sqlite:///./app.db
OPENROUTER_API_KEY=changeme
HEADERS_LLM_STRICT=true
MAX_TOKENS_PER_PART=120000
```
Copy to `.env` and populate `OPENROUTER_API_KEY` as needed.

## Directory Layout (Target)
```
/app
  /backend
    /api            # FastAPI routers
    /core           # settings, db session, logging
    /models         # SQLAlchemy models
    /vm             # Full ViewModels (service/domain layer)
    /services       # parsing, LLM, chunking, search, spec_rules
    /schemas        # Pydantic DTOs
    /storage        # file I/O, artifact cache
    main.py         # app factory
  /frontend
    /assets         # css, icons, fonts (local)
    /views          # HTML partials/templates
    /vm             # thin VMs (ES modules)
    /lib            # tiny utilities (ES modules)
    index.html
    app.js          # bootstraps thin VMs + router
/run.py
/requirements.txt
/.env.example
/README.md
/tests
```

## Phases (Codex‑Optimized)
- **Phase 1:** Bootstrap & Orchestrator
- **Phase 2:** Persistence & PDF Parsing (pages/lines + TOC spans)
- **Phase 3:** LLM Headers (strict fencing) → Mapping (TOC‑safe) → Chunking
- **Phase 4:** Frontend UI (Docs → Headers → Chunk Viewer + Search) — thin VM
- **Phase 5:** Spec Rules + Caching/Rehydration + Tests & DX polish

Each phase includes:
- **Goal, Scope, Deliverables**
- **APIs & DTOs** (with examples)
- **Acceptance Tests** (curl) & **Success Criteria**
- **Single‑Shot Codex Prompt** (Paste to ChatGPT Codex; no placeholders/todos)
