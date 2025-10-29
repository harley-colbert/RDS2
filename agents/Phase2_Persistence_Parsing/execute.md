# Phase2_Persistence_Parsing — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your Codex prompt.

## Context (from plan.md)
### Goal
Upload PDFs, persist **documents/pages/lines** with **blank line fidelity** and **bbox**, and detect TOC/Index spans.

### Scope
- SQLite models and session.
- File storage with SHA‑256 de‑dupe.
- PDF parsing via pdfplumber or PyMuPDF.
- TOC/Index heuristics → store spans in `artifacts(kind="toc_spans_v1")`.


## Single‑Shot Codex Prompt


