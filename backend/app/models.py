from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RDSInput(Base):
    __tablename__ = "rds_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_number: Mapped[str] = mapped_column(String(50), unique=True)
    customer: Mapped[Optional[str]] = mapped_column(String(200))
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pricing: Mapped["Pricing"] = relationship("Pricing", back_populates="rds_input", uselist=False)
    costing_summary: Mapped["CostingSummary"] = relationship("CostingSummary", back_populates="rds_input", uselist=False)


class Pricing(Base):
    __tablename__ = "pricing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rds_input_id: Mapped[int] = mapped_column(ForeignKey("rds_inputs.id"), unique=True)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    margin: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    rds_input: Mapped[RDSInput] = relationship("RDSInput", back_populates="pricing")


class CostingSummary(Base):
    __tablename__ = "costing_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rds_input_id: Mapped[int] = mapped_column(ForeignKey("rds_inputs.id"), unique=True)
    margin: Mapped[float] = mapped_column(Float, default=0.0)
    toggles: Mapped[dict] = mapped_column(JSON, default=dict)
    totals: Mapped[dict] = mapped_column(JSON, default=dict)
    grid_state: Mapped[list] = mapped_column(JSON, default=list)
    quantities: Mapped[dict] = mapped_column(JSON, default=dict)

    rds_input: Mapped[RDSInput] = relationship("RDSInput", back_populates="costing_summary")
    items: Mapped[list["CostingItem"]] = relationship("CostingItem", back_populates="summary", cascade="all, delete-orphan")


class CostingItem(Base):
    __tablename__ = "costing_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_id: Mapped[int] = mapped_column(ForeignKey("costing_summary.id"))
    code: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(50), default="base")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    override_margin: Mapped[float | None] = mapped_column(Float, nullable=True)

    summary: Mapped[CostingSummary] = relationship("CostingSummary", back_populates="items")


class UsageLog(Base):
    __tablename__ = "usage_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rds_input_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rds_inputs.id"), nullable=True)
    event: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rds_input: Mapped[Optional[RDSInput]] = relationship("RDSInput")
