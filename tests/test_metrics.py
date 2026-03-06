from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.analytics.metrics import compute_daily_spreads, compute_location_metrics
from src.config import AppSettings, BatteryAssumptions, MetricWeights


def _sample_frame() -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for market_date, alpha_prices, beta_prices in (
        (date(2025, 1, 1), [-10.0, 10.0, 25.0, 140.0], [5.0, 15.0, 20.0, 30.0]),
        (date(2025, 1, 2), [-5.0, 5.0, 15.0, 120.0], [0.0, 10.0, 15.0, 25.0]),
    ):
        for price in alpha_prices:
            records.append(
                {
                    "location": "ALPHA",
                    "location_type": "Trading Hub",
                    "market_date": market_date,
                    "spp": price,
                }
            )
        for price in beta_prices:
            records.append(
                {
                    "location": "BETA",
                    "location_type": "Load Zone",
                    "market_date": market_date,
                    "spp": price,
                }
            )
    return pd.DataFrame(records)


class MetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = _sample_frame()
        self.settings = AppSettings(
            metric_weights=MetricWeights(
                pct_negative=0.25,
                pct_below_20=0.25,
                avg_daily_spread=0.25,
                pct_above_100=0.25,
            ),
            battery=BatteryAssumptions(),
        )

    def test_daily_spreads_are_computed_per_market_day(self) -> None:
        daily_spreads = compute_daily_spreads(self.frame)
        alpha_day_one = daily_spreads.loc[
            (daily_spreads["location"] == "ALPHA")
            & (daily_spreads["market_date"] == date(2025, 1, 1)),
            "daily_spread",
        ].iloc[0]
        self.assertEqual(alpha_day_one, 150.0)

    def test_location_metrics_rank_higher_volatility_location_first(self) -> None:
        metrics = compute_location_metrics(self.frame, self.settings)
        self.assertEqual(metrics.loc[0, "location"], "ALPHA")
        self.assertGreater(
            metrics.loc[metrics["location"] == "ALPHA", "battery_opportunity_score"].iloc[0],
            metrics.loc[metrics["location"] == "BETA", "battery_opportunity_score"].iloc[0],
        )

    def test_threshold_percentages_are_expressed_as_percent(self) -> None:
        metrics = compute_location_metrics(self.frame, self.settings)
        alpha_row = metrics.loc[metrics["location"] == "ALPHA"].iloc[0]
        self.assertEqual(alpha_row["pct_negative"], 25.0)
        self.assertEqual(alpha_row["pct_above_100"], 25.0)


if __name__ == "__main__":
    unittest.main()
