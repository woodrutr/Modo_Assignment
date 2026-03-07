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
                    "best_fit_lens": "Training 8h",
                    "training_24x7_4h_rank": 1,
                    "training_24x7_4h_score": 92.0,
                    "training_24x7_4h_annual_cost_reduction_pct": 11.4,
                    "training_24x7_4h_effective_avg_price_usd_per_mwh": 18.2,
                    "training_24x7_8h_score": 96.0,
                    "training_24x7_8h_annual_cost_reduction_pct": 15.1,
                },
                {
                    "location": "LZ_WEST",
                    "location_type": "Load Zone",
                    "best_fit_lens": "Inference 8h",
                    "training_24x7_4h_rank": 2,
                    "training_24x7_4h_score": 55.0,
                    "training_24x7_4h_annual_cost_reduction_pct": 4.0,
                    "training_24x7_4h_effective_avg_price_usd_per_mwh": 32.1,
                    "training_24x7_8h_score": 51.0,
                    "training_24x7_8h_annual_cost_reduction_pct": 3.4,
                },
            ]
        )

    def test_build_location_map_frame_attaches_active_lens_fields(self) -> None:
        frame = build_location_map_frame(self.metrics, "training_24x7", 4)
        self.assertEqual(frame["location"].tolist(), ["HB_PAN", "LZ_WEST"])
        self.assertIn("map_score", frame.columns)
        self.assertIn("marker_size", frame.columns)
        self.assertGreater(frame.loc[0, "marker_size"], frame.loc[1, "marker_size"])

    def test_build_texas_location_map_has_valid_selected_marker(self) -> None:
        frame = build_location_map_frame(self.metrics, "training_24x7", 4)
        figure = build_texas_location_map(frame, "HB_PAN", "24/7 Training", "4h")
        self.assertEqual(len(figure.data), 2)
        marker_trace = figure.data[1]
        self.assertEqual(marker_trace.selected.marker.color, "#7f4f3f")
        self.assertEqual(marker_trace.selected.marker.size, 28)

    def test_extract_selected_location_resolves_point_index(self) -> None:
        frame = build_location_map_frame(self.metrics, "training_24x7", 4)
        selection_event = {"selection": {"points": [{"pointNumber": 1}]}}
        selected_location = extract_selected_location(selection_event, frame, "HB_PAN")
        self.assertEqual(selected_location, "LZ_WEST")


if __name__ == "__main__":
    unittest.main()
