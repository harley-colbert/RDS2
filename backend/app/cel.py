from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from sqlalchemy.orm import Session

from .formula import FormulaEngine
from .models import CostingItem, CostingSummary, Pricing, RDSInput

SummaryValues = Dict[str, float]
ToggleMap = Dict[str, int]

SUMMARY_ROLLUP_ORDER = [
    "J4",
    "J5",
    "J6",
    "J7",
    "J8",
    "J9",
    "J10",
    "J14",
    "J17",
    "J24",
    "J31",
    "J18",
    "J19",
    "J20",
    "J32",
    "J33",
    "J38",
    "J39",
    "J40",
    "J45",
    "J46",
    "J47",
]

TOGGLE_CELLS = {
    "H18": "infeed_primary",
    "H19": "infeed_secondary",
    "H20": "infeed_controls",
    "H32": "guarding_standard",
    "H33": "guarding_custom",
    "H38": "spares_blades",
    "H39": "spares_foam",
    "H40": "spares_misc",
    "H45": "misc_install",
    "H46": "misc_training",
    "H47": "misc_freight",
}


@dataclass
class RollupResult:
    summary_values: SummaryValues
    margin: float
    toggles: ToggleMap
    details: Dict[str, Dict[str, float]] = field(default_factory=dict)


class CostingEmulationLayer:
    """Implements the behaviour of the missing Costing workbook."""

    def __init__(self, session: Session, summary: CostingSummary):
        self.session = session
        self.summary = summary
        self.context = self._build_context()
        self.engine = FormulaEngine(self.context)

    def _build_context(self) -> SummaryValues:
        context: SummaryValues = {}
        for item in self.summary.items:
            key = item.metadata_json.get("summary_cell")
            if key:
                context[key] = item.quantity * item.unit_cost
        # Ensure missing keys exist with zero
        for key in SUMMARY_ROLLUP_ORDER:
            context.setdefault(key, 0.0)
        return context

    def recompute(self, margin: float | None = None) -> RollupResult:
        if margin is None:
            margin = self.summary.margin
        else:
            self.summary.margin = margin

        totals: SummaryValues = {}
        details: Dict[str, Dict[str, float]] = {}
        for key in SUMMARY_ROLLUP_ORDER:
            totals[key] = self.context.get(key, 0.0)
            details[key] = {key: totals[key]}

        subtotal_formula = "SUM(J4:J10,J14,J17,J24,J31)"
        subtotal = self.engine.eval(subtotal_formula).value
        totals["base_total"] = subtotal
        totals["margin"] = margin
        totals["sell_price"] = subtotal * (1 + margin)

        toggles = {cell: int(self.summary.toggles.get(cell, 0)) for cell in TOGGLE_CELLS}

        self.summary.totals = totals
        self.summary.toggles = toggles
        self.session.add(self.summary)
        return RollupResult(summary_values=totals, margin=margin, toggles=toggles, details=details)

    @classmethod
    def set_toggle(cls, summary: CostingSummary, cell: str, value: int) -> None:
        toggles = summary.toggles or {}
        toggles[cell] = value
        summary.toggles = toggles

    @classmethod
    def force_enable_all(cls, summary: CostingSummary) -> None:
        summary.toggles = {cell: 1 for cell in TOGGLE_CELLS}

    @staticmethod
    def base_cost(totals: SummaryValues) -> float:
        return (
            totals.get("J4", 0.0)
            + totals.get("J5", 0.0)
            + totals.get("J6", 0.0)
            + totals.get("J7", 0.0)
            + totals.get("J8", 0.0)
            + totals.get("J9", 0.0)
            + totals.get("J10", 0.0)
            + totals.get("J14", 0.0)
            + totals.get("J17", 0.0)
            + totals.get("J24", 0.0)
            + totals.get("J31", 0.0)
        )

    def export_summary_grid(self) -> List[Tuple[str, float]]:
        return [(key, self.summary.totals.get(key, 0.0)) for key in SUMMARY_ROLLUP_ORDER]


def ensure_costing_summary(session: Session, rds_input: RDSInput) -> CostingSummary:
    summary = rds_input.costing_summary
    if summary is None:
        summary = CostingSummary(rds_input=rds_input, margin=0.2, toggles={})
        session.add(summary)
        session.flush()
        # Create placeholder items for required cells
        items: List[CostingItem] = []
        for key in SUMMARY_ROLLUP_ORDER:
            items.append(
                CostingItem(
                    summary=summary,
                    code=key,
                    description=f"Placeholder for {key}",
                    quantity=1.0,
                    unit_cost=0.0,
                    metadata_json={"summary_cell": key},
                )
            )
        session.add_all(items)
    return summary
