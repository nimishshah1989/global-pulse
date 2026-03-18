"""Fix instrument IDs from the initial bulk ingest.

The initial ingest created IDs like "AADR.US_US" (double suffix) and
"SPX.US_US" for indices. This script corrects them to match
instrument_map.json format: "AADR_US" for ETFs, "SPX" for indices.

Usage:
    cd backend
    python3 -m scripts.fix_instrument_ids          # dry run
    python3 -m scripts.fix_instrument_ids --apply   # actually rename
"""

import argparse
import logging
import sqlite3
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _BACKEND_ROOT / "momentum_compass.db"


def fix_ids(db_path=None, apply=False):
    if db_path is None:
        db_path = _DEFAULT_DB

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get all instruments
    rows = cursor.execute("SELECT id, asset_type, ticker_stooq FROM instruments").fetchall()
    logger.info("Total instruments: %d", len(rows))

    renames = []  # (old_id, new_id)

    for old_id, asset_type, ticker_stooq in rows:
        new_id = old_id

        # Fix double-suffix: "AADR.US_US" → "AADR_US"
        # Pattern: TICKER.REGION_REGION
        m = re.match(r'^(.+)\.([A-Z]{2})_\2$', old_id)
        if m:
            ticker, region = m.group(1), m.group(2)
            if asset_type == "country_index":
                new_id = ticker  # Indices: just "SPX"
            else:
                new_id = "{}_{}".format(ticker, region)  # ETFs: "AADR_US"

        # Fix indices that got _REGION suffix: "SPX_US" → "SPX"
        if asset_type == "country_index" and re.match(r'^[A-Z0-9]+_[A-Z]{2}$', old_id):
            new_id = old_id.rsplit('_', 1)[0]

        if new_id != old_id:
            renames.append((old_id, new_id))

    logger.info("IDs to rename: %d", len(renames))

    if not renames:
        logger.info("No IDs need fixing — all correct!")
        conn.close()
        return

    # Show some examples
    for old, new in renames[:20]:
        logger.info("  %s → %s", old, new)
    if len(renames) > 20:
        logger.info("  ... and %d more", len(renames) - 20)

    if not apply:
        logger.info("DRY RUN — use --apply to execute renames")
        conn.close()
        return

    # Check for conflicts
    existing_ids = {r[0] for r in rows}
    new_ids = {new for _, new in renames}
    conflicts = new_ids & existing_ids - {old for old, _ in renames}
    if conflicts:
        logger.warning("Conflicts with existing IDs (will skip): %s", conflicts)

    # Execute renames in a transaction
    success = 0
    skipped = 0
    conn.execute("BEGIN")
    try:
        for old_id, new_id in renames:
            if new_id in existing_ids and new_id not in {r[0] for r in renames}:
                logger.warning("Skip %s → %s (target exists)", old_id, new_id)
                skipped += 1
                continue

            # Update prices first (FK reference)
            cursor.execute("UPDATE prices SET instrument_id = ? WHERE instrument_id = ?",
                         (new_id, old_id))
            # Update rs_scores
            cursor.execute("UPDATE rs_scores SET instrument_id = ? WHERE instrument_id = ?",
                         (new_id, old_id))
            # Update instrument itself
            cursor.execute("UPDATE instruments SET id = ? WHERE id = ?",
                         (new_id, old_id))
            success += 1

        conn.commit()
        logger.info("Renamed %d instruments (%d skipped)", success, skipped)
    except Exception as e:
        conn.rollback()
        logger.error("ROLLBACK — error: %s", e)
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Fix instrument IDs from bulk ingest")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="Actually execute renames")
    args = parser.parse_args()
    fix_ids(db_path=args.db, apply=args.apply)


if __name__ == "__main__":
    main()
