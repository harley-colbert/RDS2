# ARCHITECTURE — App vs Excel Behavior Mapping (Ground Truth First)

**Scope:** Replace the two-workbook system (RDS Sales Tool `.xlsm` + Costing `.xlsb`) with an app+DB while **exactly** replicating Excel UI, formulas, macros, outputs, and filenames.

**Ground Truth Inputs**
- **Workbook A (primary):** `RDS Sales Tool -hrc.xlsm`  
- **Workbook B (linked):** `Costing - hrc.xlsb` (binary; treat as canonical addresses from VBA)  
- **VBA/Macros:** Provided (Generate, SaveCosting, SaveWord, Log, MarginChange, ResetMargin, Test utilities)  
- **Word Template (optional):** `Quote.docx` with bookmarks (listed below)

---

## 1) Excel Ground Truth (from your VBA)

### 1.1 Canonical Write → Costing.Summary (from RDS Sales Tool)
- **Spare Parts:**  
  - `Summary!H38 ← RDS Sheet1!B4`  
  - `Summary!H39 ← RDS Sheet1!B5`  
  - `Summary!H40 ← RDS Sheet1!B6`
- **Guarding:**  
  - `Summary!H32 ← RDS Sheet3!C6`  
  - `Summary!H33 ← RDS Sheet3!C7`
- **Infeed Conveyor:**  
  - `Summary!H18 ← RDS Sheet3!C8`  
  - `Summary!H19 ← RDS Sheet3!C9`  
  - `Summary!H20 ← RDS Sheet3!C10`
- **Misc:**  
  - `Summary!H45 ← RDS Sheet3!C11`  
  - `Summary!H46 ← RDS Sheet3!C12`  
  - `Summary!H47 ← RDS Sheet3!C13`
- **Margin:**  
  - `Summary!M4 ← RDS Sheet1!B12`

### 1.2 Read Back ← Costing.Summary → RDS Sales Tool
- **Base costing:**  
  - `RDS Sheet3!B2 ← SUM(Summary!J4:J10) + Summary!J14 + J17 + J24 + J31`
- **Spare parts costing:**  
  - `RDS Sheet3!B3 ← Summary!J38`  
  - `RDS Sheet3!B4 ← Summary!J39`  
  - `RDS Sheet3!B5 ← Summary!J40`
- **Guarding costing:**  
  - `RDS Sheet3!B6 ← Summary!J32`  
  - `RDS Sheet3!B7 ← Summary!J33`
- **Infeed conveyor costing:**  
  - `RDS Sheet3!B8 ← Summary!J18`  
  - `RDS Sheet3!B9 ← Summary!J19`  
  - `RDS Sheet3!B10 ← Summary!J20`
- **Misc costing:**  
  - `RDS Sheet3!B11 ← Summary!J45`  
  - `RDS Sheet3!B12 ← Summary!J46`  
  - `RDS Sheet3!B13 ← Summary!J47`
- **Margin echo:**  
  - `RDS Sheet1!B12 ← Summary!M4`

### 1.3 Macro Toggles
When `MarginChange` or `ResetMargin` runs:
- Force **`Summary!H18,H19,H20,H32,H33,H38,H39,H40,H45,H46,H47 = 1`**, then set `Summary!M4` to the margin.

### 1.4 Word Bookmarks (and sources)
- **Qty:** `RDS Sheet3!C3:C13`
- **Price text:** `RDS Sheet3!B2:B13` (B2 = BasePrice; B3…B13 option prices)
- **Bookmarks:**  
  `QuoteNum, Customer, Layout, BasePrice, SpareQty, SparePrice, BladeQty, BladePrice, FoamQty, FoamPrice, TallQty, TallPrice, NetQty, NetPrice, FrontUSLQty, FrontUSLPrice, SideUSLQty, SideUSLPrice, SideBadgerQty, SideBadgerPrice, CanadaQty, CanadaPrice, StepQty, StepPrice, TrainQty, TrainPrice, Date, User`

### 1.5 Output Filenames (must match exactly)
- **Costing Excel:** `01 - Q#<Quote> - Costing.xlsb`
- **Word Doc:** `Alliance Automation Proposal #<Quote> - Dismantling System.docx`
- **PDF:** `Alliance Automation Proposal #<Quote> - Dismantling System.pdf`

---

## 2) App Architecture Expectations

### 2.1 Backend
- Expose endpoints:
  - `POST /api/quote/compute` → computes rollups identical to Excel macro flows (respect toggles and margin) and returns JSON with base cost, option costs, margin, and all visible numbers that appear in the RDS UI and Sell Price List/Summary.
  - `POST /api/quote/generate` → performs **SaveCosting** and **SaveWord** equivalents:
    - Writes the H/M mappings into an **on-disk** `Costing.xlsb` clone (using COM recommended).
    - Saves as `01 - Q#<Quote> - Costing.xlsb`.
    - Opens the Word template, fills bookmarks, saves `.docx`, then exports `.pdf`.
- Provide a config to replace SharePoint URLs with **local paths** (templates dir, output dir).

### 2.2 Database
- Persist a *Quote* record with:
  - `quote_number`, `customer`, *all RDS inputs* (mirror Sheet1 and Sheet3), computed pricing slices (base, spares, guarding, infeed, misc), `margin`, and *output file paths*.

### 2.3 Frontend (UI Parity)
- Recreate the **RDS inputs & pricing (Sheet1)**: identical inputs, data validation choices, and number formats.
- Provide a **Costing/Sell Price List** readout view matching Excel’s visible fields.

---

## 3) Test Harness (Windows-first; COM automation)
- Runs 8 scenarios (margin change/reset, spares, guarding variants, USL/Badger toggles, transformers, training languages).
- For each: computes Excel ground truth via COM; calls app endpoints; compares outputs with tolerances; produces CSV diffs and a Markdown REPORT.

See `tests/` and `REPORT.md` for details.
