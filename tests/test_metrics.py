from __future__ import annotations

import unittest

from src.analytics.metrics import build_artifact_bundle
from tests.fixtures import make_processed_frame


class MetricsTests(unittest.TestCase):
    def test_artifact_bundle_generates_bounded_scores_and_best_fit(self) -> None:
        day_a = ([5.0] * 8) + ([60.0] * 8) + ([20.0] * 8)
        day_b = ([20.0] * 8) + ([28.0] * 8) + ([20.0] * 8)
        prices_a = day_a * 3
        prices_b = day_b * 3
        processed = make_processed_frame(
            {
                "HB_PAN": prices_a,
                "LZ_WEST": prices_b,
            }
        )
        bundle = build_artifact_bundle(processed)
        metrics = bundle.location_metrics

        for column in [
            "training_24x7_4h_score",
            "training_24x7_8h_score",
            "inference_weekday_9_17_4h_score",
            "inference_weekday_9_17_8h_score",
        ]:
            self.assertTrue(metrics[column].between(0.0, 100.0).all())

        hb_pan = metrics.loc[metrics["location"].eq("HB_PAN")].iloc[0]
        self.assertEqual(int(hb_pan["best_fit_rank"]), min(
            int(hb_pan["training_24x7_4h_rank"]),
            int(hb_pan["training_24x7_8h_rank"]),
            int(hb_pan["inference_weekday_9_17_4h_rank"]),
            int(hb_pan["inference_weekday_9_17_8h_rank"]),
        ))
        self.assertIn(hb_pan["best_fit_lens"], {"Training 4h", "Training 8h", "Inference 4h", "Inference 8h"})

    def test_daily_and_hourly_artifacts_have_expected_grain(self) -> None:
        prices = (([12.0] * 8) + ([40.0] * 8) + ([18.0] * 8)) * 2
        processed = make_processed_frame({"HB_PAN": prices})
        bundle = build_artifact_bundle(processed)
        self.assertEqual(bundle.daily_profile_windows["profile"].nunique(), 2)
        self.assertEqual(set(bundle.hourly_profile_shape["duration_hours"].tolist()), {4, 8})
        self.assertIn("effective_active_price_avg_usd_per_mwh", bundle.hourly_profile_shape.columns)


if __name__ == "__main__":
    unittest.main()
