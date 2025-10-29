# Phase 02 — Acceptance

- [ ] `POST /api/documents/{id}/headers/llm` stores `llm_headers_v1` artifact.
- [ ] `GET /api/documents/{id}/headers` returns levels, titles, line_ids, paths.
- [ ] `POST /api/documents/{id}/chunk` builds gap-free, non-overlapping chunks.
- [ ] `GET /api/documents/{id}/chunks/{chunk_id}` returns header breadcrumb + text.
