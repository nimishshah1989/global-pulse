"""Instrument repository -- all DB queries for instruments.

JSON-backed implementation that reads from data/instrument_map.json,
allowing the API to work without PostgreSQL.
"""

import json
import logging
from pathlib import Path
from typing import Any

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


# Valid country codes derived from the instrument map specification
VALID_COUNTRY_CODES = frozenset({
    "US", "UK", "DE", "FR", "JP", "HK", "CN", "KR", "IN", "TW", "AU", "BR", "CA",
})


class InstrumentRepository:
    """Repository for instrument data backed by instrument_map.json."""

    def __init__(self, session: Any = None) -> None:
        """Initialize repository. Session param accepted for interface compatibility."""
        self._instruments = _load_instruments()

    async def get_all(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return all instruments, optionally filtered.

        Supported filter keys: country, asset_type, hierarchy_level, sector, source.
        """
        results = list(self._instruments)
        if filters:
            for key, value in filters.items():
                results = [i for i in results if i.get(key) == value]
        return results

    async def get_by_id(self, instrument_id: str) -> dict[str, Any] | None:
        """Return a single instrument by its ID, or None if not found."""
        for inst in self._instruments:
            if inst["id"] == instrument_id:
                return inst
        return None

    async def get_by_country(self, country: str) -> list[dict[str, Any]]:
        """Return all instruments belonging to a specific country."""
        return [i for i in self._instruments if i.get("country") == country]

    async def get_by_hierarchy_level(self, level: int) -> list[dict[str, Any]]:
        """Return all instruments at a given hierarchy level."""
        return [i for i in self._instruments if i.get("hierarchy_level") == level]
