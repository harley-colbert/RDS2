# Phase 03 — Frontend Thin‑VM UI — EXECUTE

Include `_shared/guardrails.md` verbatim at the top of your reasoning.

## Objective
Pure ESM UI: document list/upload, headers tree, chunk viewer, and search; no frameworks/build steps.

## Deliver
1. **Views**: DocumentsView, HeadersView (left rail), ChunkView (right panel)
2. **Thin VMs (ES modules)**:
   - vm/documents.js (list, upload, select)
   - vm/headers.js (load, select)
   - vm/chunks.js (load)
   - vm/search.js (q → backend /search)
3. **Routing**: simple hash-based router in `app.js`
4. **Styling**: `/assets/app.css` local
5. **Backend Search** endpoint if not present: `GET /api/documents/{id}/search?q=`

## Output Rules
- No external libraries; DOM updates minimal and explicit; no CDNs.
