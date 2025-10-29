# Phase 02 — LLM/CHUNKING — GATES

- **Strict JSON**: reject non-fenced or malformed responses; retry with stronger system prompt.
- **TOC exclusion**: ensure mapping ignores lines inside toc_spans_v1 ranges.
- **Stability**: same input → same header ids/paths/chunk ids (hash where appropriate).
- **Errors**: wrap with JSON error envelope, include `trace_id`, never expose API keys.
