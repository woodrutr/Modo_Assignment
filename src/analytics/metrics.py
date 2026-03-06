from __future__ import annotations

import argparse

import pandas as pd

from src.analytics.battery_model import summarize_battery_value
from src.config import AppSettings, SETTINGS


def _require_metric_columns(frame: pd.DataFrame) -> None:
    required_columns = {"location", "location_type", "market_date", "spp"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns for metrics: {sorted(missing_columns)}")


def compute_daily_spreads(frame: pd.DataFrame) -> pd.DataFrame:
    _require_metric_columns(frame)
    daily_spreads = (
        frame.groupby(["location", "market_date"], sort=True)
        .agg(
            daily_min_price=("spp", "min"),
            daily_max_price=("spp", "max"),
        )
        .reset_index()
    )
    daily_spreads["daily_spread"] = (
        daily_spreads["daily_max_price"] - daily_spreads["daily_min_price"]
    )
    return daily_spreads.sort_values(by=["location", "market_date"]).reset_index(drop=True)


def _normalize_to_score(series: pd.Series) -> pd.Series:
    min_value = float(series.min())
    max_value = float(series.max())
    if abs(max_value - min_value) < 1e-9:
        return pd.Series(50.0, index=series.index, dtype="float64")
    return (series - min_value) / (max_value - min_value) * 100.0


def compute_location_metrics(
    frame: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    _require_metric_columns(frame)
    daily_spreads = compute_daily_spreads(frame)

    metrics = (
        frame.groupby(["location", "location_type"], sort=True)
        .agg(
            observations=("spp", "count"),
            avg_price=("spp", "mean"),
            std_price=("spp", lambda series: float(series.std(ddof=0))),
            pct_negative=("spp", lambda series: float((series < 0).mean() * 100.0)),
            pct_below_20=(
                "spp",
                lambda series: float((series < settings.low_price_threshold).mean() * 100.0),
            ),
            pct_above_100=(
                "spp",
                lambda series: float((series > settings.high_price_threshold).mean() * 100.0),
            ),
        )
        .reset_index()
    )

    avg_daily_spreads = (
        daily_spreads.groupby("location", sort=True)
        .agg(avg_daily_spread=("daily_spread", "mean"))
        .reset_index()
    )
    metrics = metrics.merge(avg_daily_spreads, on="location", how="inner", validate="one_to_one")

    metrics["norm_pct_negative"] = _normalize_to_score(metrics["pct_negative"])
    metrics["norm_pct_below_20"] = _normalize_to_score(metrics["pct_below_20"])
    metrics["norm_avg_daily_spread"] = _normalize_to_score(metrics["avg_daily_spread"])
    metrics["norm_pct_above_100"] = _normalize_to_score(metrics["pct_above_100"])

    weights = settings.metric_weights
    metrics["battery_opportunity_score"] = (
        metrics["norm_pct_negative"] * weights.pct_negative
        + metrics["norm_pct_below_20"] * weights.pct_below_20
        + metrics["norm_avg_daily_spread"] * weights.avg_daily_spread
        + metrics["norm_pct_above_100"] * weights.pct_above_100
    )

    metrics = metrics.sort_values(
        by=["battery_opportunity_score", "avg_daily_spread"],
        ascending=[False, False],
    ).reset_index(drop=True)
    metrics["rank"] = metrics.index + 1
    return metrics


def _resolve_processed_year(settings: AppSettings) -> int:
    for year in (settings.target_year, settings.fallback_year):
        if settings.processed_dam_path(year).exists():
            return year
    raise FileNotFoundError(
        "No processed ERCOT DAM dataset found. Run `python -m src.data.fetch` first.",
    )


def build_metric_artifacts(
    year: int,
    settings: AppSettings = SETTINGS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    processed_frame = pd.read_parquet(settings.processed_dam_path(year))
    location_metrics = compute_location_metrics(processed_frame, settings)
    daily_spreads = compute_daily_spreads(processed_frame)
    battery_summary = summarize_battery_value(processed_frame, settings)

    settings.metrics_dir.mkdir(parents=True, exist_ok=True)
    location_metrics.to_parquet(settings.metrics_path(year), index=False)
    daily_spreads.to_parquet(settings.daily_spread_path(year), index=False)
    battery_summary.to_parquet(settings.battery_value_path(year), index=False)
    return location_metrics, daily_spreads, battery_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ERCOT screener metric artifacts.")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Override the processed analysis year to read from data/processed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    year = args.year if args.year is not None else _resolve_processed_year(SETTINGS)
    location_metrics, daily_spreads, battery_summary = build_metric_artifacts(
        year=year,
        settings=SETTINGS,
    )
    print(f"Metrics parquet: {SETTINGS.metrics_path(year)} ({len(location_metrics)} rows)")
    print(f"Daily spreads parquet: {SETTINGS.daily_spread_path(year)} ({len(daily_spreads)} rows)")
    print(f"Battery parquet: {SETTINGS.battery_value_path(year)} ({len(battery_summary)} rows)")


if __name__ == "__main__":
    main()
