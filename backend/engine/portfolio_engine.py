"""Portfolio Engine — position selection, sizing, stop-loss management, and NAV.

Reads BUY signals from the ranking system and constructs a model portfolio
with inverse-volatility weighting, trailing stops, and weekly rebalancing.
All financial precision uses Decimal; performance metrics use float for JSON.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

MAX_POSITIONS: int = 6
STOP_LOSS_ETF: Decimal = Decimal("0.08")   # 8% for sector ETFs
STOP_LOSS_STOCK: Decimal = Decimal("0.12")  # 12% for individual stocks
TRAILING_ACTIVATION: Decimal = Decimal("0.15")  # activate trail at +15%
TRAILING_FACTOR: Decimal = Decimal("0.5")   # trail at entry + (peak-entry)*0.5
REBALANCE_INTERVAL: int = 5                 # trading days between rebalances
RISK_FREE_RATE: float = 0.04               # for Sharpe
TRADING_DAYS_YEAR: int = 252
VOL_LOOKBACK: int = 20                      # days for annualised vol


# ---------------------------------------------------------------------------
# Position selection
# ---------------------------------------------------------------------------

def select_positions(
    rankings: list[dict[str, Any]],
    max_positions: int = MAX_POSITIONS,
) -> list[dict[str, Any]]:
    """Select top *max_positions* BUY-rated instruments sorted by RS score.

    Returns a trimmed list of ranking dicts that qualify for entry.
    """
    buys = [r for r in rankings if r.get("action") == "BUY"]
    buys.sort(key=lambda r: float(r.get("rs_score", 0)), reverse=True)
    return buys[:max_positions]


# ---------------------------------------------------------------------------
# Inverse-volatility weighting
# ---------------------------------------------------------------------------

def compute_weights(
    positions: list[dict[str, Any]],
    prices_map: dict[str, list[float]],
) -> list[dict[str, Any]]:
    """Assign weights using inverse annualised volatility.

    Args:
        positions: ranking dicts for selected instruments.
        prices_map: {instrument_id: [close_0, close_1, ...]} ordered by date.
            Must contain at least *VOL_LOOKBACK + 1* prices for a valid calc.

    Returns:
        Input list enriched with ``weight`` (Decimal, sums to 1).
    """
    vols: list[Decimal] = []
    valid_positions: list[dict[str, Any]] = []

    for pos in positions:
        iid = pos["instrument_id"]
        closes = prices_map.get(iid, [])
        vol = _annualised_vol(closes)
        if vol is not None and vol > Decimal("0"):
            vols.append(vol)
            valid_positions.append(pos)

    if not valid_positions:
        return []

    raw_weights = [Decimal("1") / v for v in vols]
    total = sum(raw_weights)

    for pos, rw in zip(valid_positions, raw_weights):
        pos["weight"] = (rw / total).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP,
        )

    # Fix rounding residual on the first position
    assigned = sum(p["weight"] for p in valid_positions)
    if assigned != Decimal("1"):
        valid_positions[0]["weight"] += Decimal("1") - assigned

    return valid_positions


def _annualised_vol(closes: list[float]) -> Decimal | None:
    """Annualised volatility from the last *VOL_LOOKBACK* daily returns."""
    if len(closes) < VOL_LOOKBACK + 1:
        return None

    recent = closes[-(VOL_LOOKBACK + 1):]
    returns: list[float] = []
    for i in range(1, len(recent)):
        if recent[i - 1] != 0:
            returns.append(recent[i] / recent[i - 1] - 1.0)

    if len(returns) < 2:
        return None

    mean_r = sum(returns) / len(returns)
    var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    annual_vol = math.sqrt(var * TRADING_DAYS_YEAR)
    return Decimal(str(round(annual_vol, 8)))


# ---------------------------------------------------------------------------
# Stop-loss logic
# ---------------------------------------------------------------------------

def compute_initial_stop(
    entry_price: Decimal,
    asset_type: str,
) -> Decimal:
    """Return the absolute stop-loss price for a new position."""
    pct = STOP_LOSS_STOCK if asset_type == "stock" else STOP_LOSS_ETF
    return (entry_price * (Decimal("1") - pct)).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP,
    )


def update_trailing_stop(
    entry_price: Decimal,
    peak_price: Decimal,
    current_stop: Decimal,
    asset_type: str,
) -> tuple[Decimal, bool]:
    """Update the trailing stop if the position qualifies.

    Returns (new_stop, trailing_active).
    """
    gain_pct = (peak_price - entry_price) / entry_price if entry_price else Decimal("0")

    if gain_pct < TRAILING_ACTIVATION:
        return current_stop, False

    # Trail at entry + (peak - entry) * factor
    trail_stop = entry_price + (peak_price - entry_price) * TRAILING_FACTOR
    trail_stop = trail_stop.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    # Never lower the stop
    new_stop = max(trail_stop, current_stop)
    return new_stop, True


def check_stops(
    positions: list[dict[str, Any]],
    current_prices: dict[str, float],
) -> list[dict[str, Any]]:
    """Return positions that should be exited because their stop was hit.

    Each position dict must contain:
        instrument_id, stop_price (Decimal), entry_price (Decimal),
        peak_price (Decimal), asset_type.
    """
    to_exit: list[dict[str, Any]] = []

    for pos in positions:
        iid = pos["instrument_id"]
        price = Decimal(str(current_prices.get(iid, 0)))
        stop = Decimal(str(pos["stop_price"]))

        if price > Decimal("0") and price <= stop:
            to_exit.append(pos)

    return to_exit


# ---------------------------------------------------------------------------
# NAV computation
# ---------------------------------------------------------------------------

def compute_portfolio_nav(
    daily_snapshots: list[dict[str, Any]],
) -> list[dict[str, float]]:
    """Compute NAV series from a list of daily position snapshots.

    Each snapshot: {date, positions: [{instrument_id, weight}], prices: {id: close}}.
    NAV starts at 100 on the first snapshot day.

    Returns [{date, nav}].
    """
    if not daily_snapshots:
        return []

    nav = Decimal("100")
    results: list[dict[str, float]] = []
    prev_prices: dict[str, Decimal] = {}

    for i, snap in enumerate(daily_snapshots):
        d = snap["date"]
        positions = snap.get("positions", [])
        prices = snap.get("prices", {})

        if i == 0:
            for pos in positions:
                iid = pos["instrument_id"]
                if iid in prices:
                    prev_prices[iid] = Decimal(str(prices[iid]))
            results.append({"date": d, "nav": float(nav)})
            continue

        daily_return = Decimal("0")
        for pos in positions:
            iid = pos["instrument_id"]
            w = Decimal(str(pos["weight"]))
            cur = Decimal(str(prices.get(iid, 0)))
            prev = prev_prices.get(iid)

            if prev and prev != Decimal("0") and cur > Decimal("0"):
                ret = (cur - prev) / prev
                daily_return += w * ret

            if cur > Decimal("0"):
                prev_prices[iid] = cur

        nav = nav * (Decimal("1") + daily_return)
        nav = nav.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        results.append({"date": d, "nav": float(nav)})

    return results


# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------

def get_performance_metrics(nav_history: list[dict[str, float]]) -> dict[str, Any]:
    """Compute cumulative return, CAGR, max drawdown, Sharpe ratio.

    Args:
        nav_history: [{date, nav}] with NAV starting at 100.

    Returns:
        Dict with cumulative_return, cagr, max_drawdown, sharpe_ratio (all float).
    """
    if not nav_history:
        return _empty_metrics()

    navs = [h["nav"] for h in nav_history]
    final = navs[-1]
    trading_days = len(navs)

    cumulative_return = round(final / 100.0 - 1.0, 6)

    cagr: float | None = None
    if trading_days > TRADING_DAYS_YEAR and final > 0:
        years = trading_days / TRADING_DAYS_YEAR
        cagr = round(((final / 100.0) ** (1.0 / years)) - 1.0, 6)

    # Max drawdown
    peak = 0.0
    max_dd = 0.0
    for n in navs:
        if n > peak:
            peak = n
        if peak > 0:
            dd = (peak - n) / peak
            if dd > max_dd:
                max_dd = dd
    max_drawdown = round(max_dd, 6)

    # Sharpe
    sharpe: float | None = None
    if trading_days > 1:
        daily_rets = []
        for j in range(1, len(navs)):
            if navs[j - 1] != 0:
                daily_rets.append(navs[j] / navs[j - 1] - 1.0)
        if daily_rets:
            mean_dr = sum(daily_rets) / len(daily_rets)
            ann_ret = mean_dr * TRADING_DAYS_YEAR
            var = sum((r - mean_dr) ** 2 for r in daily_rets) / len(daily_rets)
            ann_vol = math.sqrt(var * TRADING_DAYS_YEAR)
            if ann_vol > 0:
                sharpe = round((ann_ret - RISK_FREE_RATE) / ann_vol, 4)

    return {
        "cumulative_return": cumulative_return,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
    }


def compute_win_rate(closed_trades: list[dict[str, Any]]) -> float | None:
    """Percentage of closed positions that were profitable."""
    exits = [t for t in closed_trades if t.get("action", "").startswith("EXIT")]
    if not exits:
        return None
    winners = sum(1 for t in exits if t.get("pnl", 0) > 0)
    return round(winners / len(exits) * 100.0, 2)


def _empty_metrics() -> dict[str, Any]:
    return {
        "cumulative_return": 0.0,
        "cagr": None,
        "max_drawdown": 0.0,
        "sharpe_ratio": None,
    }
