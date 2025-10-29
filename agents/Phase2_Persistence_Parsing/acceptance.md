# Phase2_Persistence_Parsing — Acceptance

- Upload a small PDF twice → second call reuses existing `documents` row (same `sha256`).
- Lines preserve order and blank lines; bbox present.
- `artifacts` contains `toc_spans_v1` for TOC/Index pages.

## Success Criteria
- Deterministic ingestion, robust for multiple documents.
