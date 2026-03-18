"""Instrument data endpoints."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, Price, RSScore
from db.session import get_db
from models.common import ApiResponse, Meta
from models.instruments import InstrumentResponse
from models.prices import PriceResponse
from models.rs_scores import RSScoreResponse
from repositories.instrument_repo import InstrumentRepository
import hashlib as _hashlib


def _seed_float(instrument_id: str, salt: str = "") -> float:
    """Deterministic float in [0,1) for mock fallback."""
    digest = _hashlib.md5((instrument_id + salt).encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/instruments", tags=["instruments"])


@router.get("", response_model=ApiResponse)
async def list_instruments(
    country: Optional[str] = Query(None, description="Filter by country code (e.g. US, UK, JP)"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    hierarchy_level: Optional[int] = Query(None, description="Filter by hierarchy level (1, 2, or 3)"),
    source: Optional[str] = Query(None, description="Filter by data source (stooq or yfinance)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """List all instruments with optional filters."""
    repo = InstrumentRepository(session)

    filters: dict = {}
    if country is not None:
        filters["country"] = country.upper()
    if asset_type is not None:
        filters["asset_type"] = asset_type
    if hierarchy_level is not None:
        filters["hierarchy_level"] = hierarchy_level
    if source is not None:
        filters["source"] = source

    instruments = await repo.get_all(filters=filters if filters else None)

    # Apply is_active filter if provided
    if is_active is not None:
        instruments = [
            i for i in instruments
            if i.get("is_active", True) == is_active
        ]

    items = [InstrumentResponse(**inst) for inst in instruments]

    return ApiResponse(
        data=items,
        meta=Meta(
            timestamp=datetime.now(timezone.utc),
            count=len(items),
        ),
    )


async def _try_db_prices(
    session: AsyncSession,
    instrument_id: str,
    start_date: Optional[date],
    end_date: Optional[date],
    limit: int,
) -> list[PriceResponse] | None:
    """Try to fetch prices from the database. Returns None if empty."""
    try:
        stmt = (
            select(Price)
            .where(Price.instrument_id == instrument_id)
            .order_by(Price.date.asc())
        )
        if start_date is not None:
            stmt = stmt.where(Price.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Price.date <= end_date)

        result = await session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return None

        # Take last N records
        rows = rows[-limit:]
        return [
            PriceResponse(
                instrument_id=row.instrument_id,
                date=row.date,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in rows
        ]
    except Exception as exc:
        logger.debug("DB price query failed for %s: %s", instrument_id, exc)
        return None


@router.get("/{instrument_id}/prices", response_model=ApiResponse)
async def get_instrument_prices(
    instrument_id: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(365, ge=1, le=3650, description="Max number of price records"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Return OHLCV price history for an instrument.

    Tries the database first. Falls back to generated sample data
    if no real data is available.
    """
    repo = InstrumentRepository(session)
    instrument = await repo.get_by_id(instrument_id)

    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument '{instrument_id}' not found")

    # Try database first
    db_prices = await _try_db_prices(session, instrument_id, start_date, end_date, limit)
    if db_prices is not None:
        return ApiResponse(
            data=db_prices,
            meta=Meta(
                timestamp=datetime.now(timezone.utc),
                count=len(db_prices),
            ),
        )

    # Fallback: generate sample prices
    from data.seed_sample import generate_sample_data

    sample = generate_sample_data([instrument], days=limit, seed=42)
    df = sample.get(instrument_id)

    prices: list[PriceResponse] = []
    if df is not None and not df.is_empty():
        rows = df.to_dicts()

        for row in rows:
            row_date = row["date"]
            if start_date is not None and row_date < start_date:
                continue
            if end_date is not None and row_date > end_date:
                continue
            prices.append(
                PriceResponse(
                    instrument_id=instrument_id,
                    date=row_date,
                    open=row.get("open"),
                    high=row.get("high"),
                    low=row.get("low"),
                    close=row["close"],
                    volume=row.get("volume"),
                )
            )

    prices = prices[-limit:]

    return ApiResponse(
        data=prices,
        meta=Meta(
            timestamp=datetime.now(timezone.utc),
            count=len(prices),
        ),
    )


