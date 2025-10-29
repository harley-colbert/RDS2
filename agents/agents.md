# Agents Orchestrator (Aligned to plan.zip) — 2025-10-29

This pack mirrors the **plan.zip** phases exactly. For each phase:
1) Open the `execute.md` in the matching `PhaseX_*` folder and paste it into ChatGPT Codex.
2) Apply `_shared/guardrails.md` at the top of your prompt.
3) After code is produced, run the `acceptance.md` checks.
4) If something fails, paste `gates.md` to request a targeted fix.

**Execution Order**
- Phase1_Bootstrap_Orchestrator
- Phase2_Persistence_Parsing
- Phase3_LLM_Headers_Chunking
- Phase4_Frontend_ThinVM_UI
- Phase5_Specs_Cache_Tests

See `_shared/curl_smoke.md` for quick smoke tests.
