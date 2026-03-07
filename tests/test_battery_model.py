from __future__ import annotations

import unittest

import pandas as pd

from src.analytics.battery_model import (
    build_daily_profile_windows,
    derive_local_time_features,
)
from tests.fixtures import make_processed_frame


class BatteryModelTests(unittest.TestCase):
    def test_dst_local_hour_derivation_preserves_timezone_truth(self) -> None:
        frame = pd.DataFrame(
            {
                "timestamp_utc": pd.date_range("2025-03-09 06:00:00+00:00", periods=5, freq="h"),
                "interval_start_utc": pd.date_range("2025-03-09 06:00:00+00:00", periods=5, freq="h"),
                "interval_end_utc": pd.date_range("2025-03-09 07:00:00+00:00", periods=5, freq="h"),
                "market_date": [pd.Timestamp("2025-03-09").date()] * 5,
                "location": pd.Series(["HB_PAN"] * 5, dtype="string"),
                "location_type": pd.Series(["Trading Hub"] * 5, dtype="string"),
                "market": pd.Series(["DAY_AHEAD_HOURLY"] * 5, dtype="string"),
                "spp": [10.0, 12.0, 14.0, 16.0, 18.0],
            }
        )
        local = derive_local_time_features(frame)
        self.assertEqual(local["local_hour"].tolist(), [0, 1, 3, 4, 5])

    def test_inference_profile_is_idle_on_weekends(self) -> None:
        processed = make_processed_frame(
            {"HB_PAN": [20.0] * 48},
            start_local="2025-01-03 00:00",
        )
        daily = build_daily_profile_windows(processed)
        weekend = daily.loc[
            daily["profile"].eq("inference_weekday_9_17") & daily["is_weekday"].eq(False)
        ].iloc[0]
        self.assertEqual(weekend["active_hours_count"], 0)
        self.assertFalse(bool(weekend["4h_profitable"]))
        self.assertEqual(float(weekend["baseline_daily_cost_usd_per_mw_day"]), 0.0)

    def test_non_positive_spread_keeps_battery_idle(self) -> None:
        prices = ([30.0] * 9) + ([10.0] * 8) + ([30.0] * 7)
        processed = make_processed_frame({"HB_PAN": prices})
        daily = build_daily_profile_windows(processed)
        day = daily.loc[daily["profile"].eq("inference_weekday_9_17")].iloc[0]
        self.assertFalse(bool(day["4h_profitable"]))
        self.assertEqual(float(day["4h_net_value_usd_per_mw_day"]), 0.0)
        self.assertEqual(
            float(day["4h_effective_daily_cost_usd_per_mw_day"]),
            float(day["baseline_daily_cost_usd_per_mw_day"]),
        )

    def test_four_and_eight_hour_windows_diverge_on_synthetic_shape(self) -> None:
        prices = ([5.0] * 8) + ([50.0] * 8) + ([12.0] * 8)
        processed = make_processed_frame({"HB_PAN": prices})
        daily = build_daily_profile_windows(processed)
        day = daily.loc[daily["profile"].eq("training_24x7")].iloc[0]
        self.assertGreater(float(day["8h_net_value_usd_per_mw_day"]), float(day["4h_net_value_usd_per_mw_day"]))
        self.assertLess(int(day["4h_charge_start_hour"]), int(day["4h_discharge_start_hour"]))


if __name__ == "__main__":
    unittest.main()
