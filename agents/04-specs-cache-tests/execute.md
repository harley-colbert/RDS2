# Phase 04 — Spec Rules, Caching, Tests & DX — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your reasoning.

## Objective
Deterministic spec extraction rules, strict caching/rehydration, essential tests, and DX polish.

## Deliver
1. **services/spec_rules.py**: regex/state logic to detect units, tolerances, materials, finishes, voltages, psi, safety refs, etc.
2. **Model**: extractions(version, result_json, cost_tokens)
3. **API**: POST /api/documents/{id}/extract/specs; GET /api/documents/{id}/status; GET /api/version
4. **Caching**: key by document.sha256 + rules_version; frontend hydrates instantly if artifacts exist; Reprocess button to refresh.
5. **Tests**: pytest for parsing, TOC exclusion, header mapping, chunking, spec extraction.
6. **DX**: structured errors with trace_id; README updates.

## Output Rules
- Provide complete code and tests; no placeholders.
