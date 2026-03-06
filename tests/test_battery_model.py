from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from src.analytics.battery_model import compute_daily_battery_value, summarize_battery_value
from src.config import AppSettings, BatteryAssumptions


def _battery_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "location": ["ALPHA"] * 4 + ["BETA"] * 4,
            "market_date": [date(2025, 1, 1)] * 8,
            "spp": [-20.0, 0.0, 100.0, 200.0, 10.0, 20.0, 30.0, 40.0],
        }
    )


class BatteryModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings(
            battery=BatteryAssumptions(
                charge_mwh_per_hour=1.0,
                charge_hours_per_day=2,
                discharge_hours_per_day=2,
                round_trip_efficiency=0.8,
            ),
        )

    def test_daily_battery_value_uses_cheapest_and_richest_windows(self) -> None:
        daily_value = compute_daily_battery_value(_battery_frame(), self.settings)
        alpha_net = daily_value.loc[daily_value["location"] == "ALPHA", "net_value_usd"].iloc[0]
        self.assertEqual(alpha_net, 260.0)

    def test_summary_reports_positive_day_share(self) -> None:
        summary = summarize_battery_value(_battery_frame(), self.settings)
        alpha_row = summary.loc[summary["location"] == "ALPHA"].iloc[0]
        self.assertEqual(alpha_row["positive_value_days"], 1)
        self.assertEqual(alpha_row["pct_positive_value_days"], 100.0)


if __name__ == "__main__":
    unittest.main()
