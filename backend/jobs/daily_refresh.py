"""Daily data refresh job — orchestrates fetchers and RS engine."""
import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_INSTRUMENT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "instrument_map.json"
_FETCHED_DIR = Path(__file__).resolve().parent.parent / "data" / "fetched"


def _load_instrument_map() -> list[dict]:
    """Load the canonical instrument mapping from instrument_map.json.

    Returns:
        List of instrument dictionaries.
    """
    try:
        with open(_INSTRUMENT_MAP_PATH, "r", encoding="utf-8") as f:
            instruments: list[dict] = json.load(f)
        logger.info("Loaded %d instruments from map", len(instruments))
        return instruments
    except FileNotFoundError:
        logger.error("instrument_map.json not found at %s", _INSTRUMENT_MAP_PATH)
        return []
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse instrument_map.json: %s", exc)
        return []


async def run_stooq_daily_refresh() -> None:
    """Fetch latest daily prices from Stooq CSV endpoint for all mapped instruments.

    Downloads OHLCV data for the current trading day from Stooq's CSV endpoint
    for all instruments where source='stooq' in instrument_map.json.
    Results are saved as CSV files in data/fetched/stooq/.
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Starting Stooq daily refresh at %s", start_time.isoformat())

    instruments = _load_instrument_map()
    stooq_instruments = [i for i in instruments if i.get("source") == "stooq"]
    logger.info("Found %d Stooq instruments to fetch", len(stooq_instruments))

    if not stooq_instruments:
        logger.warning("No Stooq instruments found in instrument map")
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
                logger.debug("Skipping %s — no Stooq ticker", instrument["id"])
                continue

            try:
                df = await fetcher.fetch_ohlcv(ticker, today, today)
                if df.is_empty():
                    logger.debug("No data returned for %s", ticker)
                    continue

                out_path = output_dir / f"{instrument['id']}.csv"
                df.write_csv(out_path)
                success_count += 1
            except Exception as exc:
                logger.error("Failed to fetch %s (%s): %s", instrument["id"], ticker, exc)
                fail_count += 1

    except ImportError as exc:
        logger.error("Could not import StooqFetcher: %s", exc)
    except Exception as exc:
        logger.error("Stooq daily refresh failed: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        "Stooq daily refresh completed in %.1fs — success=%d, failed=%d",
        elapsed,
        success_count,
        fail_count,
    )


async def run_yfinance_gap_fill() -> None:
    """Fetch latest prices from yfinance for gap-fill markets.

    Covers India (NSE), South Korea (KRX), China A-shares (SSE/SZSE),
    Taiwan (TWSE), Australia (ASX), Brazil (B3), Canada (TSX),
    and the ACWI global benchmark.
    Results are saved as CSV files in data/fetched/yfinance/.
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Starting yfinance gap-fill at %s", start_time.isoformat())

    instruments = _load_instrument_map()
    yf_instruments = [i for i in instruments if i.get("source") == "yfinance"]
    logger.info("Found %d yfinance instruments to fetch", len(yf_instruments))

    if not yf_instruments:
        logger.warning("No yfinance instruments found in instrument map")
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
                logger.debug("Skipping %s — no yfinance ticker", instrument["id"])
                continue

            try:
                df = await fetcher.fetch_ohlcv_async(ticker, period="5d")
                if df.is_empty():
                    logger.debug("No data returned for %s", ticker)
                    continue

                out_path = output_dir / f"{instrument['id']}.csv"
                df.write_csv(out_path)
                success_count += 1
            except Exception as exc:
                logger.error("Failed to fetch %s (%s): %s", instrument["id"], ticker, exc)
                fail_count += 1

    except ImportError as exc:
        logger.error("Could not import YFinanceFetcher: %s", exc)
    except Exception as exc:
        logger.error("yfinance gap-fill failed: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        "yfinance gap-fill completed in %.1fs — success=%d, failed=%d",
        elapsed,
        success_count,
        fail_count,
    )


