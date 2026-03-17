"""Tests for the data pipeline: instrument map validation, fetcher URL construction,
yfinance error handling, and sample data generation.
"""

import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from data.seed_sample import generate_sample_data
from data.stooq_fetcher import StooqFetcher

# yfinance may not be installable in all environments (build dependency issues).
# Mock it if unavailable so tests that don't need real Yahoo data can still run.
try:
    from data.yfinance_fetcher import YFinanceFetcher

    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False
    YFinanceFetcher = None  # type: ignore[assignment, misc]

_INSTRUMENT_MAP_PATH = Path(__file__).parent.parent / "data" / "instrument_map.json"

_REQUIRED_FIELDS = {
    "id",
    "name",
    "source",
    "asset_type",
    "hierarchy_level",
    "currency",
    "liquidity_tier",
}

_VALID_SOURCES = {"stooq", "yfinance"}

_VALID_ASSET_TYPES = {
    "country_index",
    "sector_etf",
    "sector_index",
    "stock",
    "country_etf",
    "global_sector_etf",
    "benchmark",
}

_VALID_HIERARCHY_LEVELS = {1, 2, 3}


@pytest.fixture
def instruments() -> list[dict]:
    """Load the canonical instrument map."""
    with open(_INSTRUMENT_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def instrument_ids(instruments: list[dict]) -> set[str]:
    """Extract all instrument IDs as a set."""
    return {i["id"] for i in instruments}


class TestInstrumentMap:
    """Tests validating the structure and integrity of instrument_map.json."""

    def test_load_instrument_map(self, instruments: list[dict]) -> None:
        """Verify instrument map loads and contains entries."""
        assert isinstance(instruments, list)
        assert len(instruments) > 0

        for instrument in instruments:
            for field in _REQUIRED_FIELDS:
                assert field in instrument, (
                    f"Instrument {instrument.get('id', 'UNKNOWN')} "
                    f"missing required field: {field}"
                )

    def test_instrument_map_unique_ids(self, instruments: list[dict]) -> None:
        """All instrument IDs must be unique."""
        ids = [i["id"] for i in instruments]
        assert len(ids) == len(set(ids)), (
            f"Duplicate IDs found: "
            f"{[x for x in ids if ids.count(x) > 1]}"
        )

    def test_instrument_map_valid_sources(self, instruments: list[dict]) -> None:
        """All sources must be 'stooq' or 'yfinance'."""
        for instrument in instruments:
            assert instrument["source"] in _VALID_SOURCES, (
                f"Instrument {instrument['id']} has invalid source: "
                f"{instrument['source']}"
            )

    def test_instrument_map_valid_benchmarks(
        self,
        instruments: list[dict],
        instrument_ids: set[str],
    ) -> None:
        """All benchmark_ids must reference existing instrument IDs or be null."""
        for instrument in instruments:
            benchmark_id = instrument.get("benchmark_id")
            if benchmark_id is not None:
                assert benchmark_id in instrument_ids, (
                    f"Instrument {instrument['id']} references "
                    f"non-existent benchmark: {benchmark_id}"
                )

    def test_instrument_map_hierarchy_levels(
        self, instruments: list[dict]
    ) -> None:
        """All hierarchy levels must be 1, 2, or 3."""
        for instrument in instruments:
            assert instrument["hierarchy_level"] in _VALID_HIERARCHY_LEVELS, (
                f"Instrument {instrument['id']} has invalid hierarchy_level: "
                f"{instrument['hierarchy_level']}"
            )

    def test_instrument_map_valid_asset_types(
        self, instruments: list[dict]
    ) -> None:
        """All asset types must be from the allowed set."""
        for instrument in instruments:
            assert instrument["asset_type"] in _VALID_ASSET_TYPES, (
                f"Instrument {instrument['id']} has invalid asset_type: "
                f"{instrument['asset_type']}"
            )

    def test_instrument_map_ticker_consistency(
        self, instruments: list[dict]
    ) -> None:
        """Stooq-sourced instruments must have ticker_stooq, yfinance must have ticker_yfinance."""
        for instrument in instruments:
            if instrument["source"] == "stooq":
                assert instrument.get("ticker_stooq") is not None, (
                    f"Stooq instrument {instrument['id']} missing ticker_stooq"
                )
            elif instrument["source"] == "yfinance":
                assert instrument.get("ticker_yfinance") is not None, (
                    f"yfinance instrument {instrument['id']} missing ticker_yfinance"
                )

    def test_instrument_map_has_acwi_benchmark(
        self, instrument_ids: set[str]
    ) -> None:
        """The global ACWI benchmark must exist."""
        assert "ACWI" in instrument_ids

    def test_instrument_map_country_indices_count(
        self, instruments: list[dict]
    ) -> None:
        """Should have at least 14 country indices."""
        country_indices = [
            i for i in instruments if i["asset_type"] == "country_index"
        ]
        assert len(country_indices) >= 14


class TestStooqFetcher:
    """Tests for the Stooq data fetcher."""

    def test_stooq_fetcher_url_format(self) -> None:
        """Verify URL construction follows Stooq CSV download pattern."""
        fetcher = StooqFetcher(base_url="https://stooq.com/q/d/l/")
        url = fetcher.build_url(
            ticker="^SPX",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert url == (
            "https://stooq.com/q/d/l?s=^SPX&d1=20240101&d2=20241231&i=d"
        )

    def test_stooq_fetcher_url_format_stock(self) -> None:
        """Verify URL construction for a US stock ticker."""
        fetcher = StooqFetcher(base_url="https://stooq.com/q/d/l")
        url = fetcher.build_url(
            ticker="AAPL.US",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )
        assert "s=AAPL.US" in url
        assert "d1=20240601" in url
        assert "d2=20240630" in url
        assert "i=d" in url


@pytest.mark.skipif(not _HAS_YFINANCE, reason="yfinance not installed")
class TestYFinanceFetcher:
    """Tests for the yfinance data fetcher."""

    def test_yfinance_fetcher_handles_invalid_ticker(self) -> None:
        """Fetching an invalid ticker should return an empty DataFrame."""
        fetcher = YFinanceFetcher()
        df = fetcher.fetch_ohlcv("XXXINVALIDXXX123", period="5d")
        assert isinstance(df, pl.DataFrame)
        assert df.is_empty()

    def test_yfinance_fetcher_schema(self) -> None:
        """Empty result should have the correct OHLCV column schema."""
        fetcher = YFinanceFetcher()
        df = fetcher.fetch_ohlcv("XXXINVALIDXXX456", period="5d")
        assert set(df.columns) == {"date", "open", "high", "low", "close", "volume"}


class TestSampleDataGeneration:
    """Tests for synthetic sample data generation."""

    @pytest.fixture
    def sample_instruments(self) -> list[dict]:
        """A small set of instruments for testing sample generation."""
        return [
            {
                "id": "TEST_INDEX",
                "name": "Test Index",
                "source": "stooq",
                "asset_type": "country_index",
                "country": "US",
                "sector": None,
                "hierarchy_level": 1,
                "benchmark_id": None,
                "currency": "USD",
                "liquidity_tier": 1,
            },
            {
                "id": "TEST_ETF",
                "name": "Test ETF",
                "source": "stooq",
                "asset_type": "sector_etf",
                "country": "US",
                "sector": "technology",
                "hierarchy_level": 2,
                "benchmark_id": "TEST_INDEX",
                "currency": "USD",
                "liquidity_tier": 1,
            },
            {
                "id": "TEST_CETF",
                "name": "Test Country ETF",
                "source": "stooq",
                "asset_type": "country_etf",
                "country": "JP",
                "sector": None,
                "hierarchy_level": 1,
                "benchmark_id": None,
                "currency": "USD",
                "liquidity_tier": 2,
            },
        ]

    def test_sample_data_generation(
        self, sample_instruments: list[dict]
    ) -> None:
        """Generated data has the correct number of days and all columns."""
        days = 90
        data = generate_sample_data(sample_instruments, days=days, seed=42)

        assert len(data) == len(sample_instruments)

        for inst in sample_instruments:
            inst_id = inst["id"]
            assert inst_id in data
            df = data[inst_id]
            assert len(df) == days
            assert set(df.columns) == {
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
            }

    def test_sample_data_realistic_prices(
        self, sample_instruments: list[dict]
    ) -> None:
        """Generated prices must be positive and in reasonable ranges."""
        data = generate_sample_data(sample_instruments, days=60, seed=42)

        for inst in sample_instruments:
            df = data[inst["id"]]

            # All prices must be positive
            for col in ["open", "high", "low", "close"]:
                col_values = df[col].cast(pl.Float64)
                assert col_values.min() > 0, (
                    f"{inst['id']} has non-positive {col} values"
                )

            # High must be >= Low for each row
            highs = df["high"].cast(pl.Float64)
            lows = df["low"].cast(pl.Float64)
            assert (highs >= lows).all(), (
                f"{inst['id']} has high < low"
            )

            # Volume must be positive
            assert df["volume"].min() > 0, (
                f"{inst['id']} has non-positive volume"
            )

    def test_sample_data_deterministic_with_seed(
        self, sample_instruments: list[dict]
    ) -> None:
        """Same seed should produce identical data."""
        data1 = generate_sample_data(sample_instruments, days=30, seed=123)
        data2 = generate_sample_data(sample_instruments, days=30, seed=123)

        for inst_id in data1:
            assert data1[inst_id].equals(data2[inst_id])

    def test_sample_data_dates_are_weekdays(
        self, sample_instruments: list[dict]
    ) -> None:
        """All generated dates should be weekdays (no weekends)."""
        data = generate_sample_data(
            sample_instruments[:1], days=30, seed=42
        )
        df = list(data.values())[0]
        dates = df["date"].to_list()
        for d in dates:
            assert d.weekday() < 5, f"Found weekend date: {d}"
