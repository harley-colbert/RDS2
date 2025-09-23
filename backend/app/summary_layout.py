from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Mapping

SUMMARY_ROW_COUNT = 59

BASE_ROLLUP_CELLS: List[str] = [
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
]

SUMMARY_ROW_DEFINITIONS: Dict[int, Dict[str, object]] = {
    1: {"description": "Cost Summary"},
    2: {"description": "All values shown in USD"},
    3: {},
    4: {
        "badge": "BASE",
        "description": "Base Frame",
        "summary_cell": "J4",
        "unit_cost": 2500.0,
        "default_margin": 0.24,
    },
    5: {
        "badge": "BASE",
        "description": "Controls Package",
        "summary_cell": "J5",
        "unit_cost": 1250.0,
        "default_margin": 0.24,
    },
    6: {
        "badge": "BASE",
        "description": "Electrical Installation",
        "summary_cell": "J6",
        "unit_cost": 1850.0,
        "default_margin": 0.24,
    },
    7: {
        "badge": "BASE",
        "description": "Mechanical Assembly",
        "summary_cell": "J7",
        "unit_cost": 2650.0,
        "default_margin": 0.24,
    },
    8: {
        "badge": "BASE",
        "description": "Controls Engineering",
        "summary_cell": "J8",
        "unit_cost": 3325.0,
        "default_margin": 0.24,
    },
    9: {
        "badge": "BASE",
        "description": "Mechanical Engineering",
        "summary_cell": "J9",
        "unit_cost": 1525.0,
        "default_margin": 0.24,
    },
    10: {
        "badge": "BASE",
        "description": "Project Management",
        "summary_cell": "J10",
        "unit_cost": 2140.0,
        "default_margin": 0.24,
    },
    11: {},
    12: {},
    13: {},
    14: {
        "badge": "BASE",
        "description": "Factory Acceptance",
        "summary_cell": "J14",
        "unit_cost": 3550.0,
        "default_margin": 0.24,
    },
    15: {},
    16: {},
    17: {
        "badge": "BASE",
        "description": "Installation",
        "summary_cell": "J17",
        "unit_cost": 5125.0,
        "default_margin": 0.24,
    },
    18: {
        "badge": "INFEED",
        "description": "Infeed Conveyor - Option 1",
        "summary_cell": "J18",
        "unit_cost": 1890.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H18",
    },
    19: {
        "badge": "INFEED",
        "description": "Infeed Conveyor - Option 2",
        "summary_cell": "J19",
        "unit_cost": 2275.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H19",
    },
    20: {
        "badge": "INFEED",
        "description": "Infeed Conveyor - Option 3",
        "summary_cell": "J20",
        "unit_cost": 2640.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H20",
    },
    21: {},
    22: {},
    23: {},
    24: {
        "badge": "BASE",
        "description": "Integration Engineering",
        "summary_cell": "J24",
        "unit_cost": 3900.0,
        "default_margin": 0.24,
    },
    25: {},
    26: {},
    27: {},
    28: {},
    29: {},
    30: {},
    31: {
        "badge": "BASE",
        "description": "Commissioning",
        "summary_cell": "J31",
        "unit_cost": 2840.0,
        "default_margin": 0.24,
    },
    32: {
        "badge": "GUARD",
        "description": "Guarding - Option 1",
        "summary_cell": "J32",
        "unit_cost": 4260.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H32",
    },
    33: {
        "badge": "GUARD",
        "description": "Guarding - Option 2",
        "summary_cell": "J33",
        "unit_cost": 4895.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H33",
    },
    34: {},
    35: {},
    36: {},
    37: {},
    38: {
        "badge": "SPARES",
        "description": "Spare Parts Package",
        "summary_cell": "J38",
        "unit_cost": 10069.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H38",
    },
    39: {
        "badge": "SPARES",
        "description": "Spare Saw Blades",
        "summary_cell": "J39",
        "unit_cost": 155.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H39",
    },
    40: {
        "badge": "SPARES",
        "description": "Spare Foam Pads",
        "summary_cell": "J40",
        "unit_cost": 224.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H40",
    },
    41: {},
    42: {},
    43: {},
    44: {},
    45: {
        "badge": "MISC",
        "description": "Transformer - Canada",
        "summary_cell": "J45",
        "unit_cost": 10651.258,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H45",
    },
    46: {
        "badge": "MISC",
        "description": "Transformer - Step Up",
        "summary_cell": "J46",
        "unit_cost": 6401.453,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H46",
    },
    47: {
        "badge": "MISC",
        "description": "Training - Spanish",
        "summary_cell": "J47",
        "unit_cost": 0.0,
        "default_margin": 0.24,
        "quantity_cell": "Summary!H47",
    },
}


SUMMARY_CELL_TO_ROW: Dict[str, int] = {
    definition["summary_cell"]: row_index
    for row_index, definition in SUMMARY_ROW_DEFINITIONS.items()
    if "summary_cell" in definition
}


def build_initial_grid() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for idx in range(1, SUMMARY_ROW_COUNT + 1):
        definition = SUMMARY_ROW_DEFINITIONS.get(idx, {})
        row: Dict[str, object] = {
            "rowIndex": idx,
            "tab": definition.get("badge", ""),
            "description": definition.get("description", ""),
            "tabQty": definition.get("tab_qty"),
            "auxD": definition.get("aux_d"),
            "auxE": definition.get("aux_e"),
            "auxF": definition.get("aux_f"),
            "auxG": definition.get("aux_g"),
            "quantityCell": definition.get("quantity_cell"),
            "summaryCell": definition.get("summary_cell"),
            "defaultM": definition.get("default_margin"),
            "isEditable": bool(definition.get("summary_cell")),
        }
        rows.append(row)
    return rows


def reset_grid_state(rows: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
    return [dict(row) for row in rows]


def base_sell_cells() -> List[str]:
    return list(BASE_ROLLUP_CELLS)


def data_row_definitions() -> Dict[int, Dict[str, object]]:
    return deepcopy(SUMMARY_ROW_DEFINITIONS)