async def run_rs_computation() -> None:
    """Run RS engine computation for all active instruments.

    Loads fetched price CSVs from data/fetched/, computes RS scores
    using the engine modules, and writes results to data/fetched/rs_scores/.
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Starting RS computation at %s", start_time.isoformat())

    instruments = _load_instrument_map()
    if not instruments:
        logger.warning("No instruments loaded — skipping RS computation")
        return

    rs_output_dir = _FETCHED_DIR / "rs_scores"
    rs_output_dir.mkdir(parents=True, exist_ok=True)

    computed_count = 0
    skip_count = 0

    try:
        import polars as pl
        from engine.rs_calculator import RSCalculator
        from engine.volume_analyzer import VolumeAnalyzer
        from engine.quadrant_classifier import classify_quadrant
        from engine.liquidity_scorer import LiquidityScorer
        from engine.regime_filter import calculate_regime
        from decimal import Decimal

        calculator = RSCalculator()
        volume_analyzer = VolumeAnalyzer()
        liquidity_scorer = LiquidityScorer()

        # Try to load price data from fetched CSVs
        stooq_dir = _FETCHED_DIR / "stooq"
        yf_dir = _FETCHED_DIR / "yfinance"

        price_data: dict[str, pl.DataFrame] = {}

        for src_dir in [stooq_dir, yf_dir]:
            if not src_dir.exists():
                continue
            for csv_file in src_dir.glob("*.csv"):
                instrument_id = csv_file.stem
                try:
                    df = pl.read_csv(csv_file, try_parse_dates=True)
                    if not df.is_empty():
                        price_data[instrument_id] = df
                except Exception as exc:
                    logger.warning("Failed to read %s: %s", csv_file, exc)

        if not price_data:
            logger.info("No price data found in fetched directory — skipping RS computation")
            skip_count = len(instruments)
        else:
            # Find benchmark data (ACWI for regime)
            acwi_prices = price_data.get("ACWI")
            regime = "RISK_ON"
            if acwi_prices is not None and "close" in acwi_prices.columns:
                try:
                    regime = calculate_regime(acwi_prices)
                except Exception as exc:
                    logger.warning("Failed to calculate regime: %s", exc)

            logger.info("Global regime: %s", regime)

            for instrument in instruments:
                iid = instrument["id"]
                if iid not in price_data:
                    skip_count += 1
                    continue

                benchmark_id = instrument.get("benchmark_id")
                if benchmark_id and benchmark_id not in price_data:
                    skip_count += 1
                    continue

                try:
                    asset_prices = price_data[iid]
                    benchmark_prices = price_data.get(benchmark_id, asset_prices) if benchmark_id else asset_prices

                    # Stage 1-2: RS line and trend
                    rs_line_df = calculator.calculate_rs_line(asset_prices, benchmark_prices)
                    if rs_line_df.is_empty():
                        skip_count += 1
                        continue

                    rs_trend_df = calculator.calculate_rs_trend(rs_line_df)

                    # Stage 3: Excess returns
                    excess_returns = calculator.calculate_excess_returns(asset_prices, benchmark_prices)

                    # Stage 4: Composite (use 50 as default for missing timeframes)
                    composite = calculator.calculate_composite(
                        pct_1m=Decimal(str(excess_returns.get("1M", Decimal("50")))),
                        pct_3m=Decimal(str(excess_returns.get("3M", Decimal("50")))),
                        pct_6m=Decimal(str(excess_returns.get("6M", Decimal("50")))),
                        pct_12m=Decimal(str(excess_returns.get("12M", Decimal("50")))),
                    )

                    # Stage 6: Volume
                    if "volume" in asset_prices.columns:
                        vol_df = asset_prices.select(["date", "volume"])
                        volume_ratio = volume_analyzer.calculate_volume_ratio(vol_df)
                    else:
                        volume_ratio = Decimal("1.000")

                    vol_multiplier = volume_analyzer.calculate_vol_multiplier(volume_ratio)

                    # Stage 8: Liquidity
                    liquidity_tier = instrument.get("liquidity_tier", 2)

                    adjusted_score = volume_analyzer.calculate_adjusted_rs_score(
                        composite, vol_multiplier, liquidity_tier
                    )

                    # Stage 5: Momentum (simplified — single value)
                    rs_momentum = Decimal("0")

                    # Stage 7: Quadrant
                    quadrant = classify_quadrant(adjusted_score, rs_momentum)

                    # Write result
                    result = {
                        "instrument_id": iid,
                        "rs_composite": str(composite),
                        "adjusted_rs_score": str(adjusted_score),
                        "rs_momentum": str(rs_momentum),
                        "volume_ratio": str(volume_ratio),
                        "vol_multiplier": str(vol_multiplier),
                        "quadrant": quadrant,
                        "liquidity_tier": liquidity_tier,
                        "regime": regime,
                    }

                    import json as json_mod
                    out_path = rs_output_dir / f"{iid}.json"
                    with open(out_path, "w", encoding="utf-8") as f:
                        json_mod.dump(result, f, indent=2)

                    computed_count += 1

                except Exception as exc:
                    logger.error("Failed RS computation for %s: %s", iid, exc)
                    skip_count += 1

    except ImportError as exc:
        logger.error("Could not import engine modules: %s", exc)
    except Exception as exc:
        logger.error("RS computation failed: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        "RS computation completed in %.1fs — computed=%d, skipped=%d",
        elapsed,
        computed_count,
        skip_count,
    )


async def run_opportunity_scan() -> None:
    """Run opportunity scanner on latest RS scores.

    Reads computed RS scores from data/fetched/rs_scores/ and generates
    opportunity signals.
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Starting opportunity scan at %s", start_time.isoformat())

    rs_dir = _FETCHED_DIR / "rs_scores"
    if not rs_dir.exists():
        logger.info("No RS scores directory found — skipping opportunity scan")
        return

    signal_count = 0

    try:
        from engine.opportunity_scanner import OpportunityScanner

        scanner = OpportunityScanner()

        # Load all RS scores
        current_scores: list[dict] = []
        for json_file in rs_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    score = json.load(f)
                    current_scores.append(score)
            except Exception as exc:
                logger.warning("Failed to read %s: %s", json_file, exc)

        if not current_scores:
            logger.info("No RS scores found — skipping opportunity scan")
            return

        # Scan for volume breakouts (doesn't need previous scores)
        signals = scanner.scan_volume_breakouts(current_scores)

        # Scan for extension alerts
        signals.extend(scanner.scan_extension_alerts(current_scores))

        signal_count = len(signals)

        # Write signals to file
        if signals:
            output_dir = _FETCHED_DIR / "opportunities"
            output_dir.mkdir(parents=True, exist_ok=True)

            today_str = date.today().isoformat()
            out_path = output_dir / f"signals_{today_str}.json"

            # Convert Decimal to str for JSON serialization
            serializable_signals = []
            for sig in signals:
                s = dict(sig)
                for key, val in s.items():
                    if hasattr(val, "quantize"):  # Decimal check
                        s[key] = str(val)
                serializable_signals.append(s)

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(serializable_signals, f, indent=2)

            logger.info("Wrote %d signals to %s", signal_count, out_path)

    except ImportError as exc:
        logger.error("Could not import OpportunityScanner: %s", exc)
    except Exception as exc:
        logger.error("Opportunity scan failed: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        "Opportunity scan completed in %.1fs — signals=%d",
        elapsed,
        signal_count,
    )


async def run_daily_refresh() -> None:
    """Full daily refresh — orchestrates all fetchers and RS engine.

    Convenience function that runs the complete daily pipeline:
    1. Stooq daily fetch
    2. yfinance gap-fill
    3. RS computation
    4. Opportunity signal generation
    """
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

    try:
        await run_opportunity_scan()
    except Exception as exc:
        logger.error("Opportunity scan failed: %s", exc)

    logger.info("Full daily refresh pipeline complete")
