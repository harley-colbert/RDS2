from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.cel import CostingEmulationLayer, SUMMARY_ROLLUP_ORDER, ensure_costing_summary
from backend.app.models import Base, CostingItem, RDSInput


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as session:
        yield session


def seed_quote(session: Session) -> RDSInput:
    quote = RDSInput(quote_number="QTEST", data={})
    session.add(quote)
    session.flush()
    summary = ensure_costing_summary(session, quote)
    for idx, item in enumerate(summary.items):
        item.unit_cost = idx + 1
        item.quantity = 1
    session.flush()
    return quote


def test_rollup_base_cost(session: Session) -> None:
    quote = seed_quote(session)
    summary = quote.costing_summary
    layer = CostingEmulationLayer(session, summary)
    result = layer.recompute(0.25)
    assert pytest.approx(result.summary_values["J4"]) == 1.0
    assert pytest.approx(result.summary_values["J47"]) == float(len(SUMMARY_ROLLUP_ORDER))
    assert pytest.approx(result.summary_values["base_total"]) == sum(range(1, 12))
    assert pytest.approx(result.summary_values["sell_price"]) == result.summary_values["base_total"] * 1.25
    assert result.margin == 0.25


def test_force_enable(session: Session) -> None:
    quote = seed_quote(session)
    summary = quote.costing_summary
    CostingEmulationLayer.force_enable_all(summary)
    layer = CostingEmulationLayer(session, summary)
    result = layer.recompute()
    assert all(value == 1 for value in result.toggles.values())
