from __future__ import annotations

import json

import pytest

from backend.app import create_app


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("pricing")
    config_path = tmp_path / "config.json"
    database_path = tmp_path / "pricing.db"
    config_path.write_text(
        json.dumps(
            {
                "DATABASE_URL": f"sqlite:///{database_path}",
                "TEMPLATE_DIR": str(tmp_path / "templates"),
                "OUTPUT_DIR": str(tmp_path / "output"),
                "WORD_TEMPLATE": str(tmp_path / "templates" / "proposal_template.docx"),
                "EXCEL_TEMPLATE": str(tmp_path / "templates" / "costing_template.xlsx"),
            }
        )
    )
    app = create_app(str(config_path))
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


DEFAULT_INPUTS = {
    "sys.infeed_orientation": "Centered",
    "sys.spare_parts_qty": 1,
    "sys.spare_saw_blades_qty": 20,
    "sys.spare_foam_pads_qty": 0,
    "sys.guarding": "Standard",
    "sys.feeding_funneling": "No",
    "sys.transformer": "None",
    "sys.training_lang": "English",
}


def test_dropdown_catalog(client):
    response = client.get("/api/dropdowns")
    assert response.status_code == 200
    assert response.headers["X-Catalog-Version"] == "v1"
    payload = response.get_json()
    assert payload["version"] == "v1"
    assert payload["updatedAt"] == "2025-09-23T00:00:00Z"
    assert len(payload["dropdowns"]) == 8
    orientation = next(item for item in payload["dropdowns"] if item["id"] == "sys.infeed_orientation")
    assert orientation["default"] == "Centered"
    assert orientation["options"] == ["Left", "Centered", "Right"]


def test_dropdown_detail(client):
    response = client.get("/api/dropdowns/sys.transformer")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["options"] == ["None", "Canada", "Step Up"]
    assert payload["default"] == "None"
    missing = client.get("/api/dropdowns/unknown")
    assert missing.status_code == 404
    assert missing.headers["X-Catalog-Version"] == "v1"


def test_price_defaults(client):
    response = client.post(
        "/api/price",
        json={"inputs": DEFAULT_INPUTS},
        headers={"X-Catalog-Version": "v1"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["base"] == pytest.approx(414_320.82)
    assert payload["totals"]["options"] == pytest.approx(13_169.0)
    assert payload["totals"]["grand"] == pytest.approx(427_489.82)
    assert payload["totals"]["margin"] == pytest.approx(0.24)
    option_ids = {item["id"] for item in payload["options"]}
    assert option_ids == {"opt.spare_parts", "opt.saw_blades"}
    assert payload["derived"]["price_per_qty"] == {
        "parts": pytest.approx(10_069),
        "blades": pytest.approx(1_550),
        "pads": pytest.approx(2_240),
    }


def test_price_with_adders(client):
    payload = {"inputs": {**DEFAULT_INPUTS, "sys.guarding": "Tall w/ Netting"}}
    response = client.post("/api/price", json=payload, headers={"X-Catalog-Version": "v1"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["totals"]["options"] == pytest.approx(25_236.8917)
    assert data["totals"]["grand"] == pytest.approx(439_557.7117)
    option_ids = {item["id"] for item in data["options"]}
    assert "opt.guarding_tall_net" in option_ids

    payload = {"inputs": {**DEFAULT_INPUTS, "sys.feeding_funneling": "Side USL"}}
    response = client.post("/api/price", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["totals"]["options"] == pytest.approx(18_374.7466)
    option_ids = {item["id"] for item in data["options"]}
    assert option_ids == {"opt.spare_parts", "opt.saw_blades", "opt.feeding_side_usl"}


def test_price_validation_errors(client):
    bad_payload = {"inputs": {**DEFAULT_INPUTS, "sys.feeding_funneling": "Diagonal"}}
    response = client.post("/api/price", json=bad_payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["field"] == "sys.feeding_funneling"
    assert data["error"] == "invalid enum for sys.feeding_funneling"

    missing_payload = {"inputs": {"sys.spare_parts_qty": 1}}
    response = client.post("/api/price", json=missing_payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["field"] == "sys.spare_saw_blades_qty"


def test_price_rejects_stale_catalog(client):
    response = client.post(
        "/api/price",
        json={"inputs": DEFAULT_INPUTS},
        headers={"X-Catalog-Version": "stale"},
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data["version"] == "v1"
    assert data["error"] == "stale catalog"
