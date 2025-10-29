# Phase 01 — Acceptance

- [ ] Upload returns {"status":"parsed"} with id & sha256.
- [ ] Re‑upload same file reuses existing id (no reparse).
- [ ] `GET /api/documents/{id}/lines` returns ordered lines with bbox and blanks.
- [ ] `artifacts` contains `toc_spans_v1` entry.
