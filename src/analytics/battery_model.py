from __future__ import annotations

import pandas as pd

from src.config import AppSettings, SETTINGS


def _require_battery_columns(frame: pd.DataFrame) -> None:
    required_columns = {"location", "market_date", "spp"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns for battery model: {sorted(missing_columns)}")


def compute_daily_battery_value(
    frame: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    _require_battery_columns(frame)

    results: list[dict[str, object]] = []
    charge_hours = settings.battery.charge_hours_per_day
    discharge_hours = settings.battery.discharge_hours_per_day
    charge_mwh_per_hour = settings.battery.charge_mwh_per_hour
    discharge_mwh_per_hour = charge_mwh_per_hour * settings.battery.round_trip_efficiency

    for (location, market_date), group in frame.groupby(["location", "market_date"], sort=True):
        sorted_group = group.sort_values(by="spp", ascending=True)
        cheapest_hours = sorted_group.head(charge_hours)
        richest_hours = sorted_group.tail(discharge_hours)

        charge_cost = float(cheapest_hours["spp"].sum() * charge_mwh_per_hour)
        discharge_value = float(richest_hours["spp"].sum() * discharge_mwh_per_hour)
        net_value = discharge_value - charge_cost

        results.append(
            {
                "location": str(location),
                "market_date": market_date,
                "charge_cost_usd": charge_cost,
                "discharge_value_usd": discharge_value,
                "net_value_usd": net_value,
            }
        )

    return pd.DataFrame(results).sort_values(by=["location", "market_date"]).reset_index(drop=True)


def summarize_battery_value(
    frame: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    daily_value = compute_daily_battery_value(frame, settings)
    summary = (
        daily_value.groupby("location", sort=True)
        .agg(
            annual_battery_gross_margin_usd=("net_value_usd", "sum"),
            average_daily_battery_value_usd=("net_value_usd", "mean"),
            positive_value_days=("net_value_usd", lambda series: int((series > 0).sum())),
            days_modeled=("net_value_usd", "count"),
        )
        .reset_index()
    )
    summary["pct_positive_value_days"] = (
        summary["positive_value_days"] / summary["days_modeled"] * 100.0
    )
    return summary.sort_values(by="annual_battery_gross_margin_usd", ascending=False).reset_index(
        drop=True,
    )
