# Gates — Phase 2
- De-duplication must prevent reparsing identical files.
- Lines retain order and blank lines; bbox present.
- `toc_spans_v1` artifact includes early-page ranges only; reduce false positives.
- Stream parse large PDFs; avoid loading entire file in memory.