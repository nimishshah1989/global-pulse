"""Opportunity Scanner — generates trading signals from RS data.

Scans for quadrant entries, volume breakouts, multi-level alignments,
divergences, extension alerts, and regime changes. Each signal includes
a conviction score (0-100) and plain-English description.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


class OpportunityScanner:
    """Generates actionable opportunity signals from RS score data.

    All conviction scores are Decimal in [0, 100]. Higher = stronger signal.
    """

    def scan_quadrant_entries(
        self,
        current_scores: list[dict[str, Any]],
        previous_scores: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect instruments that just entered LEADING or IMPROVING quadrant.

        Compare current vs previous day quadrant. If changed to LEADING or
        IMPROVING, emit a signal.

        Args:
            current_scores: Today's RS score dicts with instrument_id, quadrant,
                adjusted_rs_score, rs_momentum.
            previous_scores: Previous day's RS score dicts with same keys.

        Returns:
            List of signal dicts with instrument_id, signal_type,
            conviction_score, description, metadata.
        """
        prev_map: dict[str, str] = {
            s["instrument_id"]: s["quadrant"] for s in previous_scores
        }
        signals: list[dict[str, Any]] = []

        for score in current_scores:
            iid = score["instrument_id"]
            current_q = score["quadrant"]
            previous_q = prev_map.get(iid)

            if previous_q is None or previous_q == current_q:
                continue

            if current_q == "LEADING":
                rs = Decimal(str(score["adjusted_rs_score"]))
                conviction = min(rs, Decimal("100"))
                signals.append({
                    "instrument_id": iid,
                    "signal_type": "quadrant_entry_leading",
                    "conviction_score": conviction.quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    ),
                    "description": (
                        f"{iid} entered LEADING quadrant "
                        f"(from {previous_q})"
                    ),
                    "metadata": {
                        "previous_quadrant": previous_q,
                        "current_quadrant": current_q,
                        "adjusted_rs_score": str(score["adjusted_rs_score"]),
                        "rs_momentum": str(score["rs_momentum"]),
                    },
                })
            elif current_q == "IMPROVING":
                rs = Decimal(str(score["adjusted_rs_score"]))
                conviction = min(rs * Decimal("0.8"), Decimal("100"))
                signals.append({
                    "instrument_id": iid,
                    "signal_type": "quadrant_entry_improving",
                    "conviction_score": conviction.quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    ),
                    "description": (
                        f"{iid} entered IMPROVING quadrant "
                        f"(from {previous_q})"
                    ),
                    "metadata": {
                        "previous_quadrant": previous_q,
                        "current_quadrant": current_q,
                        "adjusted_rs_score": str(score["adjusted_rs_score"]),
                        "rs_momentum": str(score["rs_momentum"]),
                    },
                })

        return signals

    def scan_volume_breakouts(
        self, scores: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect RS turning positive with volume confirmation.

        Conditions: rs_momentum > 0 AND volume_ratio > 1.5.
        High conviction signal.

        Args:
            scores: RS score dicts with instrument_id, rs_momentum,
                volume_ratio, adjusted_rs_score.

        Returns:
            List of signal dicts.
        """
        signals: list[dict[str, Any]] = []

        for score in scores:
            momentum = Decimal(str(score["rs_momentum"]))
            volume_ratio = Decimal(str(score["volume_ratio"]))

            if momentum > Decimal("0") and volume_ratio > Decimal("1.5"):
                rs = Decimal(str(score["adjusted_rs_score"]))
                conviction = min(
                    rs * (volume_ratio / Decimal("2")), Decimal("100")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                signals.append({
                    "instrument_id": score["instrument_id"],
                    "signal_type": "volume_breakout",
                    "conviction_score": conviction,
                    "description": (
                        f"{score['instrument_id']} RS turning positive "
                        f"with volume {volume_ratio}x average"
                    ),
                    "metadata": {
                        "rs_momentum": str(momentum),
                        "volume_ratio": str(volume_ratio),
                        "adjusted_rs_score": str(rs),
                    },
                })

        return signals

    def scan_multi_level_alignments(
        self,
        country_scores: list[dict[str, Any]],
        sector_scores: list[dict[str, Any]],
        stock_scores: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect country + sector + stock all in LEADING quadrant.

        Highest conviction output. All three hierarchy levels must be LEADING.
        Conviction = min(country_score, sector_score, stock_score) — weakest link.

        Args:
            country_scores: Level 1 RS scores with instrument_id, quadrant,
                adjusted_rs_score, country, name.
            sector_scores: Level 2 RS scores with same keys plus sector.
            stock_scores: Level 3 RS scores with same keys plus sector, country.

        Returns:
            List of signal dicts with full alignment chain in metadata.
        """
        leading_countries = {
            s["country"]: s
            for s in country_scores
            if s.get("quadrant") == "LEADING" and s.get("country")
        }

        leading_sectors: dict[str, list[dict[str, Any]]] = {}
        for s in sector_scores:
            if s.get("quadrant") == "LEADING" and s.get("country"):
                leading_sectors.setdefault(s["country"], []).append(s)

        signals: list[dict[str, Any]] = []

        for stock in stock_scores:
            if stock.get("quadrant") != "LEADING":
                continue

            country_code = stock.get("country")
            sector = stock.get("sector")

            if country_code not in leading_countries:
                continue

            country_sectors = leading_sectors.get(country_code, [])
            matching_sector = next(
                (s for s in country_sectors if s.get("sector") == sector),
                None,
            )
            if matching_sector is None:
                continue

            country_data = leading_countries[country_code]
            country_rs = Decimal(str(country_data["adjusted_rs_score"]))
            sector_rs = Decimal(str(matching_sector["adjusted_rs_score"]))
            stock_rs = Decimal(str(stock["adjusted_rs_score"]))
            conviction = min(country_rs, sector_rs, stock_rs).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            country_name = country_data.get("name", country_code)
            sector_name = matching_sector.get("name", sector or "")
            stock_name = stock.get("name", stock["instrument_id"])

            signals.append({
                "instrument_id": stock["instrument_id"],
                "signal_type": "multi_level_alignment",
                "conviction_score": conviction,
                "description": (
                    f"{country_name} LEADING globally -> "
                    f"{sector_name} LEADING in {country_name} -> "
                    f"{stock_name} LEADING in {sector_name}"
                ),
                "metadata": {
                    "country_id": country_data["instrument_id"],
                    "country_name": country_name,
                    "country_quadrant": "LEADING",
                    "sector_id": matching_sector["instrument_id"],
                    "sector_name": sector_name,
                    "sector_quadrant": "LEADING",
                    "stock_id": stock["instrument_id"],
                    "stock_name": stock_name,
                    "stock_quadrant": "LEADING",
                },
            })

        return signals

    def scan_divergences(
        self,
        prices: dict[str, list[dict[str, Any]]],
        rs_scores: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Detect bearish and bullish divergences in 60-day windows.

        Bearish: price makes new high but RS makes lower high.
        Bullish: price makes new low but RS makes higher low.

        Args:
            prices: Dict mapping instrument_id to list of {date, close}.
            rs_scores: Dict mapping instrument_id to list of {date, rs_line}.

        Returns:
            List of divergence signal dicts.
        """
        signals: list[dict[str, Any]] = []
        window = 60

        for iid, price_list in prices.items():
            if iid not in rs_scores:
                continue

            rs_list = rs_scores[iid]
            if len(price_list) < window or len(rs_list) < window:
                continue

            recent_prices = [
                Decimal(str(p["close"])) for p in price_list[-window:]
            ]
            recent_rs = [
                Decimal(str(r["rs_line"])) for r in rs_list[-window:]
            ]

            half = window // 2
            first_half_prices = recent_prices[:half]
            second_half_prices = recent_prices[half:]
            first_half_rs = recent_rs[:half]
            second_half_rs = recent_rs[half:]

            price_high_1 = max(first_half_prices)
            price_high_2 = max(second_half_prices)
            rs_high_1 = max(first_half_rs)
            rs_high_2 = max(second_half_rs)

            if price_high_2 > price_high_1 and rs_high_2 < rs_high_1:
                signals.append({
                    "instrument_id": iid,
                    "signal_type": "bearish_divergence",
                    "conviction_score": Decimal("60.00"),
                    "description": (
                        f"{iid} bearish divergence: price new high "
                        f"but RS lower high"
                    ),
                    "metadata": {
                        "price_high_first": str(price_high_1),
                        "price_high_second": str(price_high_2),
                        "rs_high_first": str(rs_high_1),
                        "rs_high_second": str(rs_high_2),
                    },
                })

            price_low_1 = min(first_half_prices)
            price_low_2 = min(second_half_prices)
            rs_low_1 = min(first_half_rs)
            rs_low_2 = min(second_half_rs)

            if price_low_2 < price_low_1 and rs_low_2 > rs_low_1:
                signals.append({
                    "instrument_id": iid,
                    "signal_type": "bullish_divergence",
                    "conviction_score": Decimal("60.00"),
                    "description": (
                        f"{iid} bullish divergence: price new low "
                        f"but RS higher low"
                    ),
                    "metadata": {
                        "price_low_first": str(price_low_1),
                        "price_low_second": str(price_low_2),
                        "rs_low_first": str(rs_low_1),
                        "rs_low_second": str(rs_low_2),
                    },
                })

        return signals

    def scan_extension_alerts(
        self, scores: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Flag instruments with extension_warning = True.

        Args:
            scores: RS score dicts with instrument_id, extension_warning,
                rs_pct_3m, rs_pct_6m, rs_pct_12m.

        Returns:
            List of extension alert signal dicts.
        """
        signals: list[dict[str, Any]] = []

        for score in scores:
            if not score.get("extension_warning", False):
                continue

            rs = Decimal(str(score.get("adjusted_rs_score", "50")))
            signals.append({
                "instrument_id": score["instrument_id"],
                "signal_type": "extension_alert",
                "conviction_score": min(rs, Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "description": (
                    f"{score['instrument_id']} extended — RS in top 5% "
                    f"across all timeframes"
                ),
                "metadata": {
                    "rs_pct_3m": str(score.get("rs_pct_3m", "")),
                    "rs_pct_6m": str(score.get("rs_pct_6m", "")),
                    "rs_pct_12m": str(score.get("rs_pct_12m", "")),
                },
            })

        return signals

    def scan_regime_changes(
        self, current_regime: str, previous_regime: str
    ) -> list[dict[str, Any]]:
        """Detect ACWI regime change (crossed above/below 200-day MA).

        Args:
            current_regime: Current regime ('RISK_ON' or 'RISK_OFF').
            previous_regime: Previous regime.

        Returns:
            List with one signal if regime changed, empty otherwise.
        """
        if current_regime == previous_regime:
            return []

        if current_regime == "RISK_OFF":
            return [{
                "instrument_id": "ACWI",
                "signal_type": "regime_change",
                "conviction_score": Decimal("95.00"),
                "description": (
                    "Global regime changed to RISK_OFF — ACWI crossed "
                    "below 200-day MA"
                ),
                "metadata": {
                    "previous_regime": previous_regime,
                    "current_regime": current_regime,
                },
            }]
        else:
            return [{
                "instrument_id": "ACWI",
                "signal_type": "regime_change",
                "conviction_score": Decimal("90.00"),
                "description": (
                    "Global regime changed to RISK_ON — ACWI crossed "
                    "above 200-day MA"
                ),
                "metadata": {
                    "previous_regime": previous_regime,
                    "current_regime": current_regime,
                },
            }]

    def run_full_scan(
        self,
        current_scores: list[dict[str, Any]],
        previous_scores: list[dict[str, Any]],
        country_scores: list[dict[str, Any]],
        sector_scores: list[dict[str, Any]],
        stock_scores: list[dict[str, Any]],
        prices: dict[str, list[dict[str, Any]]],
        rs_lines: dict[str, list[dict[str, Any]]],
        current_regime: str = "RISK_ON",
        previous_regime: str = "RISK_ON",
    ) -> list[dict[str, Any]]:
        """Run all signal scanners and return combined results.

        Args:
            current_scores: Today's RS scores for all instruments.
            previous_scores: Previous day's RS scores.
            country_scores: Level 1 country scores.
            sector_scores: Level 2 sector scores.
            stock_scores: Level 3 stock scores.
            prices: Price histories keyed by instrument_id.
            rs_lines: RS line histories keyed by instrument_id.
            current_regime: Current global regime.
            previous_regime: Previous global regime.

        Returns:
            Combined list of all signals, sorted by conviction_score desc.
        """
        all_signals: list[dict[str, Any]] = []

        all_signals.extend(
            self.scan_quadrant_entries(current_scores, previous_scores)
        )
        all_signals.extend(self.scan_volume_breakouts(current_scores))
        all_signals.extend(
            self.scan_multi_level_alignments(
                country_scores, sector_scores, stock_scores
            )
        )
        all_signals.extend(self.scan_divergences(prices, rs_lines))
        all_signals.extend(self.scan_extension_alerts(current_scores))
        all_signals.extend(
            self.scan_regime_changes(current_regime, previous_regime)
        )

        all_signals.sort(
            key=lambda s: s["conviction_score"], reverse=True
        )

        return all_signals
