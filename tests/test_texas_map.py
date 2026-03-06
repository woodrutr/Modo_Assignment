from __future__ import annotations

import unittest

import pandas as pd

from src.presentation.texas_map import (
    build_location_map_frame,
    extract_selected_location,
)


def _metrics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rank": [1, 2],
            "location": ["HB_HOUSTON", "LZ_CPS"],
            "location_type": ["Trading Hub", "Load Zone"],
            "battery_opportunity_score": [62.5, 38.2],
            "avg_price": [40.0, 35.0],
            "std_price": [22.0, 18.0],
            "pct_negative": [5.0, 1.5],
            "pct_below_20": [20.0, 17.0],
            "pct_above_100": [2.5, 3.0],
            "avg_daily_spread": [65.0, 72.0],
        }
    )


def _battery_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "location": ["HB_HOUSTON", "LZ_CPS"],
            "annual_battery_gross_margin_usd": [1_500_000.0, 2_100_000.0],
            "pct_positive_value_days": [88.0, 92.0],
        }
    )


class TexasMapTests(unittest.TestCase):
    def test_build_location_map_frame_joins_anchor_coordinates(self) -> None:
        map_frame = build_location_map_frame(_metrics_frame(), _battery_frame())
        self.assertEqual(len(map_frame), 2)
        self.assertTrue(map_frame["lat"].notna().all())
        self.assertTrue(map_frame["lon"].notna().all())

    def test_build_location_map_frame_raises_on_missing_anchor(self) -> None:
        metrics = _metrics_frame().copy()
        metrics.loc[0, "location"] = "UNKNOWN_LOCATION"
        with self.assertRaises(ValueError):
            build_location_map_frame(metrics, _battery_frame())

    def test_extract_selected_location_reads_point_index(self) -> None:
        map_frame = build_location_map_frame(_metrics_frame(), _battery_frame())
        selected = extract_selected_location(
            {"selection": {"points": [{"point_index": 1}]}},
            map_frame,
            fallback_location="HB_HOUSTON",
        )
        self.assertEqual(selected, "LZ_CPS")

    def test_extract_selected_location_falls_back_without_selection(self) -> None:
        map_frame = build_location_map_frame(_metrics_frame(), _battery_frame())
        selected = extract_selected_location({}, map_frame, fallback_location="HB_HOUSTON")
        self.assertEqual(selected, "HB_HOUSTON")


if __name__ == "__main__":
    unittest.main()
