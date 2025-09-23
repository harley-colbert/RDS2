import sys

def _win32_available():
    return sys.platform.startswith("win")

def _com_open_excel():
    import win32com.client as win32
    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    return excel

def compute_truth_with_com(rds_path, costing_path, scenario):
    """
    Replays the canonical VBA behavior:
      - Open Costing.xlsb
      - Set Summary!M4 (margin) and force H18,H19,H20,H32,H33,H38,H39,H40,H45,H46,H47 = 1
      - Read Summary!Jxx values, compute base cost, return dict
    """
    import win32com.client as win32
    excel = _com_open_excel()
    try:
        wb_rds = excel.Workbooks.Open(rds_path)
        wb_cost = excel.Workbooks.Open(costing_path)
        ws_sum = wb_cost.Worksheets("Summary")

        # Margin
        margin = scenario.get("margin")
        if margin == "RESET":
            # Echo baseline margin from RDS Sheet1!B17 to Summary!M4
            ws_rds1 = wb_rds.Worksheets("Sheet1")
            baseline = ws_rds1.Range("B17").Value
            ws_sum.Range("M4").Value = baseline
        elif margin is not None:
            ws_sum.Range("M4").Value = float(margin)

        # Force toggles to 1
        for addr in ["H18","H19","H20","H32","H33","H38","H39","H40","H45","H46","H47"]:
            ws_sum.Range(addr).Value = 1

        # Full recalculation
        excel.CalculateFullRebuild()

        def v(addr):
            return ws_sum.Range(addr).Value or 0

        base_cost = sum(v(f"J{i}") for i in range(4, 11)) + v("J14") + v("J17") + v("J24") + v("J31")
        truth = {
            "base_cost": base_cost,
            "spares": {"J38": v("J38"), "J39": v("J39"), "J40": v("J40")},
            "guard":  {"J32": v("J32"), "J33": v("J33")},
            "infeed": {"J18": v("J18"), "J19": v("J19"), "J20": v("J20")},
            "misc":   {"J45": v("J45"), "J46": v("J46"), "J47": v("J47")},
            "margin": v("M4")
        }
        return truth
    finally:
        try:
            wb_cost.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            wb_rds.Close(SaveChanges=False)
        except Exception:
            pass
        excel.Quit()

def compute_truth_fallback(rds_path, costing_path, scenario):
    # Runs when Excel/COM is not available (CI environments).
    return {
        "base_cost": None,
        "spares": {},
        "guard": {},
        "infeed": {},
        "misc": {},
        "margin": scenario.get("margin")
    }
