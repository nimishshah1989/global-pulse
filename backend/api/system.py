"""System endpoints: regime status, data health, matrix, and diagnostics."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, RSScore, Price
from db.session import get_db
from models.common import ApiResponse, Meta
from repositories.instrument_repo import VALID_COUNTRY_CODES, InstrumentRepository
from repositories.ranking_repo import RankingRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["system"])


async def _try_db_regime(session: AsyncSession) -> dict[str, Any] | None:
    """Try to read the latest regime from rs_scores for ACWI.

    Returns None if no data or on DB error.
    """
    try:
        # Look for ACWI benchmark instrument
        acwi_stmt = (
            select(Instrument.id)
            .where(Instrument.id.like("%ACWI%"))
            .limit(1)
        )
        acwi_result = await session.execute(acwi_stmt)
        acwi_id = acwi_result.scalar_one_or_none()

        if acwi_id is None:
            return None

        # Get the latest RS score for ACWI
        max_date_sub = select(func.max(RSScore.date)).scalar_subquery()
        score_stmt = (
            select(RSScore)
            .where(RSScore.instrument_id == acwi_id)
            .where(RSScore.date == max_date_sub)
        )
        score_result = await session.execute(score_stmt)
        score = score_result.scalar_one_or_none()

        if score is None:
            return None

        regime = score.regime or "RISK_ON"

        # Compute benchmark_vs_ma200 from rs_line / rs_ma_150 as proxy
        benchmark_vs_ma200 = Decimal("1.00")
        if score.rs_line is not None and score.rs_ma_150 is not None:
            rs_ma = Decimal(str(score.rs_ma_150))
            if rs_ma > 0:
                benchmark_vs_ma200 = (
                    Decimal(str(score.rs_line)) / rs_ma
                ).quantize(Decimal("0.01"))

        return {
            "regime": regime,
            "benchmark": "ACWI",
            "benchmark_vs_ma200": benchmark_vs_ma200,
        }
    except Exception as exc:
        logger.debug("DB regime query failed: %s", exc)
        return None


@router.get("/regime")
async def get_regime(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """Return current global risk regime (RISK_ON or RISK_OFF).

    Based on ACWI price vs its 200-day moving average.
    Queries rs_scores for ACWI first; falls back to mock if unavailable.
    """
    db_result = await _try_db_regime(session)
    if db_result is not None:
        return ApiResponse(
            data=db_result,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
        )

    # Mock fallback
    return ApiResponse(
        data={
            "regime": "RISK_ON",
            "benchmark": "ACWI",
            "benchmark_vs_ma200": Decimal("1.05"),
        },
        meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
    )


async def _try_db_data_status(
    session: AsyncSession,
) -> dict[str, Any] | None:
    """Try to read data status from the database. Returns None on failure."""
    try:
        # Count instruments
        inst_count_result = await session.execute(
            select(func.count(Instrument.id))
        )
        inst_count = inst_count_result.scalar() or 0
        if inst_count == 0:
            return None

        # Latest price date
        latest_price_result = await session.execute(
            select(func.max(Price.date))
        )
        latest_price_date = latest_price_result.scalar()

        # Latest RS computation date
        latest_rs_result = await session.execute(
            select(func.max(RSScore.date))
        )
        latest_rs_date = latest_rs_result.scalar()

        # Count prices and RS scores
        price_count_result = await session.execute(
            select(func.count()).select_from(Price)
        )
        price_count = price_count_result.scalar() or 0

        rs_count_result = await session.execute(
            select(func.count()).select_from(RSScore)
        )
        rs_count = rs_count_result.scalar() or 0

        status = "operational" if price_count > 0 and rs_count > 0 else "awaiting_rs_computation" if price_count > 0 else "awaiting_initial_load"

        return {
            "last_stooq_refresh": None,
            "last_yfinance_refresh": None,
            "last_rs_computation": str(latest_rs_date) if latest_rs_date else None,
            "instruments_count": inst_count,
            "latest_price_date": str(latest_price_date) if latest_price_date else None,
            "price_records": price_count,
            "rs_score_records": rs_count,
            "status": status,
        }
    except Exception as exc:
        logger.debug("DB data-status query failed: %s", exc)
        return None


@router.get("/data-status")
async def get_data_status(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """Return last data refresh timestamps and system health."""
    db_result = await _try_db_data_status(session)
    if db_result is not None:
        return ApiResponse(
            data=db_result,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
        )

    # Fallback: no DB session or empty DB
    instrument_repo = InstrumentRepository()
    all_instruments = await instrument_repo.get_all()

    return ApiResponse(
        data={
            "last_stooq_refresh": None,
            "last_yfinance_refresh": None,
            "last_rs_computation": None,
            "instruments_count": len(all_instruments),
            "latest_price_date": None,
            "status": "awaiting_initial_load",
        },
        meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
    )


@router.get("/matrix")
async def get_matrix(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """Return the Country x Sector RS score matrix.

    Rows = sectors, columns = countries. Each cell has a score and quadrant.
    Uses DB-backed repositories with mock fallback.
    """
    try:
        instrument_repo = InstrumentRepository(session)
        ranking_repo = RankingRepository(session)

        # Collect all unique sectors from Level 2 instruments
        all_instruments = await instrument_repo.get_all(
            filters={"hierarchy_level": 2}
        )
        sectors: set[str] = set()
        for inst in all_instruments:
            if inst.get("sector"):
                sectors.add(inst["sector"])

        countries = sorted(VALID_COUNTRY_CODES)
        sorted_sectors = sorted(sectors)

        # Build matrix: country -> sector -> {score, quadrant}
        matrix: dict[str, dict[str, dict[str, Any]]] = {}
        for country in countries:
            rankings = await ranking_repo.get_sector_rankings(country)
            country_sectors: dict[str, dict[str, Any]] = {}
            for item in rankings:
                # Find the sector slug for this instrument
                inst = await instrument_repo.get_by_id(item["instrument_id"])
                if inst and inst.get("sector"):
                    country_sectors[inst["sector"]] = {
                        "score": float(item["adjusted_rs_score"]),
                        "quadrant": item["quadrant"],
                    }
            matrix[country] = country_sectors

        return ApiResponse(
            data={
                "countries": countries,
                "sectors": sorted_sectors,
                "matrix": matrix,
            },
            meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
        )
    except Exception as exc:
        logger.exception("Error building matrix")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
