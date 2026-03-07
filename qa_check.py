"""QA/QC checks for the annual large-load flexibility dashboard."""

from __future__ import annotations

import pandas as pd

from src.config import SETTINGS, lens_metric_column
from src.presentation.texas_map import build_location_map_frame


ACTIVE_PROFILE = "training_24x7"
ACTIVE_DURATION = 4


metrics = pd.read_parquet(SETTINGS.metrics_path(SETTINGS.target_year))
daily_windows = pd.read_parquet(SETTINGS.daily_profile_windows_path(SETTINGS.target_year))
hourly_shape = pd.read_parquet(SETTINGS.hourly_profile_shape_path(SETTINGS.target_year))

map_frame = build_location_map_frame(metrics, ACTIVE_PROFILE, ACTIVE_DURATION)
rank_col = lens_metric_column(ACTIVE_PROFILE, ACTIVE_DURATION, "rank")
score_col = lens_metric_column(ACTIVE_PROFILE, ACTIVE_DURATION, "score")
price_col = lens_metric_column(ACTIVE_PROFILE, ACTIVE_DURATION, "effective_avg_price_usd_per_mwh")
reduction_col = lens_metric_column(ACTIVE_PROFILE, ACTIVE_DURATION, "annual_cost_reduction_pct")

print("=== MAP ANCHOR CHECK ===")
print("Active lens:", ACTIVE_PROFILE, f"{ACTIVE_DURATION}h")
print("Missing anchors:", map_frame["lat"].isna().sum())
print("Top map order:", map_frame[["location", "map_rank"]].head().to_string(index=False))
print()

print("=== KPI CHECK ===")
leader = metrics.sort_values(rank_col).iloc[0]
print(f"Leader: {leader['location']} rank={int(leader[rank_col])} score={leader[score_col]:.1f}")
print(f"Effective average price: ${leader[price_col]:.2f}/MWh")
print(f"Annual cost reduction: {leader[reduction_col]:.1f}%")
print(f"Best-fit lens: {leader['best_fit_lens']}")
print()

print("=== ARTIFACT GRAIN CHECK ===")
print("Location metrics rows:", len(metrics))
print("Daily profile windows rows:", len(daily_windows))
print("Hourly profile shape rows:", len(hourly_shape))
print("Profiles in daily windows:", sorted(daily_windows["profile"].unique().tolist()))
print("Durations in hourly shape:", sorted(hourly_shape["duration_hours"].unique().tolist()))
print()

print("=== SCORE BOUNDS ===")
for profile in ("training_24x7", "inference_weekday_9_17"):
    for duration in (4, 8):
        column = lens_metric_column(profile, duration, "score")
        print(column, "min", metrics[column].min(), "max", metrics[column].max())
print()

print("=== QA CHECK COMPLETE ===")
