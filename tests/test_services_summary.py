from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import Base
from backend.app.services import RDSService
from backend.app.summary_layout import SUMMARY_CELL_TO_ROW


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as session:
        yield session


def _get_row(result, row_index):
    return next(row for row in result["grid"] if row.get("rowIndex") == row_index)


def test_summary_override_clamps_and_exports(session: Session) -> None:
    service = RDSService(session)
    quote = service.get_or_create_quote("Q-OVERRIDE")
    row_index = SUMMARY_CELL_TO_ROW["J18"]

    result = service.set_summary_override(quote, row_index, 1.2)

    item = next(
        item
        for item in quote.costing_summary.items
        if item.metadata_json.get("row_index") == row_index
    )
    assert item.override_margin == pytest.approx(0.99)

    row = _get_row(result, row_index)
    assert row["overrideL"] == pytest.approx(0.99)
    assert row["effMarginK"] == pytest.approx(0.99)

    assert quote.data["Sheet3"]["B8"] == pytest.approx(result["sell_map"]["J18"])
    assert quote.data["Sheet3"]["B2"] == pytest.approx(result["footer"]["base_sell_total"])
    assert quote.data["Sheet1"]["B12"] == pytest.approx(result["margin"])

    reset_result = service.set_summary_override(quote, row_index, None)

    item = next(
        item
        for item in quote.costing_summary.items
        if item.metadata_json.get("row_index") == row_index
    )
    assert item.override_margin is None

    reset_row = _get_row(reset_result, row_index)
    assert reset_row.get("overrideL") is None
    assert reset_row["effMarginK"] == pytest.approx(quote.costing_summary.margin)

    assert quote.data["Sheet3"]["B8"] == pytest.approx(reset_result["sell_map"]["J18"])
    assert reset_result["sell_map"]["J18"] < result["sell_map"]["J18"]
    assert reset_result["margin"] == pytest.approx(quote.costing_summary.margin)
