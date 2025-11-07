from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Mapping, Tuple


CATALOG_VERSION = "v1"
CATALOG_UPDATED_AT = "2025-09-23T00:00:00Z"


@dataclass(frozen=True)
class Dropdown:
    id: str
    label: str
    options: Tuple[str | int, ...]
    default: str | int
    source: Mapping[str, str]
    tooltip: str | None = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "id": self.id,
            "label": self.label,
            "options": list(self.options),
            "default": self.default,
            "source": dict(self.source),
        }
        if self.tooltip:
            payload["tooltip"] = self.tooltip
        return payload


DROPDOWNS: Tuple[Dropdown, ...] = (
    Dropdown(
        id="sys.infeed_orientation",
        label="Infeed Orientation",
        options=("Left", "Centered", "Right"),
        default="Centered",
        source={"type": "range", "ref": "Sheet2!A2:A4"},
        tooltip="Select orientation for illustration placement",
    ),
    Dropdown(
        id="sys.spare_parts_qty",
        label="Spare Parts Package",
        options=(0, 1),
        default=1,
        source={"type": "inline", "ref": ""},
        tooltip="# of spare parts packages",
    ),
    Dropdown(
        id="sys.spare_saw_blades_qty",
        label="Spare Saw Blades",
        options=(0, 10, 20, 30, 40, 50),
        default=20,
        source={"type": "inline", "ref": ""},
        tooltip="packs of 10 blades",
    ),
    Dropdown(
        id="sys.spare_foam_pads_qty",
        label="Spare Foam Pads",
        options=(0, 10, 20, 30, 40, 50),
        default=0,
        source={"type": "inline", "ref": ""},
        tooltip="packs of 10 foam pads",
    ),
    Dropdown(
        id="sys.guarding",
        label="Guarding",
        options=("Standard", "Tall", "Tall w/ Netting"),
        default="Standard",
        source={"type": "inline", "ref": ""},
        tooltip="Choose guarding height/netting",
    ),
    Dropdown(
        id="sys.feeding_funneling",
        label="Feeding USL/Badger",
        options=("No", "Front USL", "Front Badger", "Side USL", "Side Badger"),
        default="No",
        source={"type": "inline", "ref": ""},
        tooltip="Select funneling style",
    ),
    Dropdown(
        id="sys.transformer",
        label="Transformer",
        options=("None", "Canada", "Step Up"),
        default="None",
        source={"type": "inline", "ref": ""},
        tooltip="Select transformer type",
    ),
    Dropdown(
        id="sys.training_lang",
        label="Training",
        options=("English", "English & Spanish"),
        default="English",
        source={"type": "inline", "ref": ""},
        tooltip="Training language",
    ),
)


DROPDOWN_MAP: Dict[str, Dropdown] = {dropdown.id: dropdown for dropdown in DROPDOWNS}

REQUIRED_FIELDS: Tuple[str, ...] = (
    "sys.spare_parts_qty",
    "sys.spare_saw_blades_qty",
    "sys.spare_foam_pads_qty",
    "sys.guarding",
    "sys.feeding_funneling",
    "sys.transformer",
    "sys.training_lang",
)

NUMERIC_FIELDS: Tuple[str, ...] = (
    "sys.spare_parts_qty",
    "sys.spare_saw_blades_qty",
    "sys.spare_foam_pads_qty",
)


class PricingValidationError(ValueError):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


BASE_PRICE = Decimal("414320.82")
UNIT_PRICES: Dict[str, Decimal] = {
    "opt.spare_parts": Decimal("10069"),
    "opt.saw_blades": Decimal("155"),
    "opt.foam_pads": Decimal("224"),
    "opt.guarding_tall": Decimal("10672.24"),
    "opt.guarding_tall_net": Decimal("12067.8917"),
    "opt.feeding_front": Decimal("3429.7074"),
    "opt.feeding_side_usl": Decimal("5205.7466"),
    "opt.feeding_side_badger": Decimal("5205.7466"),
    "opt.transformer_canada": Decimal("10651.258"),
    "opt.transformer_step": Decimal("6401.453"),
    "opt.training_spanish": Decimal("0"),
}

OPTION_LABELS: Dict[str, str] = {
    "opt.spare_parts": "Spare Parts Package",
    "opt.saw_blades": "Spare Saw Blades",
    "opt.foam_pads": "Spare Foam Pads",
    "opt.guarding_tall": "Taller Guarding",
    "opt.guarding_tall_net": "Taller Guarding and Netting",
    "opt.feeding_front": "Front Funneling USL/Badger",
    "opt.feeding_side_usl": "Side Funneling USL",
    "opt.feeding_side_badger": "Side Funneling Badger",
    "opt.transformer_canada": "Canada Transformer",
    "opt.transformer_step": "Step Up Transformer",
    "opt.training_spanish": "Spanish Training",
}

