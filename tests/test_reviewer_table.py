from __future__ import annotations

import unittest

import pandas as pd

from src.presentation.reviewer_table import build_selected_metric_table


class ReviewerTableTests(unittest.TestCase):
    def test_selected_metric_table_includes_battery_fields(self) -> None:
        metrics_row = pd.Series(
            {
                "location": "HB_PAN",
                "location_type": "Trading Hub",
                "rank": 1,
                "observations": 8760,
                "avg_price": 25.4442,
                "std_price": 30.8316,
                "pct_negative": 11.5868,
                "pct_below_20": 43.4589,
                "pct_above_100": 1.7808,
                "avg_daily_spread": 67.0453,
                "battery_opportunity_score": 64.0152,
            }
        )
        battery_row = pd.Series(
            {
                "annual_battery_gross_margin_usd": 5902408.65,
                "average_daily_battery_value_usd": 16170.98,
                "positive_value_days": 365,
                "days_modeled": 365,
                "pct_positive_value_days": 100.0,
            }
        )

        result = build_selected_metric_table(metrics_row, battery_row)

        self.assertEqual(result.iloc[0]["Metric"], "Location Code")
        self.assertEqual(result.iloc[0]["Value"], "HB_PAN")
        self.assertIn("Annual Battery Gross Margin ($)", result["Metric"].tolist())
        self.assertIn("$5,902,408.65", result["Value"].tolist())
        self.assertIn("100.00%", result["Value"].tolist())


if __name__ == "__main__":
    unittest.main()
