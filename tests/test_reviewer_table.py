from __future__ import annotations

import unittest

import pandas as pd

from src.presentation.reviewer_table import (
    build_location_story,
    build_raw_metric_table,
    build_reviewer_table,
)


def _metrics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rank": [1, 2],
            "location": ["HB_PAN", "LZ_CPS"],
            "location_type": ["Trading Hub", "Load Zone"],
            "battery_opportunity_score": [64.0, 37.2],
            "avg_price": [25.4, 39.0],
            "std_price": [30.8, 33.5],
            "pct_negative": [11.5, 0.0],
            "pct_below_20": [43.4, 16.3],
            "pct_above_100": [1.7, 3.1],
            "avg_daily_spread": [67.0, 74.0],
        }
    )


def _battery_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "location": ["HB_PAN", "LZ_CPS"],
            "annual_battery_gross_margin_usd": [5_902_408.65, 6_505_066.85],
            "pct_positive_value_days": [100.0, 100.0],
        }
    )


class ReviewerTableTests(unittest.TestCase):
    def test_build_raw_metric_table_preserves_machine_columns(self) -> None:
        raw_table = build_raw_metric_table(_metrics_frame(), _battery_frame())
        self.assertIn("battery_opportunity_score", raw_table.columns)
        self.assertEqual(len(raw_table), 2)

    def test_build_reviewer_table_creates_friendly_columns(self) -> None:
        reviewer = build_reviewer_table(_metrics_frame(), _battery_frame())
        self.assertEqual(
            list(reviewer.columns),
            [
                "Rank",
                "Location",
                "Code",
                "Score",
                "Cheap Hours (%)",
                "Spike Hours (%)",
                "Daily Spread ($/MWh)",
                "Est. Battery Value ($/yr)",
                "Readout",
            ],
        )
        self.assertEqual(reviewer.loc[0, "Location"], "Amarillo Hub")

    def test_build_location_story_returns_human_summary(self) -> None:
        raw_table = build_raw_metric_table(_metrics_frame(), _battery_frame())
        story = build_location_story(raw_table.iloc[0])
        self.assertIn("strongest screening candidates", story)
        self.assertIn("$5,902,409", story)


if __name__ == "__main__":
    unittest.main()
