# Phase 2 — Persistence & PDF Parsing (pages/lines + TOC spans)

## Goal
Upload PDFs, persist **documents/pages/lines** with **blank line fidelity** and **bbox**, and detect TOC/Index spans.

## Scope
- SQLite models and session.
- File storage with SHA‑256 de‑dupe.
- PDF parsing via pdfplumber or PyMuPDF.
- TOC/Index heuristics → store spans in `artifacts(kind="toc_spans_v1")`.

## DB Models
- `documents(id, filename, size, sha256, created_at, status)`
- `pages(id, document_id, index, text, meta_json)`
- `lines(id, page_id, line_no, text, bbox_json, features_json)`
- `artifacts(id, document_id, kind, key, json_blob, created_at)`

## APIs & DTOs
- `POST /api/documents/upload` (multipart form `file`):
```json
{"id":1,"filename":"spec.pdf","sha256":"...","status":"parsed"}
```
- `GET /api/documents`:
```json
[{"id":1,"filename":"spec.pdf","size":123456,"status":"parsed","created_at":"2025-10-28T20:00:00"}]
```
- `GET /api/documents/{id}` → metadata
- `GET /api/documents/{id}/lines?limit=100&offset=0`:
```json
{"total": 1200, "items":[{"line_id":10,"page_index":0,"line_no":1,"text":"...","bbox":[x,y,w,h],"features":{}}]}
```

## Acceptance Tests
- Upload a small PDF twice → second call reuses existing `documents` row (same `sha256`).
- Lines preserve order and blank lines; bbox present.
- `artifacts` contains `toc_spans_v1` for TOC/Index pages.

## Success Criteria
- Deterministic ingestion, robust for multiple documents.

## Single‑Shot Codex Prompt
Extend the project to implement persistence and parsing:

- Add SQLAlchemy models for `documents`, `pages`, `lines`, `artifacts`. Auto‑create tables at startup.
- Implement `POST /api/documents/upload` (multipart) that:
  - Stores file under `/data/docs/{sha256}/{filename}`
  - Computes `sha256`, de‑dupes documents
  - Parses PDF to pages and lines (with bbox, blank lines preserved, page index)
  - Detects TOC/Index spans (heuristics) and writes `artifacts(kind="toc_spans_v1")`
- Implement read endpoints listed above.
- Log with request IDs.
- Keep all code complete; **no placeholders**.
