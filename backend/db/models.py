"""SQLAlchemy ORM models matching the Momentum Compass database schema.

All financial fields use Numeric (never Float) to avoid precision issues.
"""

import uuid
from datetime import date, datetime

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Instrument(Base):
    """Master instrument registry."""

    __tablename__ = "instruments"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ticker_stooq: Mapped[str | None] = mapped_column(Text, nullable=True)
    ticker_yfinance: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    sector: Mapped[str | None] = mapped_column(Text, nullable=True)
    hierarchy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    benchmark_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=True
    )
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    liquidity_tier: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Relationships
    benchmark = relationship("Instrument", remote_side="Instrument.id", lazy="selectin")
    prices = relationship("Price", back_populates="instrument", lazy="selectin")
    rs_scores = relationship("RSScore", back_populates="instrument", lazy="selectin")

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
    open: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    instrument = relationship("Instrument", back_populates="prices")


class RSScore(Base):
    """Daily computed RS scores."""

    __tablename__ = "rs_scores"

    instrument_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    # Raw RS data
    rs_line: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rs_ma_150: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rs_trend: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Percentile ranks
    rs_pct_1m: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    rs_pct_3m: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    rs_pct_6m: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    rs_pct_12m: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Composite
    rs_composite: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    rs_momentum: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    # Volume
    volume_ratio: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    vol_multiplier: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    # Final score
    adjusted_rs_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    quadrant: Mapped[str | None] = mapped_column(Text, nullable=True)
    liquidity_tier: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
    weight: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True)

    index_instrument = relationship(
        "Instrument", foreign_keys=[index_id], lazy="selectin"
    )
    stock_instrument = relationship(
        "Instrument", foreign_keys=[stock_id], lazy="selectin"
    )


class Basket(Base):
    """User-created baskets."""

    __tablename__ = "baskets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    benchmark_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    basket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baskets.id"), nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=False
    )
    weight: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, default="active")

    basket = relationship("Basket", back_populates="positions")
    instrument = relationship("Instrument", lazy="selectin")


class BasketNAV(Base):
    """Daily basket NAV tracking."""

    __tablename__ = "basket_nav"

    basket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baskets.id"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    nav: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    benchmark_nav: Mapped[float | None] = mapped_column(
        Numeric(14, 6), nullable=True
    )
    rs_line: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)

    basket = relationship("Basket", back_populates="nav_history")


class Opportunity(Base):
    """Auto-generated opportunity signals."""

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instrument_id: Mapped[str] = mapped_column(
        Text, ForeignKey("instruments.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    conviction_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    instrument = relationship("Instrument", lazy="selectin")
