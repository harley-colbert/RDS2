# Phase 4 — Frontend UI (Docs → Headers → Chunk Viewer + Search) — thin VM

## Goal
Pure ESM UI that proves MVVM split: **documents list & upload**, **headers tree**, **chunk viewer**, and **search**.

## Scope
- Views: Documents, Headers (left rail), Chunk (right panel), Search.
- Thin VMs: `documents.js`, `headers.js`, `chunks.js`, `search.js`.
- Minimal router (hash or History API). All assets local.

## Backend Search
- `GET /api/documents/{id}/search?q=` → return top chunk hits with header path + snippet (BM25/TF‑IDF).

## Acceptance Tests
- Upload → parse → click **Generate Headers** → headers appear.
- Clicking a header shows the chunk text; breadcrumb shows header `path`.
- Search jumps to a matching chunk.
- No CORS errors, no external libs.

## Single‑Shot Codex Prompt
Implement the thin‑VM frontend and wire it to existing APIs:

- `/app/frontend/index.html` loads `/assets/app.css` and `/app.js`.
- `app.js` initializes router and mounts views.
- Create views and thin VMs:
  - `views/DocumentsView.html` + `vm/documents.js`: list & upload, select document
  - `views/HeadersView.html` + `vm/headers.js`: load tree by levels, select header
  - `views/ChunkView.html` + `vm/chunks.js`: load and render chunk text/meta
  - Search input bound to `vm/search.js` → backend `/search` endpoint
- Keep DOM updates simple; no frameworks, no CDNs, no build.
- Add basic styling in `/assets/app.css` (local file).
- Ensure flows work end‑to‑end with current backend.
