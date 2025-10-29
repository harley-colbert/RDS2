# Phase 3 — LLM Headers (strict fencing) → Mapping (TOC‑safe) → Chunking

## Goal
Use **one OpenRouter call** (split if needed) to get **fenced JSON** headers; map to **last occurrence** outside TOC/Index; build **chunks** per header.

## Scope
- Add `headers` and `chunks` tables.
- LLM service with `.env` keys (`OPENROUTER_API_KEY`, `MAX_TOKENS_PER_PART`, `HEADERS_LLM_STRICT`).
- Chunking across header boundaries (header line to line before next header).

## DB Models
- `headers(id, document_id, level, title, line_id, path)`
- `chunks(id, document_id, header_id, start_line_id, end_line_id, token_count, text_hash)`

## APIs & DTOs
- `POST /api/documents/{id}/headers/llm`:
```json
{"status":"ok","artifact":"llm_headers_v1"}
```
- `GET /api/documents/{id}/headers`:
```json
[{"id":10,"level":1,"title":"1 Scope","line_id":203,"path":"1"},
 {"id":11,"level":2,"title":"1.1 Purpose","line_id":214,"path":"1/1.1"}]
```
- `POST /api/documents/{id}/chunk`:
```json
{"status":"ok","chunks_created": 24}
```
- `GET /api/documents/{id}/chunks`:
```json
[{"id":301,"header_id":10,"start_line_id":203,"end_line_id":213,"token_count":742}]
```
- `GET /api/documents/{id}/chunks/{chunk_id}`:
```json
{"id":301,"header":{"title":"1 Scope","path":"1"},"text":"...","features":{}}
```

## Acceptance Tests
- LLM artifact `llm_headers_v1` stored with raw fenced JSON.
- Header mapping selects **last** body occurrence; nothing from TOC/Index.
- Chunks cover the whole doc (no overlaps, no gaps).

## Success Criteria
- Reproducible header mapping + stable chunks across re‑runs.

## Single‑Shot Codex Prompt
Add LLM header detection and chunking:

- Implement an LLM service that:
  - Concats document text; if needed, splits at `MAX_TOKENS_PER_PART` (default **120000**)
  - Calls OpenRouter (API key from `.env`) asking for **ONLY fenced JSON** with headers: `[{{"level":1,"title":"..."}}]`
  - Stores raw response in `artifacts(kind="llm_headers_v1")`
- Resolve headers to lines by matching **exact title** to the **last occurrence** among `lines`, excluding any range marked by `toc_spans_v1`.
- Persist resolved `headers` with `path` like `1/1.2/1.2.3`.
- Build `chunks` spanning from header line to line before the next header (respect sublevels). Store token counts and text hash.
- Provide the listed endpoints; return DTOs as shown.
- **No placeholders.**
