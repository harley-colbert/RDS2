"""
Drop into your backend (e.g., backend/app/services/excel_word_service.py)

Provides:
- ExcelCostingService: open Costing.xlsb via COM, write Summary H/M cells, read J-cells, save as exact filename.
- WordProposalService: open template, fill bookmarks, paste image if needed (layout), save docx and export pdf.

Requires: pywin32, python-docx (for backup checks), docx2pdf
"""

import os
from datetime import datetime
from pathlib import Path

try:
    import win32com.client as win32
except Exception:
    win32 = None

from .mapping_constants import SUMMARY_FORCE_ONES, WRITE_TO_SUMMARY, READ_BACK_TO_RDS, BASE_SUMMARY_TERMS

class ExcelCostingService:
    def __init__(self, rds_path: str, costing_path: str):
        self.rds_path = rds_path
        self.costing_path = costing_path

    def _excel(self):
        if not win32:
            raise RuntimeError("pywin32 not available; Excel COM required for .xlsb")
        app = win32.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        return app

    def apply_write_and_read(self, quote_number: str, output_dir: str, margin_value: float|None=None):
        excel = self._excel()
        wb_rds = wb_cost = None
        try:
            wb_rds = excel.Workbooks.Open(self.rds_path)
            wb_cost = excel.Workbooks.Open(self.costing_path)

            ws_sum = wb_cost.Worksheets("Summary")
            ws_rds1 = wb_rds.Worksheets("Sheet1")
            ws_rds3 = wb_rds.Worksheets("Sheet3")

            # Force H-cells to 1
            for addr in SUMMARY_FORCE_ONES:
                ws_sum.Range(addr).Value = 1

            # Write M4 (margin) if provided
            if margin_value is not None:
                ws_sum.Range("M4").Value = float(margin_value)

            # Write other H cells from RDS sources
            for summary_cell, (src_sheet, src_cell) in WRITE_TO_SUMMARY.items():
                if summary_cell == "M4":
                    # already set above if margin_value provided, else M4 should mirror Sheet1!B12
                    ws_sum.Range("M4").Value = ws_rds1.Range("B12").Value if margin_value is None else ws_sum.Range("M4").Value
                else:
                    src_ws = ws_rds1 if src_sheet == "Sheet1" else ws_rds3
                    ws_sum.Range(summary_cell).Value = src_ws.Range(src_cell).Value

            excel.CalculateFullRebuild()

            # Read back summary J-cells and update RDS Sheet3 & Sheet1
            for (t_sheet, t_cell), j_addr in READ_BACK_TO_RDS.items():
                target_ws = wb_rds.Worksheets(t_sheet)
                target_ws.Range(t_cell).Value = ws_sum.Range(j_addr).Value

            # Compute base cost sum (for API JSON return)
            base_cost = 0
            for j in BASE_SUMMARY_TERMS:
                base_cost += ws_sum.Range(j).Value or 0

            # Save Costing clone with exact name
            expected_name = f"01 - Q#{quote_number} - Costing.xlsb"
            out_path = str(Path(output_dir) / expected_name)
            wb_cost.SaveAs(Filename=out_path)
            return {
                "base_cost": base_cost,
                "spares": {"J38": ws_sum.Range("J38").Value, "J39": ws_sum.Range("J39").Value, "J40": ws_sum.Range("J40").Value},
                "guard":  {"J32": ws_sum.Range("J32").Value, "J33": ws_sum.Range("J33").Value},
                "infeed": {"J18": ws_sum.Range("J18").Value, "J19": ws_sum.Range("J19").Value, "J20": ws_sum.Range("J20").Value},
                "misc":   {"J45": ws_sum.Range("J45").Value, "J46": ws_sum.Range("J46").Value, "J47": ws_sum.Range("J47").Value},
                "margin": ws_sum.Range("M4").Value,
                "costing_xlsb": out_path
            }
        finally:
            if wb_cost:
                wb_cost.Close(SaveChanges=False)
            if wb_rds:
                wb_rds.Close(SaveChanges=True)
            excel.Quit()

class WordProposalService:
    def __init__(self, template_path: str):
        self.template_path = template_path

    def _word(self):
        if not win32:
            raise RuntimeError("pywin32 not available; Word COM required for bookmark paste + PDF export")
        return win32.DispatchEx("Word.Application")

    def fill_and_export(self, quote_number: str, customer: str, quantities: list, prices_text: list, layout_image_shape=None, output_dir: str="."):
        word = self._word()
        try:
            doc = word.Documents.Open(self.template_path)
            word.Visible = False

            # Insert bookmarks
            def set_bookmark(name, value):
                doc.Bookmarks(name).Range.InsertBefore(str(value))

            from datetime import date
            import getpass
            today = date.today().strftime("%m/%d/%y")
            user = getpass.getuser()

            set_bookmark("QuoteNum", f"Proposal #{quote_number}")
            set_bookmark("Customer", f"Prepared For: {customer}")

            # Layout image paste is optional; if needed, select bookmark and paste from clipboard
            # (app can place an image in clipboard beforehand)
            # doc.Bookmarks("Layout").Select(); word.Selection.Paste()

            # Prices (B2..B13) and Quantities (C3..C13)
            # prices_text[0] = BasePrice (B2), then options B3..B13
            set_bookmark("BasePrice", prices_text[0])
            names = [
              ("SpareQty","SparePrice"), ("BladeQty","BladePrice"), ("FoamQty","FoamPrice"),
              ("TallQty","TallPrice"), ("NetQty","NetPrice"), ("FrontUSLQty","FrontUSLPrice"),
              ("SideUSLQty","SideUSLPrice"), ("SideBadgerQty","SideBadgerPrice"),
              ("CanadaQty","CanadaPrice"), ("StepQty","StepPrice"), ("TrainQty","TrainPrice")
            ]
            # quantities has 11 entries C3..C13 ; prices_text has 12 entries B2..B13
            for i,(q_tag,p_tag) in enumerate(names):
                set_bookmark(q_tag, quantities[i])
                set_bookmark(p_tag, prices_text[i+1])

            set_bookmark("Date", today)
            set_bookmark("User", user)

            doc.Fields.Update()

            docx_name = f"Alliance Automation Proposal #{quote_number} - Dismantling System.docx"
            pdf_name  = f"Alliance Automation Proposal #{quote_number} - Dismantling System.pdf"
            docx_path = str(Path(output_dir) / docx_name)
            pdf_path  = str(Path(output_dir) / pdf_name)

            doc.SaveAs2(docx_path)
            doc.ExportAsFixedFormat(OutputFileName=pdf_path, ExportFormat=17, OpenAfterExport=False,
                                    OptimizeFor=0, Range=0, Item=0, IncludeDocProps=False,
                                    CreateBookmarks=0, BitmapMissingFonts=True)
            return {"proposal_docx": docx_path, "proposal_pdf": pdf_path}
        finally:
            doc.Close(SaveChanges=0)
            word.Quit()
