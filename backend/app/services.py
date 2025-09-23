from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from .cel import CostingEmulationLayer, ensure_costing_summary
from .models import CostingItem, CostingSummary, Pricing, RDSInput, UsageLog
from .excel import CostingWorkbookWriter
from .word import ProposalWriter


CELL_TO_FIELD = {
    "Summary!H18": "infeed_primary",
    "Summary!H19": "infeed_secondary",
    "Summary!H20": "infeed_controls",
    "Summary!H32": "guarding_standard",
    "Summary!H33": "guarding_custom",
    "Summary!H38": "spares_blades",
    "Summary!H39": "spares_foam",
    "Summary!H40": "spares_misc",
    "Summary!H45": "misc_install",
    "Summary!H46": "misc_training",
    "Summary!H47": "misc_freight",
}

SUMMARY_EXPORT_MAP = {
    "Sheet3!B2": "base_total",
    "Sheet3!B3": "J38",
    "Sheet3!B4": "J39",
    "Sheet3!B5": "J40",
    "Sheet3!B6": "J32",
    "Sheet3!B7": "J33",
    "Sheet3!B8": "J18",
    "Sheet3!B9": "J19",
    "Sheet3!B10": "J20",
    "Sheet3!B11": "J45",
    "Sheet3!B12": "J46",
    "Sheet3!B13": "J47",
    "Sheet1!B12": "margin",
}


