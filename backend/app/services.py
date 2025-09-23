from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from .cel import CostingEmulationLayer, ensure_costing_summary
from .models import CostingSummary, Pricing, RDSInput, UsageLog
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
    "Sheet3!B2": "base_sell_total",
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
            payload = dict(defaults or {})
            payload.setdefault("inputs", {})
            quote = RDSInput(quote_number=quote_number, data=payload, customer=None)
            self.session.add(quote)
            self.session.flush()
            summary = ensure_costing_summary(self.session, quote)
            layer = CostingEmulationLayer(self.session, summary)
            layer.recompute()
        return quote

    def update_input(self, quote: RDSInput, data: Dict[str, Any], customer: str | None = None) -> None:
        payload = quote.data or {}
        if data:
            for key, value in data.items():
                if isinstance(value, dict):
                    existing = payload.get(key)
                    if not isinstance(existing, dict):
                        existing = {}
                    existing.update(value)
                    payload[key] = existing
                else:
                    payload[key] = value
        quote.data = payload
        summary = ensure_costing_summary(self.session, quote)
        self._sync_summary_quantities(summary, payload.get("inputs", {}))
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
        pricing.subtotal = result.footer.get("base_sell_total", 0.0)
        pricing.margin = result.margin
        pricing.total = result.footer.get("total_sell", 0.0)
        pricing.data = {
            **result.summary_values,
            "sell_map": result.sell_map,
            "cost_map": result.cost_map,
            "footer": result.footer,
        }
        self.session.add(pricing)
        self._apply_summary_exports(quote, result)
        self.session.flush()
        return {
            "totals": result.summary_values,
            "margin": result.margin,
            "toggles": result.toggles,
            "grid": result.grid,
            "footer": result.footer,
            "sell_map": result.sell_map,
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

    def set_summary_override(self, quote: RDSInput, row_index: int, override: float | None) -> Dict[str, Any]:
        summary = ensure_costing_summary(self.session, quote)
        item = next(
            (i for i in summary.items if i.metadata_json.get("row_index") == row_index),
            None,
        )
        if item is None:
            raise ValueError(f"No summary row for index {row_index}")
        if override is None:
            item.override_margin = None
        else:
            item.override_margin = max(min(float(override), 0.99), 0.0)
        self.session.add(item)
        self.session.flush()
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
            "grid": summary.grid_state,
            "footer": (summary.totals or {}).get("footer", {}),
            "sell_map": (summary.totals or {}).get("sell_map", {}),
        }

    def _sync_summary_quantities(self, summary: CostingSummary, inputs: Dict[str, Any]) -> None:
        quantities = summary.quantities or {}

        def set_quantity(cell: str | None, value: float) -> None:
            if cell:
                quantities[cell] = float(value)

        def numeric(field: str) -> int:
            try:
                return int(inputs.get(field, 0) or 0)
            except (TypeError, ValueError):
                return 0

        set_quantity("Summary!H38", numeric("sys.spare_parts_qty"))
        set_quantity("Summary!H39", numeric("sys.spare_saw_blades_qty"))
        set_quantity("Summary!H40", numeric("sys.spare_foam_pads_qty"))

        guarding = inputs.get("sys.guarding")
        set_quantity("Summary!H32", 1 if guarding == "Tall" else 0)
        set_quantity("Summary!H33", 1 if guarding == "Tall w/ Netting" else 0)

        feeding = inputs.get("sys.feeding_funneling")
        set_quantity("Summary!H18", 1 if feeding in {"Front USL", "Front Badger"} else 0)
        set_quantity("Summary!H19", 1 if feeding == "Side USL" else 0)
        set_quantity("Summary!H20", 1 if feeding == "Side Badger" else 0)

        transformer = inputs.get("sys.transformer")
        set_quantity("Summary!H45", 1 if transformer == "Canada" else 0)
        set_quantity("Summary!H46", 1 if transformer == "Step Up" else 0)

        training = inputs.get("sys.training_lang")
        set_quantity("Summary!H47", 1 if training == "English & Spanish" else 0)

        summary.quantities = quantities
        self.session.add(summary)

    def _apply_summary_exports(self, quote: RDSInput, result) -> None:
        payload = quote.data or {}
        sheet3 = payload.get("Sheet3") if isinstance(payload.get("Sheet3"), dict) else {}
        sheet1 = payload.get("Sheet1") if isinstance(payload.get("Sheet1"), dict) else {}

        export_values: Dict[str, float] = {}
        for cell, key in SUMMARY_EXPORT_MAP.items():
            if key == "margin":
                export_values[cell] = result.margin
            elif key == "base_sell_total":
                export_values[cell] = result.footer.get("base_sell_total", 0.0)
            else:
                export_values[cell] = result.sell_map.get(key, 0.0)

        for cell, value in export_values.items():
            sheet_name, address = cell.split("!")
            if sheet_name == "Sheet3":
                sheet3[address] = value
            elif sheet_name == "Sheet1":
                sheet1[address] = value

        payload["Sheet3"] = sheet3
        payload["Sheet1"] = sheet1
        payload.setdefault("inputs", payload.get("inputs", {}))
        quote.data = payload
        self.session.add(quote)

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
    sell_map = totals.get("sell_map", {}) if isinstance(totals, dict) else {}
    footer = totals.get("footer", {}) if isinstance(totals, dict) else {}
    for cell, key in SUMMARY_EXPORT_MAP.items():
        if key == "margin":
            export[cell] = totals.get("margin", 0.0)
        elif key == "base_sell_total":
            export[cell] = footer.get("base_sell_total", 0.0)
        else:
            export[cell] = sell_map.get(key, totals.get(key, 0.0))
    return export
