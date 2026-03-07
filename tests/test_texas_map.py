from __future__ import annotations

import unittest

import pandas as pd

from src.presentation.texas_map import (
    build_location_map_frame,
    build_texas_location_map,
    extract_selected_location,
)


class TexasMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = pd.DataFrame(
            [
                {
                    "location": "HB_PAN",
                    "location_type": "Trading Hub",
                    "avg_daily_spread": 67.0,
                    "battery_opportunity_score": 64.0,
                    "rank": 1,
                },
                {
                    "location": "LZ_WEST",
                    "location_type": "Load Zone",
                    "avg_daily_spread": 60.0,
                    "battery_opportunity_score": 58.0,
                    "rank": 2,
                },
            ]
        )
        self.battery = pd.DataFrame(
            [
                {
                    "location": "HB_PAN",
                    "annual_battery_gross_margin_usd": 5902408.65,
                    "pct_positive_value_days": 100.0,
                },
                {
                    "location": "LZ_WEST",
                    "annual_battery_gross_margin_usd": 7676928.55,
                    "pct_positive_value_days": 100.0,
                },
            ]
        )

    def test_build_location_map_frame_attaches_anchor_metadata(self) -> None:
        frame = build_location_map_frame(self.metrics, self.battery)

        self.assertEqual(frame["location"].tolist(), ["HB_PAN", "LZ_WEST"])
        self.assertIn("lat", frame.columns)
        self.assertIn("marker_size", frame.columns)
        self.assertGreater(frame.loc[0, "marker_size"], 14.0)

    def test_build_texas_location_map_has_outline_and_markers(self) -> None:
        frame = build_location_map_frame(self.metrics, self.battery)
        figure = build_texas_location_map(frame, "HB_PAN")

        self.assertEqual(len(figure.data), 2, "Expected 2 traces: outline + markers")

        outline_trace = figure.data[0]
        self.assertEqual(outline_trace.mode, "lines")
        self.assertIsNotNone(outline_trace.fill)

        marker_trace = figure.data[1]
        self.assertEqual(marker_trace.selected.marker.color, "#7f4f3f")
        self.assertEqual(marker_trace.selected.marker.size, 28)

    def test_extract_selected_location_resolves_point_index(self) -> None:
        frame = build_location_map_frame(self.metrics, self.battery)
        selection_event = {"selection": {"points": [{"pointNumber": 1}]}}

        selected_location = extract_selected_location(
            selection_event=selection_event,
            map_frame=frame,
            fallback_location="HB_PAN",
        )

        self.assertEqual(selected_location, "LZ_WEST")


if __name__ == "__main__":
    unittest.main()
