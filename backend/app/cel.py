from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from sqlalchemy.orm import Session

from .formula import FormulaEngine
from .models import CostingItem, CostingSummary, Pricing, RDSInput
from .summary_layout import (
    BASE_ROLLUP_CELLS,
    SUMMARY_CELL_TO_ROW,
    SUMMARY_ROW_COUNT,
    build_initial_grid,
    data_row_definitions,
)

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
    grid: List[Dict[str, float]] = field(default_factory=list)
    footer: Dict[str, float] = field(default_factory=dict)
    sell_map: Dict[str, float] = field(default_factory=dict)
    cost_map: Dict[str, float] = field(default_factory=dict)


class CostingEmulationLayer:
    """Implements the behaviour of the missing Costing workbook."""

    def __init__(self, session: Session, summary: CostingSummary):
        self.session = session
        self.summary = summary
        self.row_definitions = data_row_definitions()
        if not summary.grid_state:
            summary.grid_state = build_initial_grid()
        if summary.quantities is None:
            summary.quantities = {}
        self.context = self._build_context()
        self.engine = FormulaEngine(self.context)

    def _build_context(self) -> SummaryValues:
        context: SummaryValues = {}
        for item in self.summary.items:
            key = item.metadata_json.get("summary_cell")
            if not key:
                continue
            definition = self.row_definitions.get(
                item.metadata_json.get("row_index"), {}
            )
            base_quantity = definition.get("base_quantity", item.quantity or 1.0)
            quantity_cell = definition.get("quantity_cell")
            quantity_multiplier = 1.0
            if quantity_cell:
                if quantity_cell in self.summary.quantities:
                    quantity_multiplier = float(
                        self.summary.quantities.get(quantity_cell, 0.0)
                    )
                else:
                    quantity_multiplier = 1.0
            context[key] = float(item.unit_cost or 0.0) * max(
                quantity_multiplier, 0.0
            ) * max(base_quantity, 0.0)
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
        rows_state: Dict[int, Dict[str, object]] = {
            row["rowIndex"]: dict(row) for row in build_initial_grid()
        }

        cost_map: Dict[str, float] = {}
        sell_map: Dict[str, float] = {}

        for item in self.summary.items:
            metadata = item.metadata_json or {}
            summary_cell = metadata.get("summary_cell")
            row_index = metadata.get("row_index")
            if not summary_cell or not row_index:
                continue

            definition = self.row_definitions.get(row_index, {})
            base_quantity = definition.get("base_quantity", item.quantity or 1.0)
            quantity_cell = definition.get("quantity_cell")
            quantity_multiplier = 1.0
            qty_display: float | None = None
            if quantity_cell:
                if quantity_cell in self.summary.quantities:
                    qty_display = float(self.summary.quantities.get(quantity_cell, 0.0))
                    quantity_multiplier = qty_display
                else:
                    quantity_multiplier = 1.0

            unit_cost = float(item.unit_cost or 0.0)
            cost = unit_cost * max(base_quantity, 0.0) * max(quantity_multiplier, 0.0)

            override = item.override_margin
            effective_margin = margin if override is None else max(min(override, 0.99), 0.0)
            sell = 0.0
            if cost > 0.0 and effective_margin < 1.0:
                sell = cost / (1.0 - effective_margin)

            cost_map[summary_cell] = cost
            sell_map[summary_cell] = sell

            row = rows_state.get(row_index, {"rowIndex": row_index})
            row.update(
                {
                    "tab": row.get("tab") or definition.get("badge", ""),
                    "description": row.get("description")
                    or definition.get("description")
                    or item.description,
                    "summaryCell": summary_cell,
                    "quantityCell": quantity_cell,
                    "costI": cost,
                    "sellJ": sell,
                    "effMarginK": effective_margin,
                    "overrideL": override,
                    "defaultM": definition.get("default_margin"),
                    "isEditable": True,
                }
            )
            if qty_display is not None:
                row["qtyH"] = qty_display
            rows_state[row_index] = row

        for key in SUMMARY_ROLLUP_ORDER:
            totals[key] = self.context.get(key, 0.0)
            details[key] = {
                "cost": cost_map.get(key, 0.0),
                "sell": sell_map.get(key, 0.0),
                "margin": rows_state.get(
                    SUMMARY_CELL_TO_ROW.get(key, 0), {}
                ).get("effMarginK", margin),
            }
            if SUMMARY_CELL_TO_ROW.get(key) in rows_state:
                row_ref = rows_state[SUMMARY_CELL_TO_ROW[key]]
                row_ref.setdefault("effMarginK", margin)
                row_ref.setdefault("costI", 0.0)
                row_ref.setdefault("sellJ", 0.0)

        subtotal_formula = "SUM(J4:J10,J14,J17,J24,J31)"
        subtotal = self.engine.eval(subtotal_formula).value
        totals["base_total"] = subtotal
        totals["margin"] = margin

        total_cost = sum(cost_map.values())
        total_sell = sum(sell_map.values())
        totals["sell_price"] = subtotal * (1 + margin)

        toggles = {cell: int(self.summary.toggles.get(cell, 0)) for cell in TOGGLE_CELLS}

        override_count = sum(1 for item in self.summary.items if item.override_margin is not None)
        line_count = len(cost_map)
        overall_margin = 0.0
        if total_sell > 0.0 and total_cost > 0.0:
            overall_margin = 1.0 - (total_cost / total_sell)
        base_sell_total = sum(sell_map.get(cell, 0.0) for cell in BASE_ROLLUP_CELLS)
        footer = {
            "total_cost": total_cost,
            "total_sell": total_sell,
            "overall_margin": overall_margin,
            "line_count": line_count,
            "override_count": override_count,
            "override_percent": (override_count / line_count) if line_count else 0.0,
            "base_sell_total": base_sell_total,
        }

        grid = [rows_state.get(idx, {"rowIndex": idx}) for idx in range(1, SUMMARY_ROW_COUNT + 1)]

        self.summary.totals = {
            **totals,
            "sell_map": sell_map,
            "cost_map": cost_map,
            "footer": footer,
        }
        self.summary.grid_state = grid
        self.summary.toggles = toggles
        self.session.add(self.summary)
        return RollupResult(
            summary_values=totals,
            margin=margin,
            toggles=toggles,
            details=details,
            grid=grid,
            footer=footer,
            sell_map=sell_map,
            cost_map=cost_map,
        )

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
        summary = CostingSummary(
            rds_input=rds_input,
            margin=0.24,
            toggles={},
            grid_state=build_initial_grid(),
        )
        session.add(summary)
        session.flush()
    definitions = data_row_definitions()
    if not summary.grid_state:
        summary.grid_state = build_initial_grid()
    if summary.quantities is None:
        summary.quantities = {}

    existing = {item.metadata_json.get("summary_cell"): item for item in summary.items}
    for key in SUMMARY_ROLLUP_ORDER:
        row_index = SUMMARY_CELL_TO_ROW.get(key)
        definition = definitions.get(row_index, {})
        item = existing.get(key)
        if item is None:
            item = CostingItem(
                summary=summary,
                code=key,
                description=definition.get("description", f"Item {key}"),
                quantity=definition.get("base_quantity", 1.0),
                unit_cost=definition.get("unit_cost", 0.0),
                metadata_json={"summary_cell": key},
            )
            session.add(item)
            existing[key] = item
        item.description = definition.get("description", item.description or f"Item {key}")
        item.quantity = definition.get("base_quantity", item.quantity or 1.0)
        item.unit_cost = definition.get("unit_cost", item.unit_cost or 0.0)
        metadata = dict(item.metadata_json or {})
        metadata.update(
            {
                "summary_cell": key,
                "row_index": row_index,
                "default_margin": definition.get("default_margin"),
                "quantity_cell": definition.get("quantity_cell"),
                "badge": definition.get("badge"),
            }
        )
        item.metadata_json = metadata
    session.flush()
    return summary
