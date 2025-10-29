# Gates — Phase 3
- LLM response must be strict fenced JSON; add retry guard if malformed.
- Map to **last** occurrence and exclude any `toc_spans_v1` ranges.
- Chunks must be contiguous, non-overlapping; stable IDs across re-runs.
- Hide secrets; wrap errors with JSON envelopes and `trace_id`.