class RDSService:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_quote(self, quote_number: str, defaults: Dict[str, Any] | None = None) -> RDSInput:
        quote = self.session.query(RDSInput).filter_by(quote_number=quote_number).one_or_none()
        if quote is None:
            quote = RDSInput(quote_number=quote_number, data=defaults or {}, customer=None)
            self.session.add(quote)
            self.session.flush()
            summary = ensure_costing_summary(self.session, quote)
            layer = CostingEmulationLayer(self.session, summary)
            layer.recompute()
        return quote

    def update_input(self, quote: RDSInput, data: Dict[str, Any], customer: str | None = None) -> None:
        quote.data = data
        if customer is not None:
            quote.customer = customer
        self.session.add(quote)
        self.session.flush()

    def recompute_costing(self, quote: RDSInput, margin: float | None = None) -> Dict[str, Any]:
        summary = ensure_costing_summary(self.session, quote)
        layer = CostingEmulationLayer(self.session, summary)
        result = layer.recompute(margin)
        pricing = quote.pricing
        if pricing is None:
            pricing = Pricing(rds_input=quote)
        pricing.subtotal = result.summary_values.get("base_total", 0.0)
        pricing.margin = result.margin
        pricing.total = result.summary_values.get("sell_price", 0.0)
        pricing.data = result.summary_values
        self.session.add(pricing)
        self.session.flush()
        return {
            "totals": result.summary_values,
            "margin": result.margin,
            "toggles": result.toggles,
        }

    def force_enable_options(self, quote: RDSInput) -> Dict[str, Any]:
        summary = ensure_costing_summary(self.session, quote)
        CostingEmulationLayer.force_enable_all(summary)
        return self.recompute_costing(quote)

    def set_margin(self, quote: RDSInput, margin: float) -> Dict[str, Any]:
        return self.recompute_costing(quote, margin)

    def reset_margin(self, quote: RDSInput, default_margin: float = 0.2) -> Dict[str, Any]:
        return self.recompute_costing(quote, default_margin)

    def set_toggle(self, quote: RDSInput, cell: str, value: int) -> Dict[str, Any]:
        summary = ensure_costing_summary(self.session, quote)
        CostingEmulationLayer.set_toggle(summary, cell, value)
        return self.recompute_costing(quote)

    def append_usage(self, quote: RDSInput | None, event: str, payload: Dict[str, Any]) -> None:
        log = UsageLog(rds_input=quote, event=event, payload=payload)
        self.session.add(log)
        self.session.flush()

    def summary_as_dict(self, quote: RDSInput) -> Dict[str, Any]:
        summary = ensure_costing_summary(self.session, quote)
        return {
            "margin": summary.margin,
            "toggles": summary.toggles,
            "totals": summary.totals,
        }

    def ensure_seed_costing(self, quote: RDSInput, seed_data: Dict[str, Dict[str, Any]]) -> None:
        summary = ensure_costing_summary(self.session, quote)
        for key, payload in seed_data.items():
            item = next((i for i in summary.items if i.metadata_json.get("summary_cell") == key), None)
            if item:
                item.quantity = payload.get("quantity", 1.0)
                item.unit_cost = payload.get("unit_cost", 0.0)
                item.description = payload.get("description", item.description)
        self.session.flush()

    def generate_outputs(self, quote: RDSInput, config: Dict[str, Any]) -> Dict[str, Any]:
        summary = ensure_costing_summary(self.session, quote)
        totals = summary.totals or {}
        export = export_summary_for_workbook(totals)
        output_dir = Path(config["OUTPUT_DIR"])
        output_dir.mkdir(parents=True, exist_ok=True)
        quote_number = quote.quote_number
        costing_writer = CostingWorkbookWriter(allow_xlsb=bool(config.get("ALLOW_XLSB")))
        costing_path = costing_writer.write(export, output_dir / f"01 - Q#{quote_number} - Costing")

        template_path = Path(config["WORD_TEMPLATE"])
        if not template_path.exists():
            raise FileNotFoundError(f"Word template not found: {template_path}")
        proposal_writer = ProposalWriter(template_path)
        bookmark_map = self._build_bookmarks(quote, totals)
        proposal_paths = proposal_writer.write(
            bookmark_map,
            output_dir / f"Alliance Automation Proposal #{quote_number} - Dismantling System",
        )

        self.append_usage(quote, "generate", {"costing": str(costing_path), "proposal": str(proposal_paths["docx"])})

        return {
            "costing": costing_path,
            "proposal_docx": proposal_paths["docx"],
            "proposal_pdf": proposal_paths["pdf"],
        }

    def _build_bookmarks(self, quote: RDSInput, totals: Dict[str, float]) -> Dict[str, str]:
        data = quote.data or {}
        sheet3 = data.get("Sheet3", {})
        sheet1 = data.get("Sheet1", {})
        def qty(key: str) -> str:
            return str(sheet3.get(key, 0))

        bookmark_map = {
            "QuoteNum": quote.quote_number,
            "Customer": quote.customer or "Unknown Customer",
            "Layout": "[Layout image not captured - upload via UI]",
            "BasePrice": f"{totals.get('sell_price', 0.0):,.2f}",
            "Date": data.get("generated_at", ""),
            "User": data.get("user", ""),
        }

        price_map = {
            "Spare": totals.get("J38", 0.0),
            "Blade": totals.get("J39", 0.0),
            "Foam": totals.get("J40", 0.0),
            "Tall": totals.get("J32", 0.0),
            "Net": totals.get("J33", 0.0),
            "FrontUSL": totals.get("J18", 0.0),
            "SideUSL": totals.get("J19", 0.0),
            "SideBadger": totals.get("J20", 0.0),
            "Canada": totals.get("J45", 0.0),
            "Step": totals.get("J46", 0.0),
            "Train": totals.get("J47", 0.0),
        }

        for key, value in price_map.items():
            bookmark_map[f"{key}Price"] = f"{value:,.2f}"
            bookmark_map[f"{key}Qty"] = qty({
                "Spare": "C3",
                "Blade": "C4",
                "Foam": "C5",
                "Tall": "C6",
                "Net": "C7",
                "FrontUSL": "C8",
                "SideUSL": "C9",
                "SideBadger": "C10",
                "Canada": "C11",
                "Step": "C12",
                "Train": "C13",
            }[key])

        return bookmark_map


def export_summary_for_workbook(totals: Dict[str, float]) -> Dict[str, float]:
    export: Dict[str, float] = {}
    for cell, key in SUMMARY_EXPORT_MAP.items():
        export[cell] = totals.get(key, 0.0)
    return export
