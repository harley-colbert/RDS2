# Phase 02 — LLM Headers & Chunking — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your reasoning.

## Objective
LLM-first header list (strict fenced JSON), TOC-safe mapping to **last occurrence** in body lines, then chunking (header → line before next header).

## Deliver
1. **Models**: headers, chunks
2. **LLM Service**:
   - Read `.env`: OPENROUTER_API_KEY, HEADERS_LLM_STRICT=true, MAX_TOKENS_PER_PART=120000
   - Concatenate doc text; split at token limit
   - Prompt for ONLY fenced JSON: `[{"level":1,"title":"..."}]`
   - Store raw in `artifacts(kind="llm_headers_v1")`
3. **Mapping**:
   - Resolve each title to the **last** matching line outside `toc_spans_v1`
   - Build hierarchical `path` like `1/1.2/1.2.1`
4. **Chunking**:
   - Build contiguous chunks; store token_count & text_hash
5. **API**:
   - `POST /api/documents/{id}/headers/llm`, `GET /api/documents/{id}/headers`
   - `POST /api/documents/{id}/chunk`, `GET /api/documents/{id}/chunks`, `GET /api/documents/{id}/chunks/{chunk_id}`

## Output Rules
- Full code, no placeholders; determinism across re-runs.
