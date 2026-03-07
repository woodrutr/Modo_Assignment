"""Presentation-only helpers for reviewer-facing annual screener tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import (
    DURATION_OPTIONS,
    LoadProfileKey,
    PROFILE_LABELS,
    lens_label,
    lens_metric_column,
)


def build_reviewer_table(metrics: pd.DataFrame, profile_key: LoadProfileKey) -> pd.DataFrame:
    columns = {
        lens_metric_column(profile_key, 4, "rank"): "Rank",
        "location": "Location",
        "location_type": "Type",
        lens_metric_column(profile_key, 4, "score"): "4h Score",
        lens_metric_column(profile_key, 8, "score"): "8h Score",
        lens_metric_column(profile_key, 4, "effective_avg_price_usd_per_mwh"): "4h Effective Avg Price",
        lens_metric_column(profile_key, 8, "effective_avg_price_usd_per_mwh"): "8h Effective Avg Price",
        lens_metric_column(profile_key, 4, "annual_cost_reduction_pct"): "4h Cost Reduction %",
        lens_metric_column(profile_key, 8, "annual_cost_reduction_pct"): "8h Cost Reduction %",
        "best_fit_lens": "Best Fit Lens",
    }
    table = (
        metrics.loc[:, list(columns.keys())]
        .rename(columns=columns)
        .sort_values("Rank", kind="mergesort")
        .reset_index(drop=True)
    )
    return table


def format_reviewer_table(table: pd.DataFrame) -> pd.DataFrame:
    formatted = table.copy()
    for column in ("4h Score", "8h Score"):
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{value:.1f}" if pd.notna(value) else "—")
    for column in ("4h Effective Avg Price", "8h Effective Avg Price"):
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"${value:.2f}" if pd.notna(value) else "—")
    for column in ("4h Cost Reduction %", "8h Cost Reduction %"):
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{value:.1f}%" if pd.notna(value) else "—")
    if "Rank" in formatted.columns:
        formatted["Rank"] = formatted["Rank"].astype(int)
    return formatted


def _format_metric_value(metric_key: str, value: Any) -> str:
    if pd.isna(value):
        return "—"
    if metric_key.endswith("_rank") or metric_key in {"rank", "observations", "positive_value_days", "days_modeled"}:
        return f"{int(value):,}"
    if metric_key.endswith("_score") or metric_key == "battery_opportunity_score":
        return f"{float(value):.1f}"
    if metric_key.endswith("_share") or metric_key.endswith("_pct") or metric_key.startswith("pct_"):
        return f"{float(value):.1f}%"
    if "usd" in metric_key and "per_mwh" not in metric_key:
        return f"${float(value):,.2f}"
    if "price" in metric_key or metric_key.endswith("_spread") or metric_key.endswith("_per_mwh"):
        return f"${float(value):.2f}"
    return str(value)


def _base_metric_keys(profile_key: LoadProfileKey, focus_duration: int | None) -> list[str]:
    keys = [
        "location",
        "location_type",
        "best_fit_lens",
        "best_fit_rank",
        "battery_opportunity_score",
        "rank",
        "avg_price",
        "std_price",
        "avg_daily_spread",
        "annual_battery_gross_margin_usd",
        "average_daily_battery_value_usd",
        "pct_positive_value_days",
    ]

    durations = (focus_duration,) if focus_duration is not None else DURATION_OPTIONS
    for duration_hours in durations:
        keys.extend(
            [
                lens_metric_column(profile_key, duration_hours, "rank"),
                lens_metric_column(profile_key, duration_hours, "score"),
                lens_metric_column(profile_key, duration_hours, "baseline_annual_cost_usd_per_mw_year"),
                lens_metric_column(profile_key, duration_hours, "effective_annual_cost_usd_per_mw_year"),
                lens_metric_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "annual_cost_reduction_usd_per_mw_year"),
                lens_metric_column(profile_key, duration_hours, "annual_cost_reduction_pct"),
                lens_metric_column(profile_key, duration_hours, "profitable_day_share"),
                lens_metric_column(profile_key, duration_hours, "count_profitable_days"),
                lens_metric_column(profile_key, duration_hours, "p50_daily_best_spread_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "p90_daily_best_spread_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "p95_active_hour_price_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "p95_active_hour_effective_price_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "p95_active_hour_reduction_pct"),
            ]
        )

    if profile_key == "inference_weekday_9_17":
        keys.extend(
            [
                "inference_weekday_day_avg_price_usd_per_mwh",
                "inference_weekday_overnight_avg_price_usd_per_mwh",
                "inference_day_minus_overnight_spread_usd_per_mwh",
            ]
        )
    return keys


def _metric_label(metric_key: str) -> str:
    direct_labels = {
        "location": "Location Code",
        "location_type": "Location Type",
        "best_fit_lens": "Best-Fit Lens",
        "best_fit_rank": "Best-Fit Rank",
        "battery_opportunity_score": "Legacy Opportunity Score",
        "rank": "Legacy Rank",
        "avg_price": "Legacy Average DAM Price",
        "std_price": "Legacy Price Volatility",
        "avg_daily_spread": "Legacy Average Daily Spread",
        "annual_battery_gross_margin_usd": "Legacy Battery Gross Margin",
        "average_daily_battery_value_usd": "Legacy Average Daily Battery Value",
        "pct_positive_value_days": "Legacy Positive-Value Day Share",
        "inference_weekday_day_avg_price_usd_per_mwh": "Weekday Daytime Avg Price",
        "inference_weekday_overnight_avg_price_usd_per_mwh": "Weekday Overnight Avg Price",
        "inference_day_minus_overnight_spread_usd_per_mwh": "Daytime Minus Overnight Spread",
    }
    if metric_key in direct_labels:
        return direct_labels[metric_key]

    for profile_key in PROFILE_LABELS:
        for duration_hours in DURATION_OPTIONS:
            prefix = f"{profile_key}_{duration_hours}h_"
            if metric_key.startswith(prefix):
                suffix = metric_key.removeprefix(prefix)
                label = suffix.replace("_", " ")
                label = label.replace("usd per mw year", "USD per MW-year")
                label = label.replace("usd per mwh", "USD/MWh")
                label = label.replace("pct", "%")
                return f"{lens_label(profile_key, duration_hours)} {label.title()}"

    return metric_key.replace("_", " ").title()


def build_selected_metric_table(
    row: pd.Series,
    profile_key: LoadProfileKey,
    focus_duration: int | None = None,
) -> pd.DataFrame:
    metric_keys = [key for key in _base_metric_keys(profile_key, focus_duration) if key in row.index]
    remaining = sorted(key for key in row.index if key not in metric_keys and key.startswith(profile_key))
    ordered = metric_keys + remaining
    return pd.DataFrame(
        {
            "Metric": [_metric_label(key) for key in ordered],
            "Value": [_format_metric_value(key, row[key]) for key in ordered],
        }
    )


def build_location_narrative(
    row: pd.Series,
    profile_key: LoadProfileKey,
    duration_hours: int,
) -> str:
    rank = int(row[lens_metric_column(profile_key, duration_hours, "rank")])
    score = row[lens_metric_column(profile_key, duration_hours, "score")]
    effective_price = row[lens_metric_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh")]
    reduction_pct = row[lens_metric_column(profile_key, duration_hours, "annual_cost_reduction_pct")]
    profitable_day_share = row[lens_metric_column(profile_key, duration_hours, "profitable_day_share")]
    p95_reduction = row[lens_metric_column(profile_key, duration_hours, "p95_active_hour_reduction_pct")]

    return (
        f"**{row['location']}** ranks **#{rank}** for **{lens_label(profile_key, duration_hours)}**. "
        f"Effective average price is **${effective_price:.2f}/MWh**, annual cost reduction is "
        f"**{reduction_pct:.1f}%**, profitable-day share is **{profitable_day_share:.1f}%**, "
        f"and active-hour tail price reduction is **{p95_reduction:.1f}%**. "
        f"Best-fit lens across all screens: **{row['best_fit_lens']}**."
    )


__all__ = [
    "build_location_narrative",
    "build_reviewer_table",
    "build_selected_metric_table",
    "format_reviewer_table",
]
