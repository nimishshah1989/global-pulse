"""Basket Engine — NAV computation and performance metrics.

Computes daily NAV normalized to 100 at inception, performance statistics
(cumulative return, CAGR, max drawdown, Sharpe, outperformance rate),
and per-position contribution analysis. All financial values use Decimal.
"""

import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


# Risk-free rate for Sharpe ratio (annualized, 4%)
RISK_FREE_RATE: Decimal = Decimal("0.04")

# Trading days per year for annualization
TRADING_DAYS_PER_YEAR: int = 252

# Trading days per week
TRADING_DAYS_PER_WEEK: int = 5


class BasketEngine:
    """Computes basket NAV, performance metrics, and position contributions."""

    def compute_nav(
        self,
        positions: list[dict[str, Any]],
        prices_by_instrument: dict[str, list[dict[str, Any]]],
        start_date: date,
        benchmark_prices: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Compute daily NAV normalized to 100 at start_date.

        For each day:
        1. Sum weighted returns: sum(weight_i * return_i)
        2. NAV[t] = NAV[t-1] * (1 + daily_return)

        Args:
            positions: List of {instrument_id, weight} dicts.
            prices_by_instrument: Dict mapping instrument_id to list of
                {date, close} sorted by date.
            start_date: Date to start NAV computation (NAV = 100).
            benchmark_prices: Optional list of {date, close} for benchmark.

        Returns:
            List of {date, nav, benchmark_nav, rs_line} dicts, all Decimal.
        """
        if not positions:
            return []

        all_dates: set[date] = set()
        price_maps: dict[str, dict[date, Decimal]] = {}

        for pos in positions:
            iid = pos["instrument_id"]
            prices = prices_by_instrument.get(iid, [])
            pmap: dict[date, Decimal] = {}
            for p in prices:
                d = p["date"] if isinstance(p["date"], date) else p["date"]
                pmap[d] = Decimal(str(p["close"]))
            price_maps[iid] = pmap
            all_dates.update(pmap.keys())

        sorted_dates = sorted(d for d in all_dates if d >= start_date)
        if not sorted_dates:
            return []

        bench_map: dict[date, Decimal] = {}
        if benchmark_prices:
            for p in benchmark_prices:
                d = p["date"] if isinstance(p["date"], date) else p["date"]
                bench_map[d] = Decimal(str(p["close"]))

        nav = Decimal("100")
        bench_nav = Decimal("100") if bench_map else None
        prev_prices: dict[str, Decimal] = {}
        prev_bench: Decimal | None = None
        results: list[dict[str, Any]] = []

        for i, d in enumerate(sorted_dates):
            if i == 0:
                for pos in positions:
                    iid = pos["instrument_id"]
                    if d in price_maps.get(iid, {}):
                        prev_prices[iid] = price_maps[iid][d]
                if bench_map and d in bench_map:
                    prev_bench = bench_map[d]

                rs_line: Decimal | None = None
                if bench_nav is not None:
                    rs_line = (nav / bench_nav * Decimal("100")).quantize(
                        Decimal("0.0001"), rounding=ROUND_HALF_UP
                    )

                results.append({
                    "date": d,
                    "nav": Decimal("100"),
                    "benchmark_nav": Decimal("100") if bench_nav is not None else None,
                    "rs_line": rs_line,
                })
                continue

            daily_return = Decimal("0")
            total_weight = Decimal("0")

            for pos in positions:
                iid = pos["instrument_id"]
                weight = Decimal(str(pos["weight"]))
                pmap = price_maps.get(iid, {})

                if d not in pmap or iid not in prev_prices:
                    continue

                current_price = pmap[d]
                prev_price = prev_prices[iid]

                if prev_price != Decimal("0"):
                    ret = (current_price - prev_price) / prev_price
                    daily_return += weight * ret
                    total_weight += weight

                prev_prices[iid] = current_price

            nav = nav * (Decimal("1") + daily_return)
            nav = nav.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

            if bench_map and d in bench_map:
                current_bench = bench_map[d]
                if prev_bench is not None and prev_bench != Decimal("0"):
                    bench_ret = (current_bench - prev_bench) / prev_bench
                    bench_nav = bench_nav * (Decimal("1") + bench_ret)
                    bench_nav = bench_nav.quantize(
                        Decimal("0.000001"), rounding=ROUND_HALF_UP
                    )
                prev_bench = current_bench

            rs_line = None
            if bench_nav is not None and bench_nav != Decimal("0"):
                rs_line = (nav / bench_nav * Decimal("100")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )

            results.append({
                "date": d,
                "nav": nav,
                "benchmark_nav": bench_nav,
                "rs_line": rs_line,
            })

        return results

    def compute_performance(
        self, nav_history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Compute performance metrics from NAV history.

        Metrics:
        - cumulative_return: (final_nav / 100) - 1
        - cagr: annualized return (if > 1 year of data)
        - max_drawdown: max peak-to-trough decline
        - sharpe_ratio: (annualized_return - 0.04) / annualized_vol
        - pct_weeks_outperforming: % of weeks where basket > benchmark

        Args:
            nav_history: List of {date, nav, benchmark_nav, rs_line} dicts.

        Returns:
            Dict with all metrics as Decimal values.
        """
        if not nav_history:
            return {
                "cumulative_return": Decimal("0"),
                "cagr": None,
                "max_drawdown": Decimal("0"),
                "sharpe_ratio": None,
                "pct_weeks_outperforming": None,
            }

        navs = [Decimal(str(h["nav"])) for h in nav_history]
        final_nav = navs[-1]
        initial_nav = Decimal("100")

        cumulative_return = (final_nav / initial_nav - Decimal("1")).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )

        num_days = len(navs)
        cagr: Decimal | None = None
        if num_days > TRADING_DAYS_PER_YEAR and final_nav > Decimal("0"):
            years = Decimal(str(num_days)) / Decimal(str(TRADING_DAYS_PER_YEAR))
            ratio = float(final_nav / initial_nav)
            exp = 1.0 / float(years)
            cagr_float = ratio ** exp - 1.0
            cagr = Decimal(str(cagr_float)).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            )

        peak = Decimal("0")
        max_dd = Decimal("0")
        for n in navs:
            if n > peak:
                peak = n
            if peak > Decimal("0"):
                dd = (peak - n) / peak
                if dd > max_dd:
                    max_dd = dd
        max_drawdown = max_dd.quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )

        sharpe: Decimal | None = None
        if num_days > 1:
            daily_returns: list[float] = []
            for i in range(1, len(navs)):
                if navs[i - 1] != Decimal("0"):
                    dr = float((navs[i] - navs[i - 1]) / navs[i - 1])
                    daily_returns.append(dr)

            if daily_returns:
                mean_dr = sum(daily_returns) / len(daily_returns)
                annualized_return = mean_dr * TRADING_DAYS_PER_YEAR
                variance = sum(
                    (r - mean_dr) ** 2 for r in daily_returns
                ) / len(daily_returns)
                annualized_vol = math.sqrt(variance * TRADING_DAYS_PER_YEAR)

                if annualized_vol > 0:
                    sharpe_val = (
                        annualized_return - float(RISK_FREE_RATE)
                    ) / annualized_vol
                    sharpe = Decimal(str(sharpe_val)).quantize(
                        Decimal("0.0001"), rounding=ROUND_HALF_UP
                    )

        pct_weeks: Decimal | None = None
        bench_navs = [h.get("benchmark_nav") for h in nav_history]
        if all(b is not None for b in bench_navs) and num_days > TRADING_DAYS_PER_WEEK:
            weeks_total = 0
            weeks_outperforming = 0
            for w_start in range(
                0, num_days - TRADING_DAYS_PER_WEEK, TRADING_DAYS_PER_WEEK
            ):
                w_end = min(w_start + TRADING_DAYS_PER_WEEK, num_days - 1)
                if w_end <= w_start:
                    continue

                nav_ret = (navs[w_end] - navs[w_start]) / navs[w_start]
                b_start = Decimal(str(bench_navs[w_start]))
                b_end = Decimal(str(bench_navs[w_end]))
                if b_start != Decimal("0"):
                    bench_ret = (b_end - b_start) / b_start
                    weeks_total += 1
                    if nav_ret > bench_ret:
                        weeks_outperforming += 1

            if weeks_total > 0:
                pct_weeks = (
                    Decimal(str(weeks_outperforming))
                    / Decimal(str(weeks_total))
                    * Decimal("100")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "cumulative_return": cumulative_return,
            "cagr": cagr,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "pct_weeks_outperforming": pct_weeks,
        }

    def compute_contributions(
        self,
        positions: list[dict[str, Any]],
        prices: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Compute which positions contributed to or dragged basket performance.

        Args:
            positions: List of {instrument_id, name, weight} dicts.
            prices: Dict mapping instrument_id to list of {date, close}.

        Returns:
            Sorted list of {instrument_id, name, weight, return, contribution}
            where contribution = weight * return.
        """
        results: list[dict[str, Any]] = []

        for pos in positions:
            iid = pos["instrument_id"]
            weight = Decimal(str(pos["weight"]))
            name = pos.get("name", iid)
            price_list = prices.get(iid, [])

            if len(price_list) < 2:
                results.append({
                    "instrument_id": iid,
                    "name": name,
                    "weight": weight,
                    "return": Decimal("0"),
                    "contribution": Decimal("0"),
                })
                continue

            first_close = Decimal(str(price_list[0]["close"]))
            last_close = Decimal(str(price_list[-1]["close"]))

            if first_close == Decimal("0"):
                ret = Decimal("0")
            else:
                ret = ((last_close - first_close) / first_close).quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_UP
                )

            contribution = (weight * ret).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            )

            results.append({
                "instrument_id": iid,
                "name": name,
                "weight": weight,
                "return": ret,
                "contribution": contribution,
            })

        results.sort(key=lambda x: x["contribution"], reverse=True)
        return results

    def rebalance_weights(
        self,
        positions: list[dict[str, Any]],
        method: str,
        rs_scores: dict[str, Decimal] | None = None,
    ) -> list[dict[str, Any]]:
        """Assign weights based on the selected method.

        Methods:
        - 'equal': 1/N for each position
        - 'manual': keep existing weights unchanged
        - 'rs_weighted': weight proportional to adjusted_rs_score

        Weights always sum to Decimal('1').

        Args:
            positions: List of {instrument_id, weight, ...} dicts.
            method: Weighting method string.
            rs_scores: Dict mapping instrument_id to Decimal RS score
                (required for 'rs_weighted' method).

        Returns:
            New list of position dicts with updated weights.
        """
        if not positions:
            return []

        n = len(positions)
        result = [dict(p) for p in positions]

        if method == "equal":
            equal_weight = (Decimal("1") / Decimal(str(n))).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            )
            remainder = Decimal("1") - equal_weight * Decimal(str(n))
            for i, pos in enumerate(result):
                pos["weight"] = equal_weight
            if remainder != Decimal("0"):
                result[0]["weight"] += remainder

        elif method == "manual":
            pass  # Keep existing weights

        elif method == "rs_weighted":
            if rs_scores is None:
                rs_scores = {}

            total_rs = Decimal("0")
            for pos in result:
                iid = pos["instrument_id"]
                score = rs_scores.get(iid, Decimal("50"))
                total_rs += score

            if total_rs == Decimal("0"):
                return self.rebalance_weights(positions, "equal")

            for pos in result:
                iid = pos["instrument_id"]
                score = rs_scores.get(iid, Decimal("50"))
                pos["weight"] = (score / total_rs).quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_UP
                )

            weight_sum = sum(p["weight"] for p in result)
            if weight_sum != Decimal("1"):
                diff = Decimal("1") - weight_sum
                result[0]["weight"] += diff

        return result
