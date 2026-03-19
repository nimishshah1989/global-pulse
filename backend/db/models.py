"""SQLAlchemy ORM models matching the Momentum Compass database schema.

All financial fields use Numeric (never Float) to avoid precision issues.
Compatible with both SQLite (development) and PostgreSQL (production).
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    BigInteger,
    JSON,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Instrument(Base):
    """Master instrument registry."""

    __tablename__ = "instruments"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ticker_stooq: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ticker_yfinance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hierarchy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    benchmark_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=True
    )
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    liquidity_tier: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Relationships
    benchmark = relationship("Instrument", remote_side="Instrument.id", lazy="selectin")
    prices = relationship("Price", back_populates="instrument", lazy="noload")
    rs_scores = relationship("RSScore", back_populates="instrument", lazy="noload")

    __table_args__ = (
        CheckConstraint("source IN ('stooq', 'yfinance')", name="ck_instrument_source"),
        CheckConstraint(
            "liquidity_tier IN (1, 2, 3)", name="ck_instrument_liquidity_tier"
        ),
    )


class Price(Base):
    """Daily OHLCV price data."""

    __tablename__ = "prices"

    instrument_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    instrument = relationship("Instrument", back_populates="prices")


class RSScore(Base):
    """Daily computed RS scores."""

    __tablename__ = "rs_scores"

    instrument_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    # Raw RS data
    rs_line: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    rs_ma_150: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    rs_trend: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Percentile ranks
    rs_pct_1m: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    rs_pct_3m: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    rs_pct_6m: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    rs_pct_12m: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # Composite
    rs_composite: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    rs_momentum: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)

    # Volume
    volume_ratio: Mapped[Optional[float]] = mapped_column(Numeric(6, 3), nullable=True)
    vol_multiplier: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True)

    # Final score
    adjusted_rs_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    quadrant: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    liquidity_tier: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Flags
    extension_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    regime: Mapped[str] = mapped_column(Text, default="RISK_ON")

    instrument = relationship("Instrument", back_populates="rs_scores")


class Constituent(Base):
    """Constituent mapping — which stocks belong to which index/sector."""

    __tablename__ = "constituents"

    index_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), primary_key=True
    )
    stock_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), primary_key=True
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    weight: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)

    index_instrument = relationship(
        "Instrument", foreign_keys=[index_id], lazy="selectin"
    )
    stock_instrument = relationship(
        "Instrument", foreign_keys=[stock_id], lazy="selectin"
    )


class Basket(Base):
    """User-created baskets."""

    __tablename__ = "baskets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    benchmark_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow()
    )
    status: Mapped[str] = mapped_column(Text, default="active")
    weighting_method: Mapped[str] = mapped_column(Text, default="equal")

    benchmark = relationship("Instrument", lazy="selectin")
    positions = relationship("BasketPosition", back_populates="basket", lazy="selectin")
    nav_history = relationship("BasketNAV", back_populates="basket", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')", name="ck_basket_status"
        ),
        CheckConstraint(
            "weighting_method IN ('equal', 'manual', 'rs_weighted')",
            name="ck_basket_weighting",
        ),
    )


class BasketPosition(Base):
    """Positions within a basket."""

    __tablename__ = "basket_positions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    basket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("baskets.id"), nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=False
    )
    weight: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow()
    )
    removed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    status: Mapped[str] = mapped_column(Text, default="active")

    basket = relationship("Basket", back_populates="positions")
    instrument = relationship("Instrument", lazy="selectin")


class BasketNAV(Base):
    """Daily basket NAV tracking."""

    __tablename__ = "basket_nav"

    basket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("baskets.id"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    nav: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    benchmark_nav: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 6), nullable=True
    )
    rs_line: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)

    basket = relationship("Basket", back_populates="nav_history")


class Opportunity(Base):
    """Auto-generated opportunity signals."""

    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    instrument_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    conviction_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow()
    )

    instrument = relationship("Instrument", lazy="selectin")
