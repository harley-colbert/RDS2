# Phase 01 — PERSISTENCE/PARSING — GATES

- **De‑dupe**: same file twice returns existing document; avoid duplicate parsing.
- **BBox & blanks**: verify a sample page shows both; add unit test if needed.
- **TOC spans**: artifact present with page ranges; exclude false positives by bounding to early pages and pattern filters.
- **Large PDFs**: stream parsing; do not load entire file into memory.
