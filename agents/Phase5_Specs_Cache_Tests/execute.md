# Phase5_Specs_Cache_Tests — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your Codex prompt.

## Context (from plan.md)
### Goal
Deterministic spec extraction (ASME/ISO‑style rules), strong caching/rehydration, and essential tests.

### Scope
- `services/spec_rules.py` for units, tolerances, materials, finishes, voltage/phase, pneumatics (psi), safety (NFPA/OSHA), etc.
- `extractions` table with versioned results and token/cost counters.
- Status/version endpoints for UI hydration & cache busting.
- Pytest for core flows.


## Single‑Shot Codex Prompt


