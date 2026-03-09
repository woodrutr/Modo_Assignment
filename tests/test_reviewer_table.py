from __future__ import annotations

import unittest

import pandas as pd

from src.presentation.reviewer_table import (
    build_next_step_prompt,
    build_rank_context,
    build_reviewer_table,
    build_selected_metric_table,
    build_why_it_ranks_high,
)


class ReviewerTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = pd.DataFrame(
            [
                {
                    "location": "HB_PAN",
                    "location_type": "Trading Hub",
                    "best_fit_lens": "Training 8h",
                    "best_fit_rank": 1,
                    "battery_opportunity_score": 64.0,
                    "rank": 1,
                    "avg_price": 25.4,
                    "std_price": 30.8,
                    "avg_daily_spread": 67.0,
                    "annual_battery_gross_margin_usd": 5902408.0,
                    "average_daily_battery_value_usd": 16171.0,
                    "pct_positive_value_days": 100.0,
                    "training_24x7_4h_rank": 1,
                    "training_24x7_4h_score": 98.0,
                    "training_24x7_4h_effective_avg_price_usd_per_mwh": 18.2,
                    "training_24x7_4h_annual_cost_reduction_pct": 11.4,
                    "training_24x7_4h_baseline_annual_cost_usd_per_mw_year": 200000.0,
                    "training_24x7_4h_effective_annual_cost_usd_per_mw_year": 177200.0,
                    "training_24x7_4h_annual_cost_reduction_usd_per_mw_year": 22800.0,
                    "training_24x7_4h_profitable_day_share": 92.0,
                    "training_24x7_4h_count_profitable_days": 336,
                    "training_24x7_4h_p50_daily_best_spread_usd_per_mwh": 16.2,
                    "training_24x7_4h_p90_daily_best_spread_usd_per_mwh": 42.0,
                    "training_24x7_4h_p95_active_hour_price_usd_per_mwh": 102.0,
                    "training_24x7_4h_p95_active_hour_effective_price_usd_per_mwh": 15.3,
                    "training_24x7_4h_p95_active_hour_reduction_pct": 85.0,
                    "training_24x7_8h_rank": 1,
                    "training_24x7_8h_score": 99.0,
                    "training_24x7_8h_effective_avg_price_usd_per_mwh": 17.5,
                    "training_24x7_8h_annual_cost_reduction_pct": 15.1,
                    "training_24x7_8h_baseline_annual_cost_usd_per_mw_year": 200000.0,
                    "training_24x7_8h_effective_annual_cost_usd_per_mw_year": 169800.0,
                    "training_24x7_8h_annual_cost_reduction_usd_per_mw_year": 30200.0,
                    "training_24x7_8h_profitable_day_share": 95.0,
                    "training_24x7_8h_count_profitable_days": 347,
                    "training_24x7_8h_p50_daily_best_spread_usd_per_mwh": 18.8,
                    "training_24x7_8h_p90_daily_best_spread_usd_per_mwh": 48.3,
                    "training_24x7_8h_p95_active_hour_price_usd_per_mwh": 102.0,
                    "training_24x7_8h_p95_active_hour_effective_price_usd_per_mwh": 15.3,
                    "training_24x7_8h_p95_active_hour_reduction_pct": 85.0,
                },
                {
                    "location": "LZ_WEST",
                    "location_type": "Load Zone",
                    "best_fit_lens": "Training 4h",
                    "best_fit_rank": 2,
                    "battery_opportunity_score": 28.0,
                    "rank": 2,
                    "avg_price": 35.4,
                    "std_price": 18.8,
                    "avg_daily_spread": 22.0,
                    "annual_battery_gross_margin_usd": 1800000.0,
                    "average_daily_battery_value_usd": 4931.0,
                    "pct_positive_value_days": 58.0,
                    "training_24x7_4h_rank": 2,
                    "training_24x7_4h_score": 44.0,
                    "training_24x7_4h_effective_avg_price_usd_per_mwh": 32.1,
                    "training_24x7_4h_annual_cost_reduction_pct": 4.0,
                    "training_24x7_4h_baseline_annual_cost_usd_per_mw_year": 240000.0,
                    "training_24x7_4h_effective_annual_cost_usd_per_mw_year": 230400.0,
                    "training_24x7_4h_annual_cost_reduction_usd_per_mw_year": 9600.0,
                    "training_24x7_4h_profitable_day_share": 30.0,
                    "training_24x7_4h_count_profitable_days": 110,
                    "training_24x7_4h_p50_daily_best_spread_usd_per_mwh": 4.2,
                    "training_24x7_4h_p90_daily_best_spread_usd_per_mwh": 11.0,
                    "training_24x7_4h_p95_active_hour_price_usd_per_mwh": 81.0,
                    "training_24x7_4h_p95_active_hour_effective_price_usd_per_mwh": 71.3,
                    "training_24x7_4h_p95_active_hour_reduction_pct": 12.0,
                    "training_24x7_8h_rank": 2,
                    "training_24x7_8h_score": 41.0,
                    "training_24x7_8h_effective_avg_price_usd_per_mwh": 31.5,
                    "training_24x7_8h_annual_cost_reduction_pct": 4.5,
                    "training_24x7_8h_baseline_annual_cost_usd_per_mw_year": 240000.0,
                    "training_24x7_8h_effective_annual_cost_usd_per_mw_year": 229200.0,
                    "training_24x7_8h_annual_cost_reduction_usd_per_mw_year": 10800.0,
                    "training_24x7_8h_profitable_day_share": 34.0,
                    "training_24x7_8h_count_profitable_days": 124,
                    "training_24x7_8h_p50_daily_best_spread_usd_per_mwh": 5.1,
                    "training_24x7_8h_p90_daily_best_spread_usd_per_mwh": 13.2,
                    "training_24x7_8h_p95_active_hour_price_usd_per_mwh": 81.0,
                    "training_24x7_8h_p95_active_hour_effective_price_usd_per_mwh": 68.0,
                    "training_24x7_8h_p95_active_hour_reduction_pct": 16.0,
                }
            ]
        )

    def test_reviewer_table_surfaces_side_by_side_durations(self) -> None:
        table = build_reviewer_table(self.metrics, "training_24x7")
        self.assertEqual(
            table.columns.tolist(),
            [
                "Rank",
                "Location",
                "Type",
                "4h Score",
                "8h Score",
                "4h Effective Avg Price",
                "8h Effective Avg Price",
                "4h Cost Reduction %",
                "8h Cost Reduction %",
                "Best Fit Lens",
            ],
        )
        self.assertEqual(table.iloc[0]["Best Fit Lens"], "Training 8h")

    def test_selected_metric_table_includes_profile_lens_metrics(self) -> None:
        result = build_selected_metric_table(self.metrics.iloc[0], "training_24x7", focus_duration=8)
        self.assertIn("Training 8h Effective Avg Price Usd/Mwh", result["Metric"].tolist())
        self.assertIn("$17.50", result["Value"].tolist())
        self.assertIn("Training 8h Annual Cost Reduction %", result["Metric"].tolist())

    def test_build_why_it_ranks_high_uses_controlled_reason_phrases(self) -> None:
        text = build_why_it_ranks_high(
            self.metrics.iloc[0],
            self.metrics,
            "training_24x7",
            4,
        )
        allowed = {
            "frequent low-price charging windows",
            "higher intraday spread potential",
            "stronger tail-risk reduction under flexible load shaping",
            "more variability than peer regions",
            "lower effective delivered cost under the active lens",
        }
        matches = [phrase for phrase in allowed if phrase in text]
        self.assertGreaterEqual(len(matches), 2)
        self.assertTrue(text.startswith("HB_PAN screens well here because it shows "))

    def test_build_rank_context_marks_lower_rank_rows_differently(self) -> None:
        title, body = build_rank_context(
            self.metrics.iloc[1],
            self.metrics,
            "training_24x7",
            4,
        )
        self.assertEqual(title, "Why it ranks lower")
        self.assertTrue(body.startswith("LZ_WEST screens lower here because it shows "))
        allowed_negative = {
            "fewer low-price charging windows",
            "lower intraday spread potential",
            "weaker tail-risk reduction under flexible load shaping",
            "less variability than peer regions",
            "higher effective delivered cost under the active lens",
        }
        self.assertTrue(any(phrase in body for phrase in allowed_negative))

    def test_build_next_step_prompt_uses_required_format(self) -> None:
        peer_frame = pd.DataFrame(
            [
                {
                    "location": "HB_TOP",
                    "std_price": 35.0,
                    "avg_daily_spread": 40.0,
                    "training_24x7_4h_rank": 1,
                    "training_24x7_4h_annual_cost_reduction_pct": 12.0,
                    "training_24x7_8h_annual_cost_reduction_pct": 15.0,
                    "training_24x7_4h_annual_cost_reduction_usd_per_mw_year": 22000.0,
                    "training_24x7_8h_annual_cost_reduction_usd_per_mw_year": 27000.0,
                    "training_24x7_4h_p95_active_hour_reduction_pct": 30.0,
                },
                {
                    "location": "HB_2",
                    "std_price": 30.0,
                    "avg_daily_spread": 32.0,
                    "training_24x7_4h_rank": 2,
                    "training_24x7_4h_annual_cost_reduction_pct": 9.0,
                    "training_24x7_8h_annual_cost_reduction_pct": 10.0,
                    "training_24x7_4h_annual_cost_reduction_usd_per_mw_year": 18000.0,
                    "training_24x7_8h_annual_cost_reduction_usd_per_mw_year": 19500.0,
                    "training_24x7_4h_p95_active_hour_reduction_pct": 24.0,
                },
                {
                    "location": "HB_MID",
                    "std_price": 25.0,
                    "avg_daily_spread": 24.0,
                    "training_24x7_4h_rank": 3,
                    "training_24x7_8h_rank": 3,
                    "training_24x7_4h_annual_cost_reduction_pct": 7.0,
                    "training_24x7_8h_annual_cost_reduction_pct": 9.0,
                    "training_24x7_4h_annual_cost_reduction_usd_per_mw_year": 15000.0,
                    "training_24x7_8h_annual_cost_reduction_usd_per_mw_year": 18100.0,
                    "training_24x7_4h_p95_active_hour_reduction_pct": 22.0,
                },
                {
                    "location": "HB_4",
                    "std_price": 20.0,
                    "avg_daily_spread": 18.0,
                    "training_24x7_4h_rank": 4,
                    "training_24x7_4h_annual_cost_reduction_pct": 5.0,
                    "training_24x7_8h_annual_cost_reduction_pct": 6.0,
                    "training_24x7_4h_annual_cost_reduction_usd_per_mw_year": 11000.0,
                    "training_24x7_8h_annual_cost_reduction_usd_per_mw_year": 12300.0,
                    "training_24x7_4h_p95_active_hour_reduction_pct": 14.0,
                },
                {
                    "location": "HB_LOW",
                    "std_price": 34.0,
                    "avg_daily_spread": 39.0,
                    "training_24x7_4h_rank": 5,
                    "training_24x7_4h_annual_cost_reduction_pct": 2.0,
                    "training_24x7_8h_annual_cost_reduction_pct": 2.8,
                    "training_24x7_4h_annual_cost_reduction_usd_per_mw_year": 4200.0,
                    "training_24x7_8h_annual_cost_reduction_usd_per_mw_year": 5200.0,
                    "training_24x7_4h_p95_active_hour_reduction_pct": 8.0,
                },
            ]
        )
        result = build_next_step_prompt(peer_frame.iloc[0], peer_frame, "training_24x7", 4)
        self.assertIn("HB_TOP", result)
        self.assertIn("incremental 8h value over 4h", result)

        mid_result = build_next_step_prompt(peer_frame.iloc[2], peer_frame, "training_24x7", 4)
        self.assertIn("HB_MID", mid_result)
        self.assertIn("middle of the pack into the first-look set", mid_result)

        low_result = build_next_step_prompt(peer_frame.iloc[4], peer_frame, "training_24x7", 4)
        self.assertIn("HB_LOW", low_result)
        self.assertIn("volatility-led edge case", low_result)


if __name__ == "__main__":
    unittest.main()
