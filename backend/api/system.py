"""System endpoints: regime status, data health, matrix, and diagnostics."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException

from models.common import ApiResponse, Meta
from repositories.instrument_repo import VALID_COUNTRY_CODES, InstrumentRepository
from repositories.ranking_repo import RankingRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["system"])


@router.get("/regime")
async def get_regime() -> ApiResponse[dict[str, Any]]:
    """Return current global risk regime (RISK_ON or RISK_OFF).

    Based on ACWI price vs its 200-day moving average.
    Stub: returns RISK_ON with mock benchmark_vs_ma200 until RS engine is live.
    """
    return ApiResponse(
        data={
            "regime": "RISK_ON",
            "benchmark": "ACWI",
            "benchmark_vs_ma200": Decimal("1.05"),
        },
        meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
    )


@router.get("/data-status")
async def get_data_status() -> ApiResponse[dict[str, Any]]:
    """Return last data refresh timestamps and system health."""
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
async def get_matrix() -> ApiResponse[dict[str, Any]]:
    """Return the Country x Sector RS score matrix.

    Rows = sectors, columns = countries. Each cell has a score and quadrant.
    """
    try:
        instrument_repo = InstrumentRepository()
        ranking_repo = RankingRepository()

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
