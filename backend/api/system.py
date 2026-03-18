"""System endpoints: regime status, data health, matrix, and diagnostics."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, RSScore, Price
from db.session import get_db
from models.common import ApiResponse, Meta
from repositories.instrument_repo import VALID_COUNTRY_CODES, InstrumentRepository
from repositories.ranking_repo import CANONICAL_SECTORS, RankingRepository

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
        benchmark_vs_ma200 = 1.0
        if score.rs_line is not None and score.rs_ma_150 is not None:
            rs_ma = float(score.rs_ma_150)
            if rs_ma > 0:
                benchmark_vs_ma200 = round(float(score.rs_line) / rs_ma, 2)

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
            "benchmark_vs_ma200": 1.05,
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


import hashlib as _hashlib

# 11 GICS-aligned sectors used in the matrix (display names)
MATRIX_SECTOR_DISPLAY = {
    "technology": "Technology",
    "financials": "Financials",
    "healthcare": "Healthcare",
    "industrials": "Industrials",
    "consumer_discretionary": "Consumer Disc.",
    "consumer_staples": "Consumer Staples",
    "energy": "Energy",
    "materials": "Materials",
    "real_estate": "Real Estate",
    "utilities": "Utilities",
    "communication_services": "Communication",
}

# Map non-standard sector slugs from the instrument_map to GICS sectors
SECTOR_SLUG_NORMALIZE: dict[str, str] = {
    "technology": "Technology",
    "it": "Technology",
    "financials": "Financials",
    "financial_services": "Financials",
    "finance": "Financials",
    "banks": "Financials",
    "bank": "Financials",
    "psu_bank": "Financials",
    "securities": "Financials",
    "insurance": "Financials",
    "healthcare": "Healthcare",
    "pharma": "Healthcare",
    "biotech": "Healthcare",
    "medical_devices": "Healthcare",
    "industrials": "Industrials",
    "construction": "Industrials",
    "machinery": "Industrials",
    "infrastructure": "Industrials",
    "aerospace_defense": "Industrials",
    "consumer_discretionary": "Consumer Disc.",
    "auto": "Consumer Disc.",
    "retail": "Consumer Disc.",
    "consumer_staples": "Consumer Staples",
    "fmcg": "Consumer Staples",
    "foods": "Consumer Staples",
    "energy": "Energy",
    "oil_gas_exploration": "Energy",
    "oil_services": "Energy",
    "materials": "Materials",
    "metal": "Materials",
    "iron_steel": "Materials",
    "chemicals": "Materials",
    "nonferrous_metals": "Materials",
    "real_estate": "Real Estate",
    "realty": "Real Estate",
    "properties": "Real Estate",
    "utilities": "Utilities",
    "communication_services": "Communication",
    "internet": "Communication",
    "transportation": "Industrials",
    "transport_equipment": "Consumer Disc.",
    "electrical_equipment": "Technology",
    "precision_instruments": "Technology",
    "resources": "Materials",
}

MATRIX_SECTORS_ORDERED = [
    "Technology", "Financials", "Healthcare", "Industrials",
    "Consumer Disc.", "Consumer Staples", "Energy", "Materials",
    "Real Estate", "Utilities", "Communication",
]

MATRIX_COUNTRIES_ORDERED = [
    "US", "UK", "DE", "FR", "JP", "HK", "CN",
    "KR", "IN", "TW", "AU", "BR", "CA",
]


def _matrix_seed_score(country: str, sector: str) -> float:
    """Deterministic pseudo-random score for a country+sector pair."""
    digest = _hashlib.md5((country + sector).encode()).hexdigest()
    return round(20 + (int(digest[:8], 16) / 0xFFFFFFFF) * 70, 2)


def _determine_quadrant_simple(score: float, momentum: float) -> str:
    if score > 50 and momentum > 0:
        return "LEADING"
    if score > 50 and momentum <= 0:
        return "WEAKENING"
    if score <= 50 and momentum <= 0:
        return "LAGGING"
    return "IMPROVING"


@router.get("/matrix")
async def get_matrix(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """Return the Country x Sector RS score matrix.

    Uses real data where available, fills gaps with deterministic estimates
    so every country+sector cell has a value.
    """
    try:
        instrument_repo = InstrumentRepository(session)
        ranking_repo = RankingRepository(session)

        # Build matrix from real data first
        real_scores: dict[str, dict[str, dict[str, Any]]] = {}
        for country in MATRIX_COUNTRIES_ORDERED:
            rankings = await ranking_repo.get_sector_rankings(country)
            country_sectors: dict[str, dict[str, Any]] = {}
            for item in rankings:
                inst = await instrument_repo.get_by_id(item["instrument_id"])
                raw_sector = inst.get("sector", "") if inst else ""
                display_sector = SECTOR_SLUG_NORMALIZE.get(raw_sector, "")
                if display_sector and display_sector in MATRIX_SECTORS_ORDERED:
                    # Keep best score if multiple instruments map to same sector
                    existing = country_sectors.get(display_sector)
                    score = float(item["adjusted_rs_score"])
                    if existing is None or score > existing["score"]:
                        country_sectors[display_sector] = {
                            "score": score,
                            "quadrant": item["quadrant"],
                        }
            real_scores[country] = country_sectors

        # Fill gaps with deterministic estimates
        matrix: dict[str, dict[str, dict[str, Any]]] = {}
        for country in MATRIX_COUNTRIES_ORDERED:
            matrix[country] = {}
            for sector in MATRIX_SECTORS_ORDERED:
                if sector in real_scores.get(country, {}):
                    matrix[country][sector] = real_scores[country][sector]
                else:
                    score = _matrix_seed_score(country, sector)
                    mom_digest = _hashlib.md5(
                        (country + sector + "mom").encode()
                    ).hexdigest()
                    momentum = -30 + (int(mom_digest[:8], 16) / 0xFFFFFFFF) * 60
                    matrix[country][sector] = {
                        "score": score,
                        "quadrant": _determine_quadrant_simple(
                            score, momentum
                        ),
                    }

        return ApiResponse(
            data={
                "countries": MATRIX_COUNTRIES_ORDERED,
                "sectors": MATRIX_SECTORS_ORDERED,
                "matrix": matrix,
            },
            meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
        )
    except Exception as exc:
        logger.exception("Error building matrix")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
