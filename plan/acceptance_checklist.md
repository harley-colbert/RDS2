# Acceptance Checklist (Quick)

- [ ] `python run.py` launches frontend on :5580 and backend on :5581
- [ ] `GET /api/health` → 200 {"status":"ok"}
- [ ] Upload PDF → pages/lines persisted (blank lines & bbox retained)
- [ ] `toc_spans_v1` artifact present for TOC/Index
- [ ] LLM headers: `POST /api/documents/{id}/headers/llm` stores `llm_headers_v1` (raw fenced JSON)
- [ ] Headers mapped to **last** occurrence outside TOC/Index
- [ ] `POST /api/documents/{id}/chunk` builds contiguous chunks
- [ ] Frontend: Docs → Headers → Chunk Viewer works; Search returns hits
- [ ] Spec extraction returns normalized JSON; cached by sha256+version
- [ ] Re-open document hydrates from cache (no LLM call)
- [ ] Basic pytest suite passes
