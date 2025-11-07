# REPORT — Behavioral Equivalence & Discrepancies

**This file is generated now as a starting point.** After you run the test harness on Windows, append results below (pass/fail per scenario and the cell-level diffs it produces).

## Summary (Initial)
- Ground truth source: VBA you provided + canonical cell mappings
- App under test: `rdsgen2.0` (repo/zip supplied by you)
- Harness: `tests/` (uses Excel & Word via COM when available)

## What Must Match (Hard Requirements)
1) **UI parity**  
   - RDS inputs & pricing (Sheet1) mirrored in the app (same validation choices, number formats, conditional formatting logic).  
   - Costing/Sell Price List readouts displayed as in Excel.

2) **Computation parity**  
   - For each scenario, the app’s base cost and option costs must match Excel (≤ $0.01 currency delta).  
   - `MarginChange` and `ResetMargin` must force `Summary!H18,H19,H20,H32,H33,H38,H39,H40,H45,H46,H47 = 1` then set `M4` before recompute.

3) **File outputs parity**  
   - Excel saved as `01 - Q#<Quote> - Costing.xlsb`.  
   - Word bookmarks replaced exactly.  
   - PDF filename identical to docx but `.pdf`.  
   - Any missing bookmark or filename mismatch = **hard fail**.

## How to Run
```bash
# Windows (with Excel/Word installed; Python 3.11+ recommended)
pip install pywin32 requests python-docx docx2pdf
cd tests
copy config.example.json config.json
# Edit config.json paths for your local files and app base_url
python -m tests.run_matrix
```

Artifacts will appear under `./.artifacts/diffs/` as per-scenario CSVs plus a summary.

## Initial Discrepancy Checklist (fill after first run)

* [ ] Endpoint `/api/quote/compute` exists and returns required fields.
* [ ] Margin-change path forces H-cells to `1` prior to recomputation.
* [ ] Filenames match exactly (see Ground Truth).
* [ ] All required Word bookmarks present and filled with correct sources.
* [ ] UI validations in app match Excel lists and constraints.

## Final Status (append after rerun)

* Pass rate summary per scenario
* Any remaining gap with owner + fix ETA

