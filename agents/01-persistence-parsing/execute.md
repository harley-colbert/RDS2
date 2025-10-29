# Phase 01 — Persistence & PDF Parsing — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your reasoning.

## Objective
Add SQLite persistence for documents/pages/lines/artifacts, and implement PDF upload + parsing to line granularity with bbox and blank‑line fidelity. Detect TOC/Index spans (artifact `toc_spans_v1`).

## Deliver
1. **Models** (SQLAlchemy, auto‑create):
   - documents, pages, lines, artifacts
2. **Storage**
   - Save uploads under `/data/docs/{sha256}/{filename}`
   - Compute SHA‑256; de‑dupe by content
3. **Parsing**
   - Use pdfplumber or PyMuPDF to produce ordered lines with bbox + page index
   - Preserve blank lines; set features flags as needed
   - Heuristics to detect TOC/Index; store ranges in `artifacts(kind="toc_spans_v1")`
4. **API**
   - `POST /api/documents/upload` (multipart)
   - `GET /api/documents`, `GET /api/documents/<built-in function id>`
   - `GET /api/documents/<built-in function id>/lines?limit=&offset=`
5. Logs with `trace_id`; JSON error envelopes.

## Output Rules
- **No placeholders.** Provide full code; update README usage.
