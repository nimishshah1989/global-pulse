"""Portfolio Simulator — forward-walk engine for model portfolio construction.

Handles day-by-day simulation: rebalancing, stop-loss management, NAV tracking.
"""
from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from engine.portfolio_engine import (
    MAX_POSITIONS, REBALANCE_INTERVAL, VOL_LOOKBACK,
    compute_initial_stop, compute_weights, compute_win_rate,
    get_performance_metrics, select_positions, update_trailing_stop,
)
from repositories.ranking_repo import _compute_volume_signal, _derive_action_gate

_ZERO = Decimal("0")
_ONE = Decimal("1")
_QUANT = Decimal("0.000001")


def simulate_portfolio(
    trading_dates: list[datetime.date],
    inst_map: dict[str, dict[str, Any]],
    prices_by_id: dict[str, list[tuple[datetime.date, float]]],
    scores_by_id_date: dict[str, dict[datetime.date, dict[str, Any]]],
    bench_price_id: str,
    regime: str,
) -> dict[str, Any]:
    """Walk forward through trading dates, managing positions and NAV."""
    px: dict[str, dict[datetime.date, float]] = {
        iid: {d: c for d, c in pairs} for iid, pairs in prices_by_id.items()
    }
    close_lists: dict[str, list[float]] = {
        iid: [c for _, c in pairs] for iid, pairs in prices_by_id.items()
    }

    positions: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    nav_history: list[dict[str, float]] = []
    nav, bench_nav = Decimal("100"), Decimal("100")
    days_since_rebalance = REBALANCE_INTERVAL
    prev_px: dict[str, Decimal] = {}
    prev_bench: Decimal | None = None
    last_rebalance_date: datetime.date | None = None

    start_idx = max(VOL_LOOKBACK + 5, 0)
    if start_idx >= len(trading_dates):
        return _empty_response("etf_only", bench_price_id)
    sim_dates = trading_dates[start_idx:]

    for _i, d in enumerate(sim_dates):
        bench_close = px.get(bench_price_id, {}).get(d)

        if days_since_rebalance >= REBALANCE_INTERVAL:
            positions, new_trades, last_rebalance_date = _rebalance(
                d, positions, inst_map, scores_by_id_date, px, close_lists, regime,
            )
            trades.extend(new_trades)
            days_since_rebalance = 0

        positions, stop_trades = _update_stops_and_exit(d, positions, px)
        trades.extend(stop_trades)

        daily_return = _ZERO
        for pos in positions:
            iid = pos["instrument_id"]
            cur = Decimal(str(px.get(iid, {}).get(d, 0)))
            prev = prev_px.get(iid)
            if prev and prev != _ZERO and cur > _ZERO:
                daily_return += Decimal(str(pos["weight"])) * ((cur - prev) / prev)
            if cur > _ZERO:
                prev_px[iid] = cur

        nav = (nav * (_ONE + daily_return)).quantize(_QUANT, rounding=ROUND_HALF_UP)

        if bench_close is not None and bench_close > 0:
            bc = Decimal(str(bench_close))
            if prev_bench and prev_bench != _ZERO:
                bench_nav = (bench_nav * (_ONE + (bc - prev_bench) / prev_bench)).quantize(
                    _QUANT, rounding=ROUND_HALF_UP,
                )
            prev_bench = bc

        nav_history.append({"date": d, "nav": float(nav), "benchmark_nav": float(bench_nav)})
        days_since_rebalance += 1

    metrics = get_performance_metrics(nav_history)
    final_date = sim_dates[-1] if sim_dates else datetime.date.today()
    current_positions = _build_current_positions(
        positions, px, scores_by_id_date, final_date, regime,
    )
    total_w = sum(Decimal(str(p["weight"])) for p in current_positions)
    cash = float(_ONE - total_w) if total_w < _ONE else 0.0

    return {
        "summary": {
            "portfolio_type": "etf_only",
            "total_positions": len(current_positions),
            "cash_weight": round(cash, 4),
            "nav": float(nav), "benchmark_nav": float(bench_nav),
            "cumulative_return": metrics["cumulative_return"],
            "cagr": metrics["cagr"], "max_drawdown": metrics["max_drawdown"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "win_rate": compute_win_rate(trades),
            "last_rebalance": last_rebalance_date, "regime": regime,
        },
        "positions": current_positions,
        "nav_history": nav_history,
        "recent_trades": trades[-20:],
    }


def _pnl_pct(cur: Decimal, entry: Decimal) -> float:
    """Compute P&L percentage."""
    return float(cur - entry) / float(entry) * 100 if entry else 0.0


def _rebalance(
    d: datetime.date,
    positions: list[dict[str, Any]],
    inst_map: dict[str, dict[str, Any]],
    scores: dict[str, dict[datetime.date, dict[str, Any]]],
    px: dict[str, dict[datetime.date, float]],
    close_lists: dict[str, list[float]],
    regime: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], datetime.date]:
    """Execute a rebalance: exit stale, enter new, reweight."""
    rankings = _rank_on_date(d, inst_map, scores, px, regime)
    new_entries = select_positions(rankings, MAX_POSITIONS)
    new_ids = {e["instrument_id"] for e in new_entries}
    trades: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []

    for pos in positions:
        iid = pos["instrument_id"]
        cur_price = Decimal(str(px.get(iid, {}).get(d, 0)))
        if iid not in new_ids:
            trades.append({
                "date": d, "instrument_id": iid,
                "name": inst_map.get(iid, {}).get("name", iid),
                "action": "EXIT_REBALANCE", "price": float(cur_price),
                "reason": "No longer BUY-rated at rebalance",
                "pnl": _pnl_pct(cur_price, pos["entry_price"]),
            })
        else:
            kept.append(pos)

    held_ids = {p["instrument_id"] for p in kept}
    additions = [e for e in new_entries if e["instrument_id"] not in held_ids]
    combined = [p["instrument_id"] for p in kept] + [a["instrument_id"] for a in additions]
    weighted = compute_weights([{"instrument_id": i} for i in combined], close_lists)
    wmap = {w["instrument_id"]: w["weight"] for w in weighted}

    for pos in kept:
        pos["weight"] = wmap.get(pos["instrument_id"], pos["weight"])

    for add in additions:
        iid = add["instrument_id"]
        entry_px = Decimal(str(px.get(iid, {}).get(d, 0)))
        if entry_px <= _ZERO:
            continue
        atype = inst_map.get(iid, {}).get("asset_type", "etf")
        kept.append({
            "instrument_id": iid,
            "name": inst_map.get(iid, {}).get("name", iid),
            "country": inst_map.get(iid, {}).get("country"),
            "sector": inst_map.get(iid, {}).get("sector"),
            "asset_type": atype, "weight": wmap.get(iid, _ZERO),
            "entry_price": entry_px, "entry_date": d,
            "peak_price": entry_px, "stop_price": compute_initial_stop(entry_px, atype),
            "trailing_stop_active": False,
        })
        trades.append({
            "date": d, "instrument_id": iid,
            "name": inst_map.get(iid, {}).get("name", iid),
            "action": "ENTER", "price": float(entry_px),
            "reason": "BUY signal at rebalance", "pnl": 0.0,
        })
    return kept, trades, d


