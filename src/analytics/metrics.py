"""Compute annual ERCOT location metrics and drilldown artifacts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.analytics.battery_model import (
    build_daily_profile_windows,
    build_hourly_profile_dispatch_frame,
    build_hourly_profile_shape_artifact,
    derive_local_time_features,
)
from src.config import (
    AppSettings,
    DURATION_OPTIONS,
    LENS_KEYS,
    PROFILE_ORDER,
    SETTINGS,
    lens_label,
    lens_metric_column,
)


LEGACY_RANK_ORDER_2025 = (
    "HB_PAN",
    "LZ_WEST",
    "LZ_LCRA",
    "HB_WEST",
    "LZ_CPS",
    "LZ_AEN",
    "LZ_NORTH",
    "LZ_RAYBN",
    "HB_NORTH",
    "HB_HUBAVG",
    "HB_BUSAVG",
    "HB_SOUTH",
    "LZ_HOUSTON",
    "HB_HOUSTON",
    "LZ_SOUTH",
)


@dataclass(frozen=True)
class ArtifactBundle:
    location_metrics: pd.DataFrame
    daily_spreads: pd.DataFrame
    battery_value: pd.DataFrame
    daily_profile_windows: pd.DataFrame
    hourly_profile_shape: pd.DataFrame


def _minmax_scale(series: pd.Series, inverse: bool = False) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    if numeric.isna().all():
        return pd.Series(np.nan, index=series.index, dtype=float)
    min_value = float(numeric.min())
    max_value = float(numeric.max())
    if np.isclose(max_value, min_value):
        return pd.Series(100.0, index=series.index, dtype=float)

    scaled = (numeric - min_value) / (max_value - min_value)
    if inverse:
        scaled = 1.0 - scaled
    return scaled * 100.0


def _assign_rank(
    frame: pd.DataFrame,
    score_column: str,
    secondary_desc_column: str,
    tertiary_asc_column: str | None = None,
    rank_column: str = "rank",
) -> pd.DataFrame:
    sort_columns = [score_column, secondary_desc_column, "location"]
    ascending = [False, False, True]
    if tertiary_asc_column is not None:
        sort_columns.insert(2, tertiary_asc_column)
        ascending.insert(2, True)

    ranked = frame.sort_values(sort_columns, ascending=ascending, kind="mergesort").reset_index(drop=True)
    ranked[rank_column] = pd.RangeIndex(start=1, stop=len(ranked) + 1, step=1)
    return ranked


def compute_daily_spreads(processed: pd.DataFrame) -> pd.DataFrame:
    spreads = (
        processed.groupby(["location", "market_date"], as_index=False)
        .agg(
            daily_min_price=("spp", "min"),
            daily_max_price=("spp", "max"),
        )
        .assign(daily_spread=lambda frame: frame["daily_max_price"] - frame["daily_min_price"])
        .sort_values(["location", "market_date"], kind="mergesort")
        .reset_index(drop=True)
    )
    return spreads


def compute_legacy_location_metrics(
    processed: pd.DataFrame,
    daily_spreads: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    grouped = (
        processed.groupby(["location", "location_type"], as_index=False)
        .agg(
            observations=("spp", "size"),
            avg_price=("spp", "mean"),
            std_price=("spp", "std"),
            pct_negative=("spp", lambda series: float(series.lt(0).mean() * 100.0)),
            pct_below_20=(
                "spp",
                lambda series: float(series.lt(settings.low_price_threshold).mean() * 100.0),
            ),
            pct_above_100=(
                "spp",
                lambda series: float(series.gt(settings.high_price_threshold).mean() * 100.0),
            ),
        )
    )

    avg_spreads = (
        daily_spreads.groupby("location", as_index=False)
        .agg(avg_daily_spread=("daily_spread", "mean"))
    )
    legacy = grouped.merge(avg_spreads, on="location", how="left", validate="one_to_one")
    legacy["norm_pct_negative"] = _minmax_scale(legacy["pct_negative"])
    legacy["norm_pct_below_20"] = _minmax_scale(legacy["pct_below_20"])
    legacy["norm_avg_daily_spread"] = _minmax_scale(legacy["avg_daily_spread"])
    legacy["norm_pct_above_100"] = _minmax_scale(legacy["pct_above_100"])

    weights = settings.legacy_metric_weights
    legacy["battery_opportunity_score"] = (
        weights.pct_negative * legacy["norm_pct_negative"]
        + weights.pct_below_20 * legacy["norm_pct_below_20"]
        + weights.avg_daily_spread * legacy["norm_avg_daily_spread"]
        + weights.pct_above_100 * legacy["norm_pct_above_100"]
    )

    legacy = _assign_rank(
        frame=legacy,
        score_column="battery_opportunity_score",
        secondary_desc_column="avg_daily_spread",
        tertiary_asc_column="avg_price",
        rank_column="rank",
    )
    return legacy


def compute_legacy_battery_value(
    processed: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    charge_hours = settings.legacy_battery.charge_hours_per_day
    charge_mwh_per_hour = settings.legacy_battery.charge_mwh_per_hour
    round_trip_efficiency = settings.legacy_battery.round_trip_efficiency

    for (location, market_date), day_frame in processed.groupby(["location", "market_date"], sort=True):
        ordered_prices = np.sort(day_frame["spp"].to_numpy(dtype=float))
        charge_cost = float(ordered_prices[:charge_hours].sum() * charge_mwh_per_hour / round_trip_efficiency)
        discharge_value = float(ordered_prices[-charge_hours:].sum() * charge_mwh_per_hour)
        daily_value = discharge_value - charge_cost
        rows.append(
            {
                "location": str(location),
                "market_date": market_date,
                "daily_battery_value_usd": daily_value,
            }
        )

    daily_values = pd.DataFrame(rows)
    battery = (
        daily_values.groupby("location", as_index=False)
        .agg(
            annual_battery_gross_margin_usd=("daily_battery_value_usd", "sum"),
            average_daily_battery_value_usd=("daily_battery_value_usd", "mean"),
            positive_value_days=("daily_battery_value_usd", lambda series: int(series.gt(0).sum())),
            days_modeled=("daily_battery_value_usd", "size"),
        )
        .assign(
            pct_positive_value_days=lambda frame: (
                frame["positive_value_days"] / frame["days_modeled"] * 100.0
            )
        )
        .sort_values(
            ["annual_battery_gross_margin_usd", "location"],
            ascending=[False, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )
    return battery


def _annual_inference_context(processed: pd.DataFrame) -> pd.DataFrame:
    local_frame = derive_local_time_features(processed)
    weekday = local_frame.loc[local_frame["is_weekday"]].copy()
    day_mask = weekday["local_hour"].between(9, 16)
    overnight_mask = weekday["local_hour"].between(0, 8)

    day = (
        weekday.loc[day_mask]
        .groupby("location", as_index=False)
        .agg(inference_weekday_day_avg_price_usd_per_mwh=("spp", "mean"))
    )
    overnight = (
        weekday.loc[overnight_mask]
        .groupby("location", as_index=False)
        .agg(inference_weekday_overnight_avg_price_usd_per_mwh=("spp", "mean"))
    )
    context = day.merge(overnight, on="location", how="outer", validate="one_to_one")
    context["inference_day_minus_overnight_spread_usd_per_mwh"] = (
        context["inference_weekday_day_avg_price_usd_per_mwh"]
        - context["inference_weekday_overnight_avg_price_usd_per_mwh"]
    )
    return context


def _summarize_lens_metrics(
    daily_windows: pd.DataFrame,
    hourly_dispatch: pd.DataFrame,
    profile_key: str,
    duration_hours: int,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    prefix = f"{duration_hours}h"
    eligible = daily_windows.loc[
        daily_windows["profile"].eq(profile_key) & daily_windows["active_load_mwh"].gt(0),
        :,
    ].copy()
    if eligible.empty:
        raise ValueError(f"No eligible daily windows found for {profile_key} {duration_hours}h.")

    day_column = f"{prefix}_profitable"
    spread_column = f"{prefix}_best_spread_usd_per_mwh"
    value_column = f"{prefix}_net_value_usd_per_mw_day"
    effective_column = f"{prefix}_effective_daily_cost_usd_per_mw_day"

    daily_summary = (
        eligible.groupby(["location", "location_type"], as_index=False)
        .agg(
            baseline_annual_cost_usd_per_mw_year=("baseline_daily_cost_usd_per_mw_day", "sum"),
            effective_annual_cost_usd_per_mw_year=(effective_column, "sum"),
            annual_active_load_mwh=("active_load_mwh", "sum"),
            annual_cost_reduction_usd_per_mw_year=(value_column, "sum"),
            count_profitable_days=(day_column, "sum"),
            eligible_day_count=("local_date", "size"),
            p50_daily_best_spread_usd_per_mwh=(spread_column, lambda series: float(series.quantile(0.50))),
            p90_daily_best_spread_usd_per_mwh=(spread_column, lambda series: float(series.quantile(0.90))),
        )
    )

    daily_summary["annual_cost_reduction_pct"] = np.where(
        daily_summary["baseline_annual_cost_usd_per_mw_year"].gt(0),
        (
            daily_summary["annual_cost_reduction_usd_per_mw_year"]
            / daily_summary["baseline_annual_cost_usd_per_mw_year"]
            * 100.0
        ),
        0.0,
    )
    daily_summary["profitable_day_share"] = np.where(
        daily_summary["eligible_day_count"].gt(0),
        daily_summary["count_profitable_days"] / daily_summary["eligible_day_count"] * 100.0,
        0.0,
    )
    daily_summary["effective_avg_price_usd_per_mwh"] = np.where(
        daily_summary["annual_active_load_mwh"].gt(0),
        daily_summary["effective_annual_cost_usd_per_mw_year"] / daily_summary["annual_active_load_mwh"],
        np.nan,
    )

    hourly_slice = hourly_dispatch.loc[
        hourly_dispatch["profile"].eq(profile_key)
        & hourly_dispatch["duration_hours"].eq(duration_hours)
        & hourly_dispatch["active_hour_flag"],
        :,
    ]
    hourly_summary = (
        hourly_slice.groupby("location", as_index=False)
        .agg(
            p95_active_hour_price_usd_per_mwh=(
                "market_price_usd_per_mwh",
                lambda series: float(series.quantile(0.95)),
            ),
            p95_active_hour_effective_price_usd_per_mwh=(
                "effective_active_price_usd_per_mwh",
                lambda series: float(series.quantile(0.95)),
            ),
        )
    )
    hourly_summary["p95_active_hour_reduction_pct"] = np.where(
        hourly_summary["p95_active_hour_price_usd_per_mwh"].gt(0),
        (
            (
                hourly_summary["p95_active_hour_price_usd_per_mwh"]
                - hourly_summary["p95_active_hour_effective_price_usd_per_mwh"]
            )
            / hourly_summary["p95_active_hour_price_usd_per_mwh"]
            * 100.0
        ),
        0.0,
    )

    summary = daily_summary.merge(hourly_summary, on="location", how="left", validate="one_to_one")

    weights = settings.lens_score_weights
    summary["score_component_effective_avg_price"] = _minmax_scale(
        summary["effective_avg_price_usd_per_mwh"], inverse=True
    )
    summary["score_component_annual_cost_reduction_pct"] = _minmax_scale(
        summary["annual_cost_reduction_pct"]
    )
    summary["score_component_profitable_day_share"] = _minmax_scale(summary["profitable_day_share"])
    summary["score_component_p95_active_hour_reduction_pct"] = _minmax_scale(
        summary["p95_active_hour_reduction_pct"]
    )
    summary["score"] = (
        weights.effective_avg_price * summary["score_component_effective_avg_price"]
        + weights.annual_cost_reduction_pct * summary["score_component_annual_cost_reduction_pct"]
        + weights.profitable_day_share * summary["score_component_profitable_day_share"]
        + weights.p95_active_hour_reduction_pct * summary["score_component_p95_active_hour_reduction_pct"]
    )

    summary = _assign_rank(
        frame=summary,
        score_column="score",
        secondary_desc_column="annual_cost_reduction_pct",
        tertiary_asc_column="effective_avg_price_usd_per_mwh",
        rank_column="lens_rank",
    )
    summary = summary.rename(columns={"score": "lens_score"})
    summary["profile"] = profile_key
    summary["duration_hours"] = duration_hours
    summary["lens_name"] = summary.apply(
        lambda row: lens_label(row["profile"], int(row["duration_hours"])),
        axis=1,
    )
    return summary


def compute_location_metrics_artifact(
    processed: pd.DataFrame,
    daily_spreads: pd.DataFrame,
    daily_profile_windows: pd.DataFrame,
    hourly_dispatch: pd.DataFrame,
    legacy_battery: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    legacy_metrics = compute_legacy_location_metrics(processed, daily_spreads, settings=settings)

    annual = legacy_metrics.copy()
    annual = annual.merge(_annual_inference_context(processed), on="location", how="left", validate="one_to_one")
    annual = annual.merge(
        legacy_battery,
        on="location",
        how="left",
        validate="one_to_one",
    )

    lens_frames: list[pd.DataFrame] = []
    for profile_key, duration_hours in LENS_KEYS:
        lens_frame = _summarize_lens_metrics(
            daily_windows=daily_profile_windows,
            hourly_dispatch=hourly_dispatch,
            profile_key=profile_key,
            duration_hours=duration_hours,
            settings=settings,
        )
        lens_frames.append(lens_frame)

        rename_map = {
            "baseline_annual_cost_usd_per_mw_year": lens_metric_column(
                profile_key,
                duration_hours,
                "baseline_annual_cost_usd_per_mw_year",
            ),
            "effective_annual_cost_usd_per_mw_year": lens_metric_column(
                profile_key,
                duration_hours,
                "effective_annual_cost_usd_per_mw_year",
            ),
            "effective_avg_price_usd_per_mwh": lens_metric_column(
                profile_key,
                duration_hours,
                "effective_avg_price_usd_per_mwh",
            ),
            "annual_cost_reduction_usd_per_mw_year": lens_metric_column(
                profile_key,
                duration_hours,
                "annual_cost_reduction_usd_per_mw_year",
            ),
            "annual_cost_reduction_pct": lens_metric_column(
                profile_key,
                duration_hours,
                "annual_cost_reduction_pct",
            ),
            "profitable_day_share": lens_metric_column(profile_key, duration_hours, "profitable_day_share"),
            "count_profitable_days": lens_metric_column(profile_key, duration_hours, "count_profitable_days"),
            "p50_daily_best_spread_usd_per_mwh": lens_metric_column(
                profile_key,
                duration_hours,
                "p50_daily_best_spread_usd_per_mwh",
            ),
            "p90_daily_best_spread_usd_per_mwh": lens_metric_column(
                profile_key,
                duration_hours,
                "p90_daily_best_spread_usd_per_mwh",
            ),
            "p95_active_hour_price_usd_per_mwh": lens_metric_column(
                profile_key,
                duration_hours,
                "p95_active_hour_price_usd_per_mwh",
            ),
            "p95_active_hour_effective_price_usd_per_mwh": lens_metric_column(
                profile_key,
                duration_hours,
                "p95_active_hour_effective_price_usd_per_mwh",
            ),
            "p95_active_hour_reduction_pct": lens_metric_column(
                profile_key,
                duration_hours,
                "p95_active_hour_reduction_pct",
            ),
            "lens_score": lens_metric_column(profile_key, duration_hours, "score"),
            "lens_rank": lens_metric_column(profile_key, duration_hours, "rank"),
        }
        annual = annual.merge(
            lens_frame.loc[:, ["location", *rename_map.keys()]].rename(columns=rename_map),
            on="location",
            how="left",
            validate="one_to_one",
        )

    lens_index = pd.concat(
        [
            frame.loc[
                :,
                ["location", "profile", "duration_hours", "lens_name", "lens_rank", "annual_cost_reduction_pct", "lens_score"],
            ]
            for frame in lens_frames
        ],
        ignore_index=True,
    )
    best_fit = (
        lens_index.sort_values(
            ["location", "lens_rank", "annual_cost_reduction_pct", "lens_score", "lens_name"],
            ascending=[True, True, False, False, True],
            kind="mergesort",
        )
        .groupby("location", as_index=False)
        .first()
        .rename(
            columns={
                "lens_name": "best_fit_lens",
                "lens_rank": "best_fit_rank",
            }
        )
    )
    annual = annual.merge(
        best_fit.loc[:, ["location", "best_fit_lens", "best_fit_rank", "profile", "duration_hours"]],
        on="location",
        how="left",
        validate="one_to_one",
    ).rename(columns={"profile": "best_fit_profile", "duration_hours": "best_fit_duration_hours"})

    annual = annual.sort_values(["rank", "location"], kind="mergesort").reset_index(drop=True)

    if settings.target_year == 2025 and len(annual) == len(LEGACY_RANK_ORDER_2025):
        order = tuple(annual["location"].tolist())
        if order != LEGACY_RANK_ORDER_2025:
            raise ValueError(
                "Legacy annual ranking order drifted. "
                f"Expected {LEGACY_RANK_ORDER_2025}, received {order}."
            )

    return annual


def build_artifact_bundle(
    processed: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> ArtifactBundle:
    daily_spreads = compute_daily_spreads(processed)
    legacy_battery = compute_legacy_battery_value(processed, settings=settings)
    daily_profile_windows = build_daily_profile_windows(processed, settings=settings)
    hourly_dispatch = build_hourly_profile_dispatch_frame(
        processed=processed,
        daily_windows=daily_profile_windows,
        settings=settings,
    )
    hourly_profile_shape = build_hourly_profile_shape_artifact(hourly_dispatch)
    location_metrics = compute_location_metrics_artifact(
        processed=processed,
        daily_spreads=daily_spreads,
        daily_profile_windows=daily_profile_windows,
        hourly_dispatch=hourly_dispatch,
        legacy_battery=legacy_battery,
        settings=settings,
    )
    return ArtifactBundle(
        location_metrics=location_metrics,
        daily_spreads=daily_spreads,
        battery_value=legacy_battery,
        daily_profile_windows=daily_profile_windows,
        hourly_profile_shape=hourly_profile_shape,
    )


def write_metric_artifacts(
    year: int,
    settings: AppSettings = SETTINGS,
) -> ArtifactBundle:
    processed_path = settings.processed_dam_path(year)
    if not processed_path.exists():
        raise FileNotFoundError(
            f"Missing processed parquet: {processed_path}. Run `python -m src.data.fetch` first."
        )

    processed = pd.read_parquet(processed_path)
    bundle = build_artifact_bundle(processed=processed, settings=settings)
    settings.metrics_dir.mkdir(parents=True, exist_ok=True)
    bundle.location_metrics.to_parquet(settings.metrics_path(year), index=False)
    bundle.daily_spreads.to_parquet(settings.daily_spread_path(year), index=False)
    bundle.battery_value.to_parquet(settings.battery_value_path(year), index=False)
    bundle.daily_profile_windows.to_parquet(settings.daily_profile_windows_path(year), index=False)
    bundle.hourly_profile_shape.to_parquet(settings.hourly_profile_shape_path(year), index=False)
    return bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=SETTINGS.target_year)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = write_metric_artifacts(args.year)
    print(f"Location metrics: {len(bundle.location_metrics)} rows -> {SETTINGS.metrics_path(args.year)}")
    print(f"Daily spreads: {len(bundle.daily_spreads)} rows -> {SETTINGS.daily_spread_path(args.year)}")
    print(f"Battery value: {len(bundle.battery_value)} rows -> {SETTINGS.battery_value_path(args.year)}")
    print(
        "Daily profile windows: "
        f"{len(bundle.daily_profile_windows)} rows -> {SETTINGS.daily_profile_windows_path(args.year)}"
    )
    print(
        "Hourly profile shape: "
        f"{len(bundle.hourly_profile_shape)} rows -> {SETTINGS.hourly_profile_shape_path(args.year)}"
    )


if __name__ == "__main__":
    main()
