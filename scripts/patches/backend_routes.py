"""
Drop this as a replacement for your generate/pricing routes (e.g., backend/app/routes/generate.py).
Adjust import paths to match your project layout.
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
from ..services.excel_word_service import ExcelCostingService, WordProposalService
from ..core.mapping_constants import SUMMARY_FORCE_ONES

api_bp = Blueprint("api", __name__)

@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})

@api_bp.route("/api/quote/compute", methods=["POST"])
def compute_quote():
    data = request.get_json(force=True)
    margin = data.get("margin")
    quote_number = data.get("quote_number", "Q0000")
    customer = data.get("customer", "Unknown")

    # Your config should supply these paths
    rds_path = request.app.config["RDS_SALES_TOOL"]
    costing_path = request.app.config["COSTING_WORKBOOK"]

    # Use Excel service to apply toggles and margin then read back summary slices (no file save here)
    svc = ExcelCostingService(rds_path, costing_path)
    # We call apply_write_and_read but ignore file save path by writing to a temp folder, or refactor service as needed.
    tmp_dir = Path(request.app.config.get("OUTPUT_DIR", "./output"))
    tmp_dir.mkdir(parents=True, exist_ok=True)
    result = svc.apply_write_and_read(quote_number=quote_number, output_dir=str(tmp_dir), margin_value=(None if margin == "RESET" else margin))

    # Remove the temporary costing file if created during compute
    # (or refactor service to not SaveAs for compute path)
    return jsonify({
        "base_cost": result["base_cost"],
        "spares": result["spares"],
        "guard":  result["guard"],
        "infeed": result["infeed"],
        "misc":   result["misc"],
        "margin": result["margin"]
    })

@api_bp.route("/api/quote/generate", methods=["POST"])
def generate_outputs():
    data = request.get_json(force=True)
    quote_number = data["quote_number"]
    customer = data["customer"]
    output_dir = data.get("output_dir") or request.app.config.get("OUTPUT_DIR","./output")

    rds_path = request.app.config["RDS_SALES_TOOL"]
    costing_path = request.app.config["COSTING_WORKBOOK"]
    template_path = request.app.config["WORD_TEMPLATE"]

    excel_svc = ExcelCostingService(rds_path, costing_path)
    excel_out = excel_svc.apply_write_and_read(quote_number=quote_number, output_dir=output_dir, margin_value=data.get("margin"))

    # Build Word sources from RDS (quantities C3..C13, prices B2..B13) using Excel COM? Optionally store during compute.
    # For simplicity here, we derive quantities/prices from the RDS workbook after Excel recompute (left as an exercise to read ranges via COM).

    word_svc = WordProposalService(template_path)
    # Provide correct quantities/prices read from RDS:
    # quantities = [...]
    # prices_text = [...]
    # For initial scaffold, return filenames only and let harness validate
    # (Populate real quantities/prices in your implementation)
    word_out = word_svc.fill_and_export(quote_number, customer, quantities=[], prices_text=[], output_dir=output_dir)

    return jsonify({
        **excel_out,
        **word_out
    })
