"""Pure functions for annual large-load flexibility diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    AppSettings,
    DURATION_OPTIONS,
    MONTH_ORDER,
    PROFILE_ORDER,
    SETTINGS,
    get_profile,
)


@dataclass(frozen=True)
class DispatchWindow:
    charge_start_hour: int | None
    charge_start_ordinal: int | None
    discharge_start_hour: int | None
    discharge_start_ordinal: int | None
    charge_avg_price_usd_per_mwh: float | None
    discharge_avg_price_usd_per_mwh: float | None
    best_spread_usd_per_mwh: float | None
    net_value_usd_per_mw_day: float
    profitable: bool


def derive_local_time_features(
    processed: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    local_timestamp = processed["interval_start_utc"].dt.tz_convert(settings.market_timezone)
    out = processed.copy()
    out = out.assign(
        local_timestamp=local_timestamp,
        local_date=local_timestamp.dt.date,
        local_hour=local_timestamp.dt.hour.astype(int),
        local_month=local_timestamp.dt.month.astype(int),
        local_month_label=pd.Categorical.from_codes(
            local_timestamp.dt.month.to_numpy() - 1,
            categories=list(MONTH_ORDER),
            ordered=True,
        ),
        is_weekday=(local_timestamp.dt.dayofweek < 5),
    )
    out = out.sort_values(["location", "interval_start_utc"], kind="mergesort").reset_index(drop=True)
    out = out.assign(
        hour_ordinal_in_day=out.groupby(["location", "local_date"], sort=False).cumcount().astype(int)
    )
    return out


def _candidate_windows(
    day_frame: pd.DataFrame,
    allowed_mask: pd.Series,
    duration_hours: int,
) -> list[tuple[int, np.ndarray]]:
    windows: list[tuple[int, np.ndarray]] = []
    mask = allowed_mask.to_numpy(dtype=bool)
    if len(day_frame) < duration_hours:
        return windows

    for start in range(0, len(day_frame) - duration_hours + 1):
        positions = np.arange(start, start + duration_hours)
        if mask[positions].all():
            windows.append((start, positions))
    return windows


def _select_best_dispatch_window(
    day_frame: pd.DataFrame,
    profile_key: str,
    duration_hours: int,
    settings: AppSettings,
) -> DispatchWindow:
    profile = get_profile(profile_key)  # type: ignore[arg-type]
    is_weekday = bool(day_frame["is_weekday"].iloc[0])

    active_mask = day_frame["local_hour"].isin(profile.active_hours)
    if profile.weekdays_only:
        active_mask = active_mask & day_frame["is_weekday"]

    charge_mask = day_frame["local_hour"].isin(profile.charge_hours)
    if profile.weekdays_only:
        charge_mask = charge_mask & day_frame["is_weekday"]

    discharge_windows = _candidate_windows(day_frame, active_mask, duration_hours)
    charge_windows = _candidate_windows(day_frame, charge_mask, duration_hours)
    prices = day_frame["spp"].to_numpy(dtype=float)

    if (profile.weekdays_only and not is_weekday) or not discharge_windows or not charge_windows:
        return DispatchWindow(
            charge_start_hour=None,
            charge_start_ordinal=None,
            discharge_start_hour=None,
            discharge_start_ordinal=None,
            charge_avg_price_usd_per_mwh=None,
            discharge_avg_price_usd_per_mwh=None,
            best_spread_usd_per_mwh=None,
            net_value_usd_per_mw_day=0.0,
            profitable=False,
        )

    battery_power_mw = (
        settings.flex_battery.load_mw * settings.flex_battery.battery_power_mw_per_mw_load
    )
    round_trip_efficiency = settings.flex_battery.round_trip_efficiency

    best_raw_value = float("-inf")
    best_window: DispatchWindow | None = None

    for charge_start_ordinal, charge_positions in charge_windows:
        charge_end_ordinal = int(charge_positions[-1])
        charge_avg_price = float(prices[charge_positions].mean())
        charge_start_hour = int(day_frame.iloc[charge_start_ordinal]["local_hour"])

        for discharge_start_ordinal, discharge_positions in discharge_windows:
            if charge_end_ordinal >= discharge_start_ordinal:
                continue

            discharge_avg_price = float(prices[discharge_positions].mean())
            spread = (round_trip_efficiency * discharge_avg_price) - charge_avg_price
            raw_value = float(duration_hours * battery_power_mw * spread)

            if raw_value > best_raw_value:
                best_raw_value = raw_value
                best_window = DispatchWindow(
                    charge_start_hour=charge_start_hour,
                    charge_start_ordinal=int(charge_start_ordinal),
                    discharge_start_hour=int(day_frame.iloc[discharge_start_ordinal]["local_hour"]),
                    discharge_start_ordinal=int(discharge_start_ordinal),
                    charge_avg_price_usd_per_mwh=charge_avg_price,
                    discharge_avg_price_usd_per_mwh=discharge_avg_price,
                    best_spread_usd_per_mwh=float(spread),
                    net_value_usd_per_mw_day=max(raw_value, 0.0),
                    profitable=raw_value > 0.0,
                )

    if best_window is None:
        return DispatchWindow(
            charge_start_hour=None,
            charge_start_ordinal=None,
            discharge_start_hour=None,
            discharge_start_ordinal=None,
            charge_avg_price_usd_per_mwh=None,
            discharge_avg_price_usd_per_mwh=None,
            best_spread_usd_per_mwh=None,
            net_value_usd_per_mw_day=0.0,
            profitable=False,
        )

    return best_window


def build_daily_profile_windows(
    processed: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    local_frame = derive_local_time_features(processed, settings=settings)
    rows: list[dict[str, Any]] = []

    for (location, location_type, local_date), day_frame in local_frame.groupby(
        ["location", "location_type", "local_date"],
        sort=True,
    ):
        day_frame = day_frame.reset_index(drop=True)
        local_month = int(day_frame["local_month"].iloc[0])
        local_month_label = str(day_frame["local_month_label"].iloc[0])
        is_weekday = bool(day_frame["is_weekday"].iloc[0])

        for profile_key in PROFILE_ORDER:
            profile = get_profile(profile_key)  # type: ignore[arg-type]
            active_mask = day_frame["local_hour"].isin(profile.active_hours)
            if profile.weekdays_only:
                active_mask = active_mask & day_frame["is_weekday"]

            baseline_daily_cost = float(day_frame.loc[active_mask, "spp"].sum())
            active_load_mwh = float(active_mask.sum())

            row: dict[str, Any] = {
                "location": str(location),
                "location_type": str(location_type),
                "profile": profile_key,
                "local_date": local_date,
                "local_month": local_month,
                "local_month_label": local_month_label,
                "is_weekday": is_weekday,
                "active_hours_count": int(active_mask.sum()),
                "active_load_mwh": active_load_mwh,
                "baseline_daily_cost_usd_per_mw_day": baseline_daily_cost,
            }

            for duration_hours in DURATION_OPTIONS:
                prefix = f"{duration_hours}h"
                dispatch = _select_best_dispatch_window(
                    day_frame=day_frame,
                    profile_key=profile_key,
                    duration_hours=duration_hours,
                    settings=settings,
                )
                row[f"{prefix}_charge_start_hour"] = dispatch.charge_start_hour
                row[f"{prefix}_charge_start_ordinal"] = dispatch.charge_start_ordinal
                row[f"{prefix}_discharge_start_hour"] = dispatch.discharge_start_hour
                row[f"{prefix}_discharge_start_ordinal"] = dispatch.discharge_start_ordinal
                row[f"{prefix}_charge_avg_price_usd_per_mwh"] = dispatch.charge_avg_price_usd_per_mwh
                row[f"{prefix}_discharge_avg_price_usd_per_mwh"] = (
                    dispatch.discharge_avg_price_usd_per_mwh
                )
                row[f"{prefix}_best_spread_usd_per_mwh"] = dispatch.best_spread_usd_per_mwh
                row[f"{prefix}_profitable"] = bool(dispatch.profitable)
                row[f"{prefix}_net_value_usd_per_mw_day"] = float(dispatch.net_value_usd_per_mw_day)
                row[f"{prefix}_effective_daily_cost_usd_per_mw_day"] = float(
                    baseline_daily_cost - dispatch.net_value_usd_per_mw_day
                )

            rows.append(row)

    return pd.DataFrame(rows).sort_values(["profile", "location", "local_date"]).reset_index(drop=True)


def build_hourly_profile_dispatch_frame(
    processed: pd.DataFrame,
    daily_windows: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    base = derive_local_time_features(processed, settings=settings)
    frames: list[pd.DataFrame] = []
    round_trip_efficiency = settings.flex_battery.round_trip_efficiency

    for profile_key in PROFILE_ORDER:
        profile = get_profile(profile_key)  # type: ignore[arg-type]
        profile_base = base.copy()
        if profile.weekdays_only:
            profile_base = profile_base.loc[profile_base["is_weekday"]].copy()

        profile_base = profile_base.assign(
            profile=profile_key,
            active_hour_flag=profile_base["local_hour"].isin(profile.active_hours),
        )
        window_slice = daily_windows.loc[
            daily_windows["profile"].eq(profile_key),
            :,
        ]

        for duration_hours in DURATION_OPTIONS:
            prefix = f"{duration_hours}h"
            join_columns = [
                "location",
                "profile",
                "local_date",
                f"{prefix}_charge_start_ordinal",
                f"{prefix}_discharge_start_ordinal",
                f"{prefix}_profitable",
            ]
            merged = profile_base.merge(
                window_slice[join_columns],
                on=["location", "profile", "local_date"],
                how="left",
                validate="many_to_one",
            )
            profitable = merged[f"{prefix}_profitable"].fillna(False)
            charge_start = merged[f"{prefix}_charge_start_ordinal"]
            discharge_start = merged[f"{prefix}_discharge_start_ordinal"]
            ordinals = merged["hour_ordinal_in_day"]

            selected_charge = (
                profitable
                & charge_start.notna()
                & ordinals.ge(charge_start)
                & ordinals.lt(charge_start + duration_hours)
            )
            selected_discharge = (
                profitable
                & discharge_start.notna()
                & ordinals.ge(discharge_start)
                & ordinals.lt(discharge_start + duration_hours)
            )

            effective_active_price = np.where(
                merged["active_hour_flag"],
                merged["spp"],
                np.nan,
            )
            effective_active_price = np.where(
                selected_discharge,
                (1.0 - round_trip_efficiency) * merged["spp"],
                effective_active_price,
            )

            frames.append(
                merged.assign(
                    duration_hours=duration_hours,
                    market_price_usd_per_mwh=merged["spp"].astype(float),
                    selected_charge_hour_flag=selected_charge.astype(bool),
                    selected_discharge_hour_flag=selected_discharge.astype(bool),
                    effective_active_price_usd_per_mwh=effective_active_price.astype(float),
                )[
                    [
                        "location",
                        "location_type",
                        "profile",
                        "duration_hours",
                        "interval_start_utc",
                        "local_date",
                        "local_month",
                        "local_month_label",
                        "local_hour",
                        "hour_ordinal_in_day",
                        "is_weekday",
                        "active_hour_flag",
                        "selected_charge_hour_flag",
                        "selected_discharge_hour_flag",
                        "market_price_usd_per_mwh",
                        "effective_active_price_usd_per_mwh",
                    ]
                ]
            )

    return pd.concat(frames, ignore_index=True)


def build_hourly_profile_shape_artifact(hourly_dispatch: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        hourly_dispatch.groupby(
            [
                "location",
                "location_type",
                "profile",
                "duration_hours",
                "local_month",
                "local_month_label",
                "local_hour",
            ],
            as_index=False,
            sort=True,
            observed=True,
        )
        .agg(
            market_price_avg_usd_per_mwh=("market_price_usd_per_mwh", "mean"),
            effective_active_price_avg_usd_per_mwh=("effective_active_price_usd_per_mwh", "mean"),
            observation_count=("market_price_usd_per_mwh", "size"),
            active_observation_count=("active_hour_flag", "sum"),
            charge_observation_count=("selected_charge_hour_flag", "sum"),
            discharge_observation_count=("selected_discharge_hour_flag", "sum"),
        )
    )
    grouped["active_hour_flag"] = grouped["active_observation_count"].gt(0)
    return grouped.sort_values(
        ["profile", "duration_hours", "location", "local_month", "local_hour"],
        kind="mergesort",
    ).reset_index(drop=True)


__all__ = [
    "DispatchWindow",
    "build_daily_profile_windows",
    "build_hourly_profile_dispatch_frame",
    "build_hourly_profile_shape_artifact",
    "derive_local_time_features",
]
