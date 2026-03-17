"""Fetch real OHLCV data from Stooq and yfinance for all mapped instruments."""
import json
import os
import time
import httpx
import yfinance as yf
from datetime import date, timedelta
from pathlib import Path

FETCH_DIR = Path(__file__).parent.parent / "data" / "fetched"
MAP_FILE = Path(__file__).parent.parent / "data" / "instrument_map.json"


def fetch_yfinance_instrument(ticker: str, instrument_id: str, period: str = "2y") -> bool:
    """Fetch OHLCV from yfinance and save to CSV."""
    try:
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            print(f"  SKIP {instrument_id} ({ticker}): no data")
            return False

        # Flatten multi-index columns if present
        if hasattr(data.columns, 'levels'):
            data.columns = data.columns.get_level_values(0)

        # Save to CSV
        filepath = FETCH_DIR / f"{instrument_id}.csv"
        data.to_csv(filepath)
        print(f"  OK {instrument_id} ({ticker}): {len(data)} rows")
        return True
    except Exception as e:
        print(f"  FAIL {instrument_id} ({ticker}): {e}")
        return False


def fetch_stooq_instrument(ticker: str, instrument_id: str, start_date: str, end_date: str) -> bool:
    """Fetch OHLCV from Stooq CSV endpoint."""
    url = f"https://stooq.com/q/d/l/?s={ticker}&d1={start_date}&d2={end_date}&i=d"
    try:
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        if response.status_code != 200:
            print(f"  FAIL {instrument_id} ({ticker}): HTTP {response.status_code}")
            return False

        content = response.text
        if "No data" in content or len(content.strip()) < 50:
            print(f"  SKIP {instrument_id} ({ticker}): no data returned")
            return False

        # Check if it's actually CSV with proper headers
        first_line = content.strip().split('\n')[0].lower()
        if 'date' not in first_line and 'close' not in first_line:
            print(f"  SKIP {instrument_id} ({ticker}): unexpected format: {first_line[:80]}")
            return False

        filepath = FETCH_DIR / f"{instrument_id}.csv"
        filepath.write_text(content)
        lines = len(content.strip().split('\n')) - 1  # minus header
        print(f"  OK {instrument_id} ({ticker}): {lines} rows")
        return True
    except Exception as e:
        print(f"  FAIL {instrument_id} ({ticker}): {e}")
        return False


def main():
    os.makedirs(FETCH_DIR, exist_ok=True)

    with open(MAP_FILE) as f:
        instruments = json.load(f)

    # Separate by source
    yfinance_instruments = [i for i in instruments if i['source'] == 'yfinance']
    stooq_instruments = [i for i in instruments if i['source'] == 'stooq']

    print(f"Total instruments: {len(instruments)}")
    print(f"  yfinance: {len(yfinance_instruments)}")
    print(f"  stooq: {len(stooq_instruments)}")

    # === Fetch yfinance instruments first (more reliable, no rate limiting) ===
    print(f"\n=== Fetching {len(yfinance_instruments)} yfinance instruments ===")
    yf_ok = yf_fail = 0
    for inst in yfinance_instruments:
        ticker = inst['ticker_yfinance']
        if ticker is None:
            print(f"  SKIP {inst['id']}: no yfinance ticker")
            yf_fail += 1
            continue
        if fetch_yfinance_instrument(ticker, inst['id']):
            yf_ok += 1
        else:
            yf_fail += 1

    print(f"\nyfinance results: {yf_ok} OK, {yf_fail} failed")

    # === Fetch Stooq instruments (with rate limiting) ===
    today = date.today()
    start = today - timedelta(days=730)  # 2 years
    start_str = start.strftime('%Y%m%d')
    end_str = today.strftime('%Y%m%d')

    print(f"\n=== Fetching {len(stooq_instruments)} Stooq instruments ===")
    print(f"Date range: {start_str} to {end_str}")
    print(f"Rate limit: 2 seconds between requests")
    stooq_ok = stooq_fail = 0
    for i, inst in enumerate(stooq_instruments):
        ticker = inst['ticker_stooq']
        if ticker is None:
            print(f"  SKIP {inst['id']}: no stooq ticker")
            stooq_fail += 1
            continue
        if fetch_stooq_instrument(ticker, inst['id'], start_str, end_str):
            stooq_ok += 1
        else:
            stooq_fail += 1
            # If we got rate-limited, try yfinance as fallback for ETFs
            yf_ticker = inst.get('ticker_yfinance')
            if yf_ticker is None and inst['asset_type'] in ('country_etf', 'sector_etf', 'global_sector_etf', 'benchmark'):
                # Try using the stooq ticker minus the suffix as yfinance ticker
                yf_fallback = ticker.replace('.US', '').replace('.JP', '.T').replace('^', '')
                if '.' not in yf_fallback and '^' not in ticker:
                    # US ETFs like XLK, SPY etc
                    print(f"    -> Trying yfinance fallback: {yf_fallback}")
                    if fetch_yfinance_instrument(yf_fallback, inst['id']):
                        stooq_fail -= 1
                        stooq_ok += 1
                elif ticker.startswith('^'):
                    # Indices - try with ^ prefix on yfinance
                    yf_fallback = ticker  # yfinance uses same ^SPX etc
                    print(f"    -> Trying yfinance fallback: {yf_fallback}")
                    if fetch_yfinance_instrument(yf_fallback, inst['id']):
                        stooq_fail -= 1
                        stooq_ok += 1

        # Rate limit between stooq requests
        if i < len(stooq_instruments) - 1:
            time.sleep(2)

    print(f"\nStooq results: {stooq_ok} OK, {stooq_fail} failed")
    print(f"\n{'='*50}")
    print(f"TOTAL: {yf_ok + stooq_ok} OK, {yf_fail + stooq_fail} failed out of {len(instruments)}")
    print(f"Data saved to: {FETCH_DIR}")

    # List what we got
    fetched_files = list(FETCH_DIR.glob("*.csv"))
    print(f"\nFiles in {FETCH_DIR}: {len(fetched_files)}")


if __name__ == "__main__":
    main()
