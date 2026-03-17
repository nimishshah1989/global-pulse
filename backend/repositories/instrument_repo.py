"""Instrument repository -- DB-backed with JSON fallback.

Queries the instruments table first. Falls back to instrument_map.json
if the DB is empty or unavailable (for tests and pre-seed operation).
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument

logger = logging.getLogger(__name__)

_INSTRUMENT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "instrument_map.json"

# Module-level cache so we only read the file once
_instruments_cache: list[dict[str, Any]] | None = None


def _load_instruments() -> list[dict[str, Any]]:
    """Load instruments from the JSON mapping file, with caching."""
    global _instruments_cache
    if _instruments_cache is not None:
        return _instruments_cache

    try:
        with open(_INSTRUMENT_MAP_PATH, "r", encoding="utf-8") as f:
            _instruments_cache = json.load(f)
    except FileNotFoundError:
        logger.warning("instrument_map.json not found at %s, using empty list", _INSTRUMENT_MAP_PATH)
        _instruments_cache = []
    return _instruments_cache


def _instrument_to_dict(inst: Instrument) -> dict[str, Any]:
    """Convert an Instrument ORM model to a dictionary."""
    return {
        "id": inst.id,
        "name": inst.name,
        "ticker_stooq": inst.ticker_stooq,
        "ticker_yfinance": inst.ticker_yfinance,
        "source": inst.source,
        "asset_type": inst.asset_type,
        "country": inst.country,
        "sector": inst.sector,
        "hierarchy_level": inst.hierarchy_level,
        "benchmark_id": inst.benchmark_id,
        "currency": inst.currency,
        "liquidity_tier": inst.liquidity_tier,
        "is_active": inst.is_active,
        "metadata": inst.metadata_,
    }


# Valid country codes derived from the instrument map specification
VALID_COUNTRY_CODES = frozenset({
    "US", "UK", "DE", "FR", "JP", "HK", "CN", "KR", "IN", "TW", "AU", "BR", "CA",
})


class InstrumentRepository:
    """Repository for instrument data, DB-backed with JSON fallback."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize repository with an optional DB session."""
        self._session = session
        self._json_instruments = _load_instruments()

    async def _try_db_all(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]] | None:
        """Try to query instruments from the database. Returns None on failure."""
        if self._session is None:
            return None
        try:
            stmt = select(Instrument).where(Instrument.is_active == True)
            if filters:
                if "country" in filters:
                    stmt = stmt.where(Instrument.country == filters["country"])
                if "hierarchy_level" in filters:
                    stmt = stmt.where(Instrument.hierarchy_level == filters["hierarchy_level"])
                if "asset_type" in filters:
                    stmt = stmt.where(Instrument.asset_type == filters["asset_type"])
                if "sector" in filters:
                    stmt = stmt.where(Instrument.sector == filters["sector"])
                if "source" in filters:
                    stmt = stmt.where(Instrument.source == filters["source"])
            result = await self._session.execute(stmt)
            rows = result.scalars().all()
            if not rows:
                return None
            return [_instrument_to_dict(r) for r in rows]
        except Exception:
            logger.debug("DB query failed for instruments, falling back to JSON")
            return None

    async def get_all(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return all instruments, optionally filtered.

        Supported filter keys: country, asset_type, hierarchy_level, sector, source.
        """
        db_result = await self._try_db_all(filters)
        if db_result is not None:
            return db_result

        # JSON fallback
        results = list(self._json_instruments)
        if filters:
            for key, value in filters.items():
                results = [i for i in results if i.get(key) == value]
        return results

    async def get_by_id(self, instrument_id: str) -> dict[str, Any] | None:
        """Return a single instrument by its ID, or None if not found."""
        if self._session is not None:
            try:
                result = await self._session.execute(
                    select(Instrument).where(Instrument.id == instrument_id)
                )
                inst = result.scalar_one_or_none()
                if inst is not None:
                    return _instrument_to_dict(inst)
            except Exception:
                pass

        # JSON fallback
        for inst in self._json_instruments:
            if inst["id"] == instrument_id:
                return inst
        return None

    async def get_by_country(self, country: str) -> list[dict[str, Any]]:
        """Return all instruments belonging to a specific country."""
        return await self.get_all(filters={"country": country})

    async def get_by_hierarchy_level(self, level: int) -> list[dict[str, Any]]:
        """Return all instruments at a given hierarchy level."""
        return await self.get_all(filters={"hierarchy_level": level})