def _update_stops_and_exit(
    d: datetime.date,
    positions: list[dict[str, Any]],
    px: dict[str, dict[datetime.date, float]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Update trailing stops and exit stopped-out positions."""
    trades: list[dict[str, Any]] = []
    stopped: set[str] = set()
    for pos in positions:
        iid = pos["instrument_id"]
        cur = Decimal(str(px.get(iid, {}).get(d, 0)))
        if cur <= _ZERO:
            continue
        if cur > pos["peak_price"]:
            pos["peak_price"] = cur
        new_stop, trailing = update_trailing_stop(
            pos["entry_price"], pos["peak_price"], pos["stop_price"],
            pos.get("asset_type", "etf"),
        )
        pos["stop_price"] = new_stop
        pos["trailing_stop_active"] = trailing
        if cur <= pos["stop_price"]:
            stopped.add(iid)
            trades.append({
                "date": d, "instrument_id": iid, "name": pos["name"],
                "action": "EXIT_STOP", "price": float(cur),
                "reason": "Stop loss triggered" + (" (trailing)" if trailing else ""),
                "pnl": _pnl_pct(cur, pos["entry_price"]),
            })
    return [p for p in positions if p["instrument_id"] not in stopped], trades


def _rank_on_date(
    d: datetime.date,
    inst_map: dict[str, dict[str, Any]],
    scores: dict[str, dict[datetime.date, dict[str, Any]]],
    px: dict[str, dict[datetime.date, float]],
    regime: str,
) -> list[dict[str, Any]]:
    """Build ranking dicts for a specific date from RS scores + prices."""
    results: list[dict[str, Any]] = []
    for iid, info in inst_map.items():
        id_scores = scores.get(iid, {})
        sd = id_scores.get(d)
        if sd is None:
            for off in range(1, 6):
                ck = d - datetime.timedelta(days=off)
                if ck in id_scores:
                    sd = id_scores[ck]
                    break
        if sd is None:
            continue

        cur_close = px.get(iid, {}).get(d)
        if not cur_close or cur_close <= 0:
            continue

        abs_ret: float | None = None
        for lb in (63, 45, 21):
            base = d - datetime.timedelta(days=int(lb * 1.5))
            for off in range(10):
                cd = base + datetime.timedelta(days=off)
                if cd in px.get(iid, {}) and px[iid][cd] > 0:
                    abs_ret = (cur_close / px[iid][cd] - 1.0) * 100
                    break
            if abs_ret is not None:
                break

        vs = _compute_volume_signal(sd["volume_ratio"], (abs_ret or 0) > 0)
        action, reason = _derive_action_gate(
            abs_ret, sd["rs_score"], sd["rs_momentum"], vs, regime,
        )
        results.append({
            "instrument_id": iid, "name": info.get("name", iid),
            "country": info.get("country"), "sector": info.get("sector"),
            "asset_type": info.get("asset_type", "etf"),
            "rs_score": sd["rs_score"], "rs_momentum": sd["rs_momentum"],
            "action": action, "action_reason": reason,
        })
    return results


def _build_current_positions(
    positions: list[dict[str, Any]],
    px: dict[str, dict[datetime.date, float]],
    scores_by_id_date: dict[str, dict[datetime.date, dict[str, Any]]],
    final_date: datetime.date,
    regime: str,
) -> list[dict[str, Any]]:
    """Build current-position response dicts with latest action."""
    result: list[dict[str, Any]] = []
    for pos in positions:
        iid = pos["instrument_id"]
        cur = float(px.get(iid, {}).get(final_date, 0))
        entry = float(pos["entry_price"])
        pnl = ((cur / entry) - 1.0) * 100 if entry else 0.0
        latest = scores_by_id_date.get(iid, {}).get(final_date, {})
        action = "HOLD"
        if latest:
            vs = _compute_volume_signal(latest.get("volume_ratio", 1.0), pnl > 0)
            action, _ = _derive_action_gate(
                pnl, latest.get("rs_score", 50.0),
                latest.get("rs_momentum", 0.0), vs, regime,
            )
        result.append({
            "instrument_id": iid, "name": pos["name"],
            "country": pos.get("country"), "sector": pos.get("sector"),
            "weight": float(pos["weight"]), "entry_price": entry,
            "current_price": cur, "entry_date": pos["entry_date"],
            "pnl_pct": round(pnl, 2), "stop_price": float(pos["stop_price"]),
            "trailing_stop_active": pos.get("trailing_stop_active", False),
            "action": action,
        })
    return result


def _empty_response(portfolio_type: str, benchmark_id: str) -> dict[str, Any]:
    """Return valid but empty simulation response."""
    return {
        "summary": {
            "portfolio_type": portfolio_type, "total_positions": 0,
            "cash_weight": 1.0, "nav": 100.0, "benchmark_nav": 100.0,
            "cumulative_return": 0.0, "cagr": None, "max_drawdown": 0.0,
            "sharpe_ratio": None, "win_rate": None,
            "last_rebalance": None, "regime": "BULL",
        },
        "positions": [], "nav_history": [], "recent_trades": [],
    }
