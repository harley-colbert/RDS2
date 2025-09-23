from __future__ import annotations

from flask import Blueprint, Flask, current_app, jsonify, request

from .database import session_scope
from .models import RDSInput
from .services import RDSService


api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/quote/<quote_number>", methods=["GET", "POST"])
def quote_detail(quote_number: str):
    with session_scope() as session:
        service = RDSService(session)
        quote = service.get_or_create_quote(quote_number)
        if request.method == "POST":
            payload = request.json or {}
            service.update_input(quote, payload.get("data", {}), payload.get("customer"))
            service.recompute_costing(quote, payload.get("margin"))
            service.append_usage(quote, "update", payload)
        data = {
            "quote_number": quote.quote_number,
            "customer": quote.customer,
            "inputs": quote.data,
            "pricing": {
                "base_total": quote.pricing.subtotal if quote.pricing else 0.0,
                "margin": quote.pricing.margin if quote.pricing else 0.0,
                "sell_price": quote.pricing.total if quote.pricing else 0.0,
                "raw": quote.pricing.data if quote.pricing else {},
            },
            "summary": service.summary_as_dict(quote),
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
