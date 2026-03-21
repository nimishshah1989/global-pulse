"""Pydantic v2 response models for the Model Portfolio engine.

Covers portfolio positions, summary metrics, NAV history, and trade log.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class PortfolioPosition(BaseModel):
    """A single position in the model portfolio."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    name: str
    country: str | None = None
    sector: str | None = None
    weight: float
    entry_price: float
    current_price: float
    entry_date: date
    pnl_pct: float  # current unrealised P&L %
    stop_price: float
    trailing_stop_active: bool = False
    action: str  # latest action from ranking engine


class PortfolioTrade(BaseModel):
    """A single trade (entry or exit) in the portfolio history."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    instrument_id: str
    name: str
    action: str  # ENTER / EXIT_STOP / EXIT_SIGNAL / EXIT_REBALANCE
    price: float
    reason: str


class NAVPoint(BaseModel):
    """One day of NAV history."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    nav: float
    benchmark_nav: float | None = None


class PortfolioSummary(BaseModel):
    """Aggregate portfolio statistics."""

    model_config = ConfigDict(from_attributes=True)

    portfolio_type: str  # "etf_only" for now
    total_positions: int
    cash_weight: float  # 1 - sum(position weights) when < max_positions
    nav: float  # current NAV (started at 100)
    benchmark_nav: float | None = None
    cumulative_return: float
    cagr: float | None = None
    max_drawdown: float
    sharpe_ratio: float | None = None
    win_rate: float | None = None  # % of closed positions that were profitable
    last_rebalance: date | None = None
    regime: str  # BULL / CAUTIOUS / CORRECTION / BEAR


class PortfolioResponse(BaseModel):
    """Full model-portfolio response envelope payload."""

    model_config = ConfigDict(from_attributes=True)

    summary: PortfolioSummary
    positions: list[PortfolioPosition]
    nav_history: list[NAVPoint]
    recent_trades: list[PortfolioTrade]