async def _try_db_rs_scores(
    session: AsyncSession,
    instrument_id: str,
    start_date: Optional[date],
    end_date: Optional[date],
    limit: int,
) -> list[RSScoreResponse] | None:
    """Try to fetch RS scores from the database. Returns None if empty."""
    try:
        stmt = (
            select(RSScore)
            .where(RSScore.instrument_id == instrument_id)
            .order_by(RSScore.date.asc())
        )
        if start_date is not None:
            stmt = stmt.where(RSScore.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(RSScore.date <= end_date)

        result = await session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return None

        rows = rows[-limit:]
        return [
            RSScoreResponse(
                instrument_id=row.instrument_id,
                date=row.date,
                rs_line=float(row.rs_line) if row.rs_line is not None else None,
                rs_ma=float(row.rs_ma_150) if row.rs_ma_150 is not None else None,
                price_trend=row.rs_trend,
                rs_momentum_pct=float(row.rs_momentum) if row.rs_momentum is not None else None,
                momentum_trend="ACCELERATING" if (row.rs_momentum or 0) > 0 else "DECELERATING",
                volume_character="ACCUMULATION" if (row.volume_ratio or 0) > 0.5 else "DISTRIBUTION",
                action=row.quadrant or "WATCH",
                rs_score=float(row.adjusted_rs_score) if row.adjusted_rs_score is not None else 50.0,
                regime=row.regime or "RISK_ON",
            )
            for row in rows
        ]
    except Exception as exc:
        logger.debug("DB RS score query failed for %s: %s", instrument_id, exc)
        return None


@router.get("/{instrument_id}/rs", response_model=ApiResponse)
async def get_instrument_rs(
    instrument_id: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(90, ge=1, le=1000, description="Max number of RS score records"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Return RS score history for an instrument.

    Tries the database first. Falls back to mock RS scores if no real data.
    """
    repo = InstrumentRepository(session)
    instrument = await repo.get_by_id(instrument_id)

    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument '{instrument_id}' not found")

    # Try database first
    db_scores = await _try_db_rs_scores(session, instrument_id, start_date, end_date, limit)
    if db_scores is not None:
        return ApiResponse(
            data=db_scores,
            meta=Meta(
                timestamp=datetime.now(timezone.utc),
                count=len(db_scores),
            ),
        )

    # Fallback: generate mock RS scores
    from data.seed_sample import _generate_trading_dates

    trading_dates = _generate_trading_dates(limit)

    iid = instrument["id"]
    rs_records: list[RSScoreResponse] = []

    base_score = 20 + _seed_float(iid, "score") * 70
    base_momentum = -30 + _seed_float(iid, "momentum") * 60
    vol_raw = 0.5 + _seed_float(iid, "volume") * 1.5
    rs_trend = "OUTPERFORMING" if base_score > 50 else "UNDERPERFORMING"
    pct_1m = _seed_float(iid, "1m") * 100
    pct_3m = _seed_float(iid, "3m") * 100
    pct_6m = _seed_float(iid, "6m") * 100
    pct_12m = _seed_float(iid, "12m") * 100
    extension_warning = pct_3m > 95 and pct_6m > 95 and pct_12m > 90

    for i, d in enumerate(trading_dates):
        if start_date is not None and d < start_date:
            continue
        if end_date is not None and d > end_date:
            continue

        day_offset = (i - limit // 2) * 0.05
        score = round(max(0, min(100, base_score + day_offset)), 2)
        momentum = round(max(-50, min(50, base_momentum + day_offset * 0.3)), 2)

        quadrant: str
        if score > 50 and momentum > 0:
            quadrant = "LEADING"
        elif score > 50 and momentum <= 0:
            quadrant = "WEAKENING"
        elif score <= 50 and momentum <= 0:
            quadrant = "LAGGING"
        else:
            quadrant = "IMPROVING"

        rs_records.append(
            RSScoreResponse(
                instrument_id=iid,
                date=d,
                rs_line=round(100 + day_offset * 0.5, 4),
                rs_ma_150=100.0,
                rs_trend=rs_trend,
                rs_pct_1m=round(pct_1m, 2),
                rs_pct_3m=round(pct_3m, 2),
                rs_pct_6m=round(pct_6m, 2),
                rs_pct_12m=round(pct_12m, 2),
                rs_composite=score,
                rs_momentum=momentum,
                volume_ratio=round(vol_raw, 3),
                vol_multiplier=1.0,
                adjusted_rs_score=score,
                quadrant=quadrant,
                liquidity_tier=instrument.get("liquidity_tier", 2),
                extension_warning=extension_warning,
                regime="RISK_ON",
            )
        )

    rs_records = rs_records[-limit:]

    return ApiResponse(
        data=rs_records,
        meta=Meta(
            timestamp=datetime.now(timezone.utc),
            count=len(rs_records),
        ),
    )
