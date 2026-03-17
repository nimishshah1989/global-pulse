"""System endpoints: regime status, data health, and diagnostics."""

from datetime import datetime, timezone

from fastapi import APIRouter

from models.common import ApiResponse, Meta

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/regime")
async def get_regime() -> ApiResponse[dict[str, str]]:
    """Return current global risk regime (RISK_ON or RISK_OFF).

    Based on ACWI price vs its 200-day moving average.
    Stub: always returns RISK_ON until RS engine is implemented.
    """
    return ApiResponse(
        data={"regime": "RISK_ON"},
        meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
    )


@router.get("/data-status")
async def get_data_status() -> ApiResponse[dict[str, str | None]]:
    """Return last data refresh timestamps and system health.

    Stub: returns placeholder values until data pipeline is implemented.
    """
    return ApiResponse(
        data={
            "last_stooq_refresh": None,
            "last_yfinance_refresh": None,
            "last_rs_computation": None,
            "instrument_count": "0",
            "status": "awaiting_initial_load",
        },
        meta=Meta(timestamp=datetime.now(tz=timezone.utc)),
    )
