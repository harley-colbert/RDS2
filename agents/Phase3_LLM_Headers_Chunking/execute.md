# Phase3_LLM_Headers_Chunking — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your Codex prompt.

## Context (from plan.md)
### Goal
Use **one OpenRouter call** (split if needed) to get **fenced JSON** headers; map to **last occurrence** outside TOC/Index; build **chunks** per header.

### Scope
- Add `headers` and `chunks` tables.
- LLM service with `.env` keys (`OPENROUTER_API_KEY`, `MAX_TOKENS_PER_PART`, `HEADERS_LLM_STRICT`).
- Chunking across header boundaries (header line to line before next header).


## Single‑Shot Codex Prompt