PRICE_PER_QTY: Dict[str, Decimal] = {
    "parts": UNIT_PRICES["opt.spare_parts"],
    "blades": UNIT_PRICES["opt.saw_blades"] * Decimal(10),
    "pads": UNIT_PRICES["opt.foam_pads"] * Decimal(10),
}

DEFAULT_MARGIN = Decimal("0.24")


def catalog_payload() -> Dict[str, object]:
    return {
        "version": CATALOG_VERSION,
        "updatedAt": CATALOG_UPDATED_AT,
        "dropdowns": [dropdown.to_dict() for dropdown in DROPDOWNS],
    }


def dropdown_payload(dropdown_id: str) -> Dict[str, object] | None:
    dropdown = DROPDOWN_MAP.get(dropdown_id)
    if dropdown is None:
        return None
    payload = dropdown.to_dict()
    payload["version"] = CATALOG_VERSION
    payload["updatedAt"] = CATALOG_UPDATED_AT
    return payload


def _coerce_value(field: str, value: object) -> str | int:
    if field in NUMERIC_FIELDS:
        if isinstance(value, bool):  # guard against True/False
            raise PricingValidationError(f"invalid enum for {field}", field)
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            raise PricingValidationError(f"invalid enum for {field}", field) from None
        return numeric
    if not isinstance(value, str):
        raise PricingValidationError(f"invalid enum for {field}", field)
    return value


def validate_inputs(payload: Mapping[str, object]) -> Dict[str, str | int]:
    if "inputs" not in payload or not isinstance(payload["inputs"], Mapping):
        raise PricingValidationError("inputs must be an object", "inputs")
    inputs_raw = payload["inputs"]
    validated: Dict[str, str | int] = {}

    for field in REQUIRED_FIELDS:
        if field not in inputs_raw:
            raise PricingValidationError(f"missing field: {field}", field)
        validated[field] = _coerce_value(field, inputs_raw[field])

    optional_orientation = inputs_raw.get("sys.infeed_orientation", DROPDOWN_MAP["sys.infeed_orientation"].default)
    if optional_orientation not in DROPDOWN_MAP["sys.infeed_orientation"].options:
        raise PricingValidationError("invalid enum for sys.infeed_orientation", "sys.infeed_orientation")
    validated["sys.infeed_orientation"] = optional_orientation

    for field, value in validated.items():
        dropdown = DROPDOWN_MAP.get(field)
        if dropdown and value not in dropdown.options:
            raise PricingValidationError(f"invalid enum for {field}", field)

    return validated


def _add_option(
    collector: List[Dict[str, object]],
    option_id: str,
    qty: int,
) -> Decimal:
    unit_price = UNIT_PRICES[option_id]
    label = OPTION_LABELS[option_id]
    extended = unit_price * Decimal(qty)
    collector.append(
        {
            "id": option_id,
            "label": label,
            "unit": float(unit_price),
            "qty": qty,
            "extended": float(extended),
        }
    )
    return extended


def compute_pricing(inputs: Mapping[str, str | int]) -> Dict[str, object]:
    options: List[Dict[str, object]] = []
    options_total = Decimal("0")

    spare_parts_qty = int(inputs["sys.spare_parts_qty"])
    if spare_parts_qty:
        options_total += _add_option(options, "opt.spare_parts", spare_parts_qty)

    blades_qty = int(inputs["sys.spare_saw_blades_qty"])
    if blades_qty:
        options_total += _add_option(options, "opt.saw_blades", blades_qty)

    pads_qty = int(inputs["sys.spare_foam_pads_qty"])
    if pads_qty:
        options_total += _add_option(options, "opt.foam_pads", pads_qty)

    guarding = inputs["sys.guarding"]
    if guarding == "Tall":
        options_total += _add_option(options, "opt.guarding_tall", 1)
    elif guarding == "Tall w/ Netting":
        options_total += _add_option(options, "opt.guarding_tall_net", 1)

    feeding = inputs["sys.feeding_funneling"]
    if feeding in {"Front USL", "Front Badger"}:
        options_total += _add_option(options, "opt.feeding_front", 1)
    elif feeding == "Side USL":
        options_total += _add_option(options, "opt.feeding_side_usl", 1)
    elif feeding == "Side Badger":
        options_total += _add_option(options, "opt.feeding_side_badger", 1)

    transformer = inputs["sys.transformer"]
    if transformer == "Canada":
        options_total += _add_option(options, "opt.transformer_canada", 1)
    elif transformer == "Step Up":
        options_total += _add_option(options, "opt.transformer_step", 1)

    training = inputs["sys.training_lang"]
    if training == "English & Spanish":
        options_total += _add_option(options, "opt.training_spanish", 1)

    grand_total = BASE_PRICE + options_total

    return {
        "base": float(BASE_PRICE),
        "options": options,
        "totals": {
            "options": float(options_total),
            "grand": float(grand_total),
            "margin": float(DEFAULT_MARGIN),
        },
        "derived": {
            "price_per_qty": {key: float(value) for key, value in PRICE_PER_QTY.items()},
        },
    }
