# Agents Orchestrator

**Date:** 2025-10-29

This pack drives ChatGPT Codex through 5 **single‑shot** phases. For each phase:

1) Open the `execute.md` under that phase and paste it into Codex.  
2) Let Codex output **complete code** (no placeholders).  
3) Run the **acceptance** smoke tests.  
4) If any check fails, open `gates.md` in the same phase and paste into Codex to request a targeted fix.

**Order:** 00 → 01 → 02 → 03 → 04

## Global Files
- `_shared/guardrails.md` — hard constraints to include in *every* Codex prompt.
- `_shared/curl_smoke.md` — copy/paste smoke tests.

## Phases
- `00-bootstrap/` — `run.py`, backend/ frontend skeletons, CORS, health.
- `01-persistence-parsing/` — SQLite models, upload, PDF parsing, TOC spans.
- `02-llm-headers-chunking/` — LLM strict‑JSON headers, TOC‑safe mapping, chunking.
- `03-frontend-thinvm/` — pure ESM UI: docs, headers, chunk viewer, search.
- `04-specs-cache-tests/` — spec rules, caching/rehydration, tests, DX polish.
