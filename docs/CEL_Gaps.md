# Costing Emulation Layer Gaps

The original `Costing.xlsb` workbook is unavailable. The current Costing Emulation Layer (CEL) reproduces the interfaces that Workbook A expected, but several costing formulas remain placeholders.

## Known Placeholders

* `Summary!J4` – `Summary!J47`: Each entry is created as a placeholder costing item with a default quantity of `1` and unit cost `0`. Populate these rows via the admin UI or database seed scripts with the correct costing data once available.
* Base rollup (`SUM(J4:J10,J14,J17,J24,J31)`) reflects the VBA read-back behaviour. Additional dependencies (e.g., overhead, freight) should be added when recovered from the legacy workbook.
* Toggle meanings are inferred from VBA comments. If future analysis reveals additional dependency logic (e.g., toggles gating formulas), encode the rules in `CostingEmulationLayer.recompute`.

## TODO Interface

Extend `CostingItem.metadata_json` to capture the following optional keys when the true formulas are known:

```json
{
  "summary_cell": "J4",
  "formula": "material_cost + labor_cost",
  "inputs": ["material_cost", "labor_cost"],
  "units": "USD",
  "notes": "Placeholder until Costing.xlsb recovered"
}
```

Then update `CostingEmulationLayer._build_context()` to evaluate the stored formula via the `FormulaEngine`.

## Next Steps

1. Extract legacy costing logic from any archived builds of `Costing.xlsb`.
2. Replace placeholder quantities/unit costs with real values.
3. Expand unit tests to cover the recovered formulas and toggle interactions.
4. Wire the generation button to a backend endpoint that calls `CostingWorkbookWriter` and `ProposalWriter`.
