# Phase3_LLM_Headers_Chunking — Acceptance

- LLM artifact `llm_headers_v1` stored with raw fenced JSON.
- Header mapping selects **last** body occurrence; nothing from TOC/Index.
- Chunks cover the whole doc (no overlaps, no gaps).

## Success Criteria
- Reproducible header mapping + stable chunks across re‑runs.
