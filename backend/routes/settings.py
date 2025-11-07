from __future__ import annotations

import os

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from ..services.app_settings import AppSettings

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")
_store = AppSettings()

_ALLOWED_EXTS = {".xls", ".xlsx", ".xlsb"}


def _is_allowed_cost_grid(path: str) -> bool:
    _, ext = os.path.splitext(path)
    return ext.lower() in _ALLOWED_EXTS


@settings_bp.get("/cost-grid-path")
def get_cost_grid_path():
    path = _store.get("cost_grid_path")
    return jsonify({"path": path})


@settings_bp.put("/cost-grid-path")
def put_cost_grid_path():
    data = request.get_json(silent=True) or {}
    path = (data.get("path") or "").strip()
    dry_run = request.args.get("dry_run", "0") in {"1", "true", "True"}

    if not path:
        return jsonify({"error": "Missing 'path'"}), 400

    if not _is_allowed_cost_grid(path):
        allowed = ", ".join(sorted(_ALLOWED_EXTS))
        return jsonify({"error": f"Unsupported extension. Allowed: {allowed}"}), 400

    if not os.path.isfile(path):
        return jsonify({"error": f"File not found: {path}"}), 400

    if dry_run:
        return jsonify({"ok": True, "validated": True, "path": path})

    _store.set("cost_grid_path", path)
    return jsonify({"ok": True, "path": path})


@settings_bp.post("/cost-grid-upload")
def upload_cost_grid():
    if "file" not in request.files:
        return jsonify({"error": "No file provided as form field 'file'"}), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(uploaded.filename)
    _, ext = os.path.splitext(filename)
    if ext.lower() not in _ALLOWED_EXTS:
        allowed = ", ".join(sorted(_ALLOWED_EXTS))
        return jsonify({"error": f"Unsupported extension. Allowed: {allowed}"}), 400

    save_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "uploads",
        "cost_grid",
    )
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    uploaded.save(save_path)

    _store.set("cost_grid_path", save_path)
    return jsonify({"ok": True, "path": save_path})
