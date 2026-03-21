"""Portfolio Repository — data access layer for the model portfolio.

Fetches candidate instruments, prices, and RS scores from the database,
then delegates the forward-walk simulation to engine.portfolio_simulator.
"""
from __future__ import annotations

import datetime
import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, Price, RSScore
from engine.portfolio_simulator import simulate_portfolio
from repositories.ranking_repo import (
    _compute_market_regime,
    _BENCHMARK_ID_MAP,
)

logger = logging.getLogger(__name__)

# Asset types treated as ETFs for portfolio filtering
_ETF_TYPES = frozenset({
    "sector_etf", "sector_index", "country_etf", "global_sector_etf",
    "etf", "regional_etf", "commodity_etf", "bond_etf",
})


class PortfolioRepository:
    """Builds a model portfolio from ranking signals and price data."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_model_portfolio(
        self,
        portfolio_type: str = "etf_only",
        country: str | None = None,
        lookback_days: int = 252,
        benchmark_id: str = "ACWI",
    ) -> dict[str, Any]:
        """Build and return the full model portfolio.

        Steps:
        1. Fetch candidate instruments + their RS scores per day.
        2. Fetch price history for all candidates + benchmark.
        3. Delegate forward simulation to portfolio_simulator.
        4. Return summary, current positions, NAV history, recent trades.
        """
        if self._session is None:
            return _empty_response(portfolio_type, benchmark_id)

        cutoff = datetime.date.today() - datetime.timedelta(
            days=int(lookback_days * 1.6),
        )
        bench_price_id = _BENCHMARK_ID_MAP.get(benchmark_id, benchmark_id)

        # 1. Fetch candidate instruments
        candidates = await self._fetch_candidates(portfolio_type, country)
        if not candidates:
            return _empty_response(portfolio_type, benchmark_id)

        inst_ids = [c["instrument_id"] for c in candidates]
        inst_map = {c["instrument_id"]: c for c in candidates}

        # 2. Fetch prices + RS scores
        all_ids = list(set(inst_ids) | {bench_price_id})
        prices_by_id, trading_dates = await self._fetch_prices(all_ids, cutoff)
        scores_by_id_date = await self._fetch_rs_scores(inst_ids, cutoff)

        if not trading_dates:
            return _empty_response(portfolio_type, benchmark_id)

        # Compute regime from benchmark
        regime = self._compute_regime(prices_by_id, bench_price_id)

        # 3. Simulate
        return simulate_portfolio(
            trading_dates=trading_dates,
            inst_map=inst_map,
            prices_by_id=prices_by_id,
            scores_by_id_date=scores_by_id_date,
            bench_price_id=bench_price_id,
            regime=regime,
        )

    # ------------------------------------------------------------------
    # Data fetching helpers
    # ------------------------------------------------------------------

    async def _fetch_candidates(
        self,
        portfolio_type: str,
        country: str | None,
    ) -> list[dict[str, Any]]:
        """Return candidate instruments based on portfolio type."""
        assert self._session is not None

        conditions = [Instrument.is_active == True]  # noqa: E712

        if portfolio_type == "etf_only":
            conditions.append(Instrument.asset_type.in_(list(_ETF_TYPES)))
        elif portfolio_type == "stock_only":
            conditions.append(Instrument.asset_type == "stock")
        else:  # stock_etf — everything
            conditions.append(
                Instrument.asset_type.in_(list(_ETF_TYPES) + ["stock"]),
            )

        if country:
            conditions.append(Instrument.country == country)

        stmt = select(Instrument).where(*conditions)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "instrument_id": r.id,
                "name": r.name,
                "country": r.country,
                "sector": r.sector,
                "asset_type": r.asset_type,
                "benchmark_id": r.benchmark_id,
            }
            for r in rows
        ]

    async def _fetch_prices(
        self,
        instrument_ids: list[str],
        cutoff: datetime.date,
    ) -> tuple[dict[str, list[tuple[datetime.date, float]]], list[datetime.date]]:
        """Return {id: [(date, close), ...]} and sorted list of all dates."""
        assert self._session is not None

        stmt = (
            select(Price.instrument_id, Price.date, Price.close)
            .where(Price.instrument_id.in_(instrument_ids))
            .where(Price.date >= cutoff)
            .order_by(Price.instrument_id, Price.date)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        prices: dict[str, list[tuple[datetime.date, float]]] = defaultdict(list)
        all_dates: set[datetime.date] = set()

        for iid, dt, close in rows:
            c = float(close) if close is not None else 0.0
            prices[iid].append((dt, c))
            all_dates.add(dt)

        sorted_dates = sorted(all_dates)
        return dict(prices), sorted_dates

    async def _fetch_rs_scores(
        self,
        instrument_ids: list[str],
        cutoff: datetime.date,
    ) -> dict[str, dict[datetime.date, dict[str, Any]]]:
        """Return {id: {date: {rs_score, rs_momentum, volume_ratio, rs_trend}}}."""
        assert self._session is not None

        stmt = (
            select(
                RSScore.instrument_id,
                RSScore.date,
                RSScore.adjusted_rs_score,
                RSScore.rs_momentum,
                RSScore.volume_ratio,
                RSScore.rs_trend,
            )
            .where(RSScore.instrument_id.in_(instrument_ids))
            .where(RSScore.date >= cutoff)
            .order_by(RSScore.instrument_id, RSScore.date)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        scores: dict[str, dict[datetime.date, dict[str, Any]]] = defaultdict(dict)
        for iid, dt, adj, mom, vr, trend in rows:
            scores[iid][dt] = {
                "rs_score": float(adj) if adj is not None else 50.0,
                "rs_momentum": float(mom) if mom is not None else 0.0,
                "volume_ratio": float(vr) if vr is not None else 1.0,
                "rs_trend": trend or "UNDERPERFORMING",
            }

        return dict(scores)

    @staticmethod
    def _compute_regime(
        prices_by_id: dict[str, list[tuple[datetime.date, float]]],
        bench_id: str,
    ) -> str:
        """Derive market regime from benchmark vs 200-day MA."""
        bench_prices = prices_by_id.get(bench_id, [])
        if len(bench_prices) < 200:
            return "BULL"

        latest = bench_prices[-1][1]
        ma200 = sum(p[1] for p in bench_prices[-200:]) / 200
        return _compute_market_regime(latest, ma200)


def _empty_response(portfolio_type: str, benchmark_id: str) -> dict[str, Any]:
    """Return a valid but empty portfolio response."""
    return {
        "summary": {
            "portfolio_type": portfolio_type,
            "total_positions": 0,
            "cash_weight": 1.0,
            "nav": 100.0,
            "benchmark_nav": 100.0,
            "cumulative_return": 0.0,
            "cagr": None,
            "max_drawdown": 0.0,
            "sharpe_ratio": None,
            "win_rate": None,
            "last_rebalance": None,
            "regime": "BULL",
        },
        "positions": [],
        "nav_history": [],
        "recent_trades": [],
    }
