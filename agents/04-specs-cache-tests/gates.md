# Phase 04 — SPECS/CACHE/TESTS — GATES

- **Determinism**: identical inputs produce identical extraction JSON.
- **Cache hits**: re-open doc uses existing artifacts; assert no LLM call unless forced.
- **Coverage**: tests cover unhappy paths (malformed PDFs, missing headers, empty chunks).
- **Docs**: README contains troubleshooting and curl cheatsheet.
