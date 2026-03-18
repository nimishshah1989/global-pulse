"""Daily data refresh job — orchestrates fetchers and RS v2 engine."""
import json
import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

_INSTRUMENT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "instrument_map.json"
_DB_PATH = Path(__file__).resolve().parent.parent / "momentum_compass.db"
_FETCHED_DIR = Path(__file__).resolve().parent.parent / "data" / "fetched"


def _load_instrument_map() -> list[dict]:
    """Load the canonical instrument mapping."""
    try:
        with open(_INSTRUMENT_MAP_PATH, "r", encoding="utf-8") as f:
            instruments: list[dict] = json.load(f)
        logger.info("Loaded %d instruments from map", len(instruments))
        return instruments
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("Failed to load instrument_map.json: %s", exc)
        return []


async def run_stooq_daily_refresh() -> None:
    """Fetch latest daily prices from Stooq for all mapped instruments."""
    start_time = datetime.now(timezone.utc)
    logger.info("Starting Stooq daily refresh at %s", start_time.isoformat())

    instruments = _load_instrument_map()
    stooq_instruments = [i for i in instruments if i.get("source") == "stooq"]
    logger.info("Found %d Stooq instruments to fetch", len(stooq_instruments))

    if not stooq_instruments:
        return

    output_dir = _FETCHED_DIR / "stooq"
    output_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    fail_count = 0

    try:
        from data.stooq_fetcher import StooqFetcher
        fetcher = StooqFetcher()
        today = date.today()

        for instrument in stooq_instruments:
            ticker = instrument.get("ticker_stooq")
            if not ticker:
                continue
            try:
                df = await fetcher.fetch_ohlcv(ticker, today, today)
                if df.is_empty():
                    continue
                out_path = output_dir / f"{instrument['id']}.csv"
                df.write_csv(out_path)
                success_count += 1
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", instrument["id"], exc)
                fail_count += 1
    except ImportError as exc:
        logger.error("Could not import StooqFetcher: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("Stooq refresh done in %.1fs — ok=%d, fail=%d", elapsed, success_count, fail_count)


async def run_yfinance_gap_fill() -> None:
    """Fetch latest prices from yfinance for gap-fill markets."""
    start_time = datetime.now(timezone.utc)
    logger.info("Starting yfinance gap-fill at %s", start_time.isoformat())

    instruments = _load_instrument_map()
    yf_instruments = [i for i in instruments if i.get("source") == "yfinance"]
    logger.info("Found %d yfinance instruments to fetch", len(yf_instruments))

    if not yf_instruments:
        return

    output_dir = _FETCHED_DIR / "yfinance"
    output_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    fail_count = 0

    try:
        from data.yfinance_fetcher import YFinanceFetcher
        fetcher = YFinanceFetcher()

        for instrument in yf_instruments:
            ticker = instrument.get("ticker_yfinance")
            if not ticker:
                continue
            try:
                df = await fetcher.fetch_ohlcv_async(ticker, period="5d")
                if df.is_empty():
                    continue
                out_path = output_dir / f"{instrument['id']}.csv"
                df.write_csv(out_path)
                success_count += 1
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", instrument["id"], exc)
                fail_count += 1
    except ImportError as exc:
        logger.error("Could not import YFinanceFetcher: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("yfinance gap-fill done in %.1fs — ok=%d, fail=%d", elapsed, success_count, fail_count)


async def run_stooq_bulk_download() -> None:
    """Weekly full Stooq bulk download."""
    logger.info("Starting Stooq bulk download")
    try:
        from data.stooq_fetcher import StooqFetcher
        fetcher = StooqFetcher()
        await fetcher.bulk_download()
        logger.info("Stooq bulk download complete")
    except Exception as exc:
        logger.error("Stooq bulk download failed: %s", exc)


async def run_rs_computation() -> None:
    """Run RS v2 engine computation for all active instruments.

    Uses the simplified 3-indicator system (Price Trend, Momentum, OBV).
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Starting RS v2 computation at %s", start_time.isoformat())

    try:
        from engine.rs_engine_v2 import compute_instrument_scores, calculate_regime

        instruments = _load_instrument_map()
        if not instruments:
            return

        conn = sqlite3.connect(str(_DB_PATH))
        inst_map = {i["id"]: i for i in instruments}

        # Load all prices
        all_prices: dict[str, pl.DataFrame] = {}
        cursor = conn.execute("SELECT DISTINCT instrument_id FROM prices")
        priced_ids = [row[0] for row in cursor.fetchall()]

        for iid in priced_ids:
            rows = conn.execute(
                "SELECT date, open, high, low, close, volume FROM prices WHERE instrument_id = ? ORDER BY date ASC",
                (iid,)
            ).fetchall()
            if not rows:
                continue
            df = pl.DataFrame({
                "date": [r[0] for r in rows],
                "open": [float(r[1]) if r[1] else None for r in rows],
                "high": [float(r[2]) if r[2] else None for r in rows],
                "low": [float(r[3]) if r[3] else None for r in rows],
                "close": [float(r[4]) if r[4] else None for r in rows],
                "volume": [float(r[5]) if r[5] else 0.0 for r in rows],
            })
            df = df.with_columns(pl.col("date").str.to_date("%Y-%m-%d"))
            df = df.filter(pl.col("close").is_not_null())
            all_prices[iid] = df

        # Regime
        acwi_prices = all_prices.get("ACWI")
        regime = "RISK_ON"
        if acwi_prices is not None and acwi_prices.height >= 200:
            regime = calculate_regime(acwi_prices)

        logger.info("Regime: %s, computing %d instruments", regime, len(instruments))

        # Clear and recompute
        conn.execute("DELETE FROM rs_scores")
        computed = 0

        for instrument in instruments:
            iid = instrument["id"]
            if iid not in all_prices:
                continue

            asset_prices = all_prices[iid]
            if asset_prices.height < 20:
                continue

            benchmark_id = instrument.get("benchmark_id")
            if benchmark_id and benchmark_id in all_prices:
                benchmark_prices = all_prices[benchmark_id]
            elif "ACWI" in all_prices:
                benchmark_prices = all_prices["ACWI"]
            else:
                continue

            if benchmark_prices.height < 20:
                continue

            try:
                scores = compute_instrument_scores(
                    iid, asset_prices, benchmark_prices, timeframe="medium"
                )
                if scores is None:
                    continue

                latest_date = str(asset_prices["date"].max())
                vol_char_val = 1.0 if scores["volume_character"] == "ACCUMULATION" else 0.0

                conn.execute(
                    """INSERT OR REPLACE INTO rs_scores (
                        instrument_id, date, rs_line, rs_ma_150, rs_trend,
                        rs_pct_1m, rs_pct_3m, rs_pct_6m, rs_pct_12m,
                        rs_composite, rs_momentum, volume_ratio, vol_multiplier,
                        adjusted_rs_score, quadrant, liquidity_tier,
                        extension_warning, regime
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        iid, latest_date,
                        scores["rs_line"], scores["rs_ma"], scores["price_trend"],
                        scores["rs_score"], scores["rs_score"],
                        scores["obv"], scores["obv_ma"],
                        scores["rs_score"], scores["rs_momentum_pct"],
                        vol_char_val, 1.0,
                        scores["rs_score"], scores["action"],
                        instrument.get("liquidity_tier", 2),
                        False, regime,
                    ),
                )
                computed += 1

                if computed % 500 == 0:
                    conn.commit()
            except Exception as exc:
                logger.error("Error computing %s: %s", iid, exc)

        conn.commit()
        conn.close()
        logger.info("RS v2 computation done: %d instruments", computed)

    except Exception as exc:
        logger.error("RS computation failed: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("RS computation completed in %.1fs", elapsed)


async def run_opportunity_scan() -> None:
    """Run opportunity scanner on latest RS scores."""
    logger.info("Opportunity scan — using v2 action-based signals")
    # V2 signals are derived directly from the action matrix
    # No separate scan needed — the action IS the signal


async def run_daily_refresh() -> None:
    """Full daily refresh pipeline."""
    logger.info("Starting full daily refresh pipeline")

    try:
        await run_stooq_daily_refresh()
    except Exception as exc:
        logger.error("Stooq daily refresh failed: %s", exc)

    try:
        await run_yfinance_gap_fill()
    except Exception as exc:
        logger.error("yfinance gap-fill failed: %s", exc)

    try:
        await run_rs_computation()
    except Exception as exc:
        logger.error("RS computation failed: %s", exc)

    logger.info("Full daily refresh pipeline complete")
