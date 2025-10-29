# Phase 5 — Spec Rules + Caching/Rehydration + Tests & DX polish

## Goal
Deterministic spec extraction (ASME/ISO‑style rules), strong caching/rehydration, and essential tests.

## Scope
- `services/spec_rules.py` for units, tolerances, materials, finishes, voltage/phase, pneumatics (psi), safety (NFPA/OSHA), etc.
- `extractions` table with versioned results and token/cost counters.
- Status/version endpoints for UI hydration & cache busting.
- Pytest for core flows.

## DB Models
- `extractions(id, document_id, extractor, version, result_json, cost_tokens, created_at)`

## APIs & DTOs
- `POST /api/documents/{id}/extract/specs`:
```json
{"status":"ok","extraction_id":91,"summary":{"voltages":["480VAC"],"pressures":["80 psi"]}}
```
- `GET /api/documents/{id}/status`:
```json
{"artifacts":["llm_headers_v1","toc_spans_v1"],"extractions":["spec_rules_v1"]}
```
- `GET /api/version`:
```json
{"rules_version":"spec_rules_v1"}
```

## Caching/Rehydration
- Keys: `document.sha256` + `rules_version` or extractor version.
- Frontend should instantly hydrate from existing artifacts; “Reprocess” button to refresh.

## Acceptance Tests
- Known sample docs produce stable, repeatable extraction JSON.
- Re‑open document is instant; no LLM call unless “Reprocess”.

## Single‑Shot Codex Prompt
Add spec rules, caching, and tests:

- Implement `services/spec_rules.py` with deterministic regex/state logic; persist results in `extractions` with `version`.
- Implement `POST /api/documents/{id}/extract/specs`, `GET /api/documents/{id}/status`, and `GET /api/version`.
- Add pytest for: parsing, TOC exclusion, header mapping, chunking, spec rules.
- Structure error envelopes and logs with a `trace_id` on all API responses.
- Keep all code complete; **no placeholders**.
