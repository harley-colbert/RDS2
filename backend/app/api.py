from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, Flask, current_app, jsonify, request

from .database import session_scope
from .models import RDSInput
from .services import RDSService
from .system_options import (
    CATALOG_VERSION,
    PricingValidationError,
    catalog_payload,
    compute_pricing,
    dropdown_payload,
    validate_inputs,
)


api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/quote/<quote_number>", methods=["GET", "POST"])
def quote_detail(quote_number: str):
    with session_scope() as session:
        service = RDSService(session)
        quote = service.get_or_create_quote(quote_number)
        result_payload: Dict[str, Any] | None = None
        if request.method == "POST":
            payload = request.json or {}
            service.update_input(quote, payload.get("data", {}), payload.get("customer"))
            result_payload = service.recompute_costing(quote, payload.get("margin"))
            service.append_usage(quote, "update", payload)
        summary_payload = service.summary_as_dict(quote)
        data = {
            "quote_number": quote.quote_number,
            "customer": quote.customer,
            "inputs": (quote.data or {}).get("inputs", {}),
            "data": quote.data or {},
            "pricing": {
                "base_total": quote.pricing.subtotal if quote.pricing else 0.0,
                "margin": quote.pricing.margin if quote.pricing else 0.0,
                "sell_price": quote.pricing.total if quote.pricing else 0.0,
                "raw": quote.pricing.data if quote.pricing else {},
            },
            "summary": summary_payload,
            "result": result_payload,
        }
        return jsonify(data)


@api.post("/quote/<quote_number>/margin")
def set_margin(quote_number: str):
    payload = request.json or {}
    margin = float(payload.get("margin", 0.2))
    with session_scope() as session:
        service = RDSService(session)
        quote = service.get_or_create_quote(quote_number)
        result = service.set_margin(quote, margin)
        service.append_usage(quote, "margin_change", {"margin": margin})
        return jsonify(result)


@api.post("/quote/<quote_number>/margin/reset")
def reset_margin(quote_number: str):
    with session_scope() as session:
        service = RDSService(session)
        quote = service.get_or_create_quote(quote_number)
        result = service.reset_margin(quote)
        service.append_usage(quote, "margin_reset", {})
        return jsonify(result)


@api.post("/quote/<quote_number>/toggle")
def toggle_cell(quote_number: str):
    payload = request.json or {}
    cell = payload.get("cell")
    value = int(payload.get("value", 1))
    with session_scope() as session:
        service = RDSService(session)
        quote = service.get_or_create_quote(quote_number)
        result = service.set_toggle(quote, cell, value)
        service.append_usage(quote, "toggle", {"cell": cell, "value": value})
        return jsonify(result)


@api.post("/quote/<quote_number>/summary/<int:row_index>/override")
def summary_override(quote_number: str, row_index: int):
    payload = request.json or {}
    override_value = payload.get("override")
    override = None
    if override_value is not None and override_value != "":
        try:
            override = float(override_value)
        except (TypeError, ValueError):
            return jsonify({"error": "invalid override"}), 400
    with session_scope() as session:
        service = RDSService(session)
        quote = service.get_or_create_quote(quote_number)
        try:
            result = service.set_summary_override(quote, row_index, override)
        except ValueError:
            return jsonify({"error": "row not found"}), 404
        service.append_usage(
            quote,
            "summary_override",
            {"row_index": row_index, "override": override},
        )
        return jsonify(result)


@api.post("/quote/<quote_number>/generate")
def generate_outputs(quote_number: str):
    with session_scope() as session:
        service = RDSService(session)
        quote = service.get_or_create_quote(quote_number)
        config = current_app.config
        result = service.generate_outputs(quote, config)
        return jsonify({k: str(v) if v else None for k, v in result.items()})


def register_api(app: Flask) -> None:
    app.register_blueprint(api)
def _with_catalog_header(response):
    response.headers["X-Catalog-Version"] = CATALOG_VERSION
    return response


@api.get("/dropdowns")
def dropdown_catalog():
    response = jsonify(catalog_payload())
    return _with_catalog_header(response)


@api.get("/dropdowns/<dropdown_id>")
def dropdown_detail(dropdown_id: str):
    payload = dropdown_payload(dropdown_id)
    if payload is None:
        return _with_catalog_header(jsonify({"error": "not found"})), 404
    response = jsonify(payload)
    return _with_catalog_header(response)


@api.post("/price")
def price_quote():
    client_version = request.headers.get("X-Catalog-Version")
    if client_version and client_version != CATALOG_VERSION:
        response = jsonify({"error": "stale catalog", "version": CATALOG_VERSION})
        return _with_catalog_header(response), 409

    payload = request.json or {}
    try:
        inputs = validate_inputs(payload)
    except PricingValidationError as exc:
        response = jsonify({"error": str(exc), "field": exc.field})
        return _with_catalog_header(response), 400

    pricing = compute_pricing(inputs)
    response = jsonify(pricing)
    return _with_catalog_header(response)
