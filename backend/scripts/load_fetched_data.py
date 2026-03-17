"""Load all fetched CSV files into Polars DataFrames, normalize, and print summary."""
import polars as pl
from pathlib import Path

FETCH_DIR = Path(__file__).parent.parent / "data" / "fetched"


def load_all_fetched() -> dict[str, pl.DataFrame]:
    """Load all fetched CSV files into Polars DataFrames."""
    results = {}
    errors = []

    csv_files = sorted(FETCH_DIR.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files in {FETCH_DIR}\n")
    print(f"{'Instrument':<20} {'Rows':>6} {'Start':>12} {'End':>12} {'Latest Close':>14}")
    print("-" * 70)

    for csv_file in csv_files:
        instrument_id = csv_file.stem
        try:
            df = pl.read_csv(csv_file)

            # Normalize column names to lowercase
            col_map = {c: c.lower().strip() for c in df.columns}
            df = df.rename(col_map)

            # Ensure required columns exist
            if 'date' not in df.columns or 'close' not in df.columns:
                errors.append(f"  SKIP {instrument_id}: missing required columns, has: {df.columns}")
                continue

            # Build select expressions
            select_exprs = [
                pl.col('date').str.to_date().alias('date'),
                pl.col('close').cast(pl.Float64).alias('close'),
            ]

            # Optional columns
            for col_name in ['open', 'high', 'low']:
                if col_name in df.columns:
                    select_exprs.append(pl.col(col_name).cast(pl.Float64).alias(col_name))
                else:
                    select_exprs.append(pl.lit(None).cast(pl.Float64).alias(col_name))

            if 'volume' in df.columns:
                select_exprs.append(pl.col('volume').cast(pl.Int64).alias('volume'))
            else:
                select_exprs.append(pl.lit(0).cast(pl.Int64).alias('volume'))

            df = df.select(select_exprs).sort('date')

            # Drop rows with null close
            df = df.filter(pl.col('close').is_not_null())

            if len(df) == 0:
                errors.append(f"  SKIP {instrument_id}: 0 rows after filtering")
                continue

            # Reorder columns consistently
            df = df.select(['date', 'open', 'high', 'low', 'close', 'volume'])

            results[instrument_id] = df

            date_min = df['date'].min()
            date_max = df['date'].max()
            latest_close = df['close'][-1]
            print(f"{instrument_id:<20} {len(df):>6} {str(date_min):>12} {str(date_max):>12} {latest_close:>14.2f}")

        except Exception as e:
            errors.append(f"  FAIL {instrument_id}: {e}")

    print("-" * 70)
    print(f"\nLoaded: {len(results)} instruments")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(err)

    return results


def print_coverage_summary(results: dict[str, pl.DataFrame]) -> None:
    """Print a summary of data coverage."""
    import json

    map_file = Path(__file__).parent.parent / "data" / "instrument_map.json"
    with open(map_file) as f:
        instruments = json.load(f)

    mapped_ids = {i['id'] for i in instruments}
    fetched_ids = set(results.keys())

    missing = mapped_ids - fetched_ids
    extra = fetched_ids - mapped_ids

    print(f"\n{'='*50}")
    print(f"COVERAGE SUMMARY")
    print(f"{'='*50}")
    print(f"Mapped instruments:  {len(mapped_ids)}")
    print(f"Fetched & loaded:    {len(fetched_ids)}")
    print(f"Coverage:            {len(fetched_ids)}/{len(mapped_ids)} ({100*len(fetched_ids)/len(mapped_ids):.1f}%)")

    if missing:
        print(f"\nMissing ({len(missing)}):")
        for m in sorted(missing):
            inst = next((i for i in instruments if i['id'] == m), None)
            name = inst['name'] if inst else '?'
            print(f"  - {m}: {name}")

    if extra:
        print(f"\nExtra (not in map): {sorted(extra)}")

    # Date range stats
    all_starts = [df['date'].min() for df in results.values()]
    all_ends = [df['date'].max() for df in results.values()]
    row_counts = [len(df) for df in results.values()]

    print(f"\nDate range: {min(all_starts)} to {max(all_ends)}")
    print(f"Rows per instrument: min={min(row_counts)}, max={max(row_counts)}, avg={sum(row_counts)/len(row_counts):.0f}")


if __name__ == "__main__":
    results = load_all_fetched()
    print_coverage_summary(results)
