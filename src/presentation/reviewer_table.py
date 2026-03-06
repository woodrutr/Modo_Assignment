from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from src.config import AppSettings, SETTINGS


def build_raw_metric_table(metrics: pd.DataFrame, battery: pd.DataFrame) -> pd.DataFrame:
    display_columns = [
        "rank",
        "location",
        "location_type",
        "battery_opportunity_score",
        "avg_price",
        "std_price",
        "pct_negative",
        "pct_below_20",
        "pct_above_100",
        "avg_daily_spread",
        "annual_battery_gross_margin_usd",
        "pct_positive_value_days",
    ]
    return (
        metrics.merge(battery, on="location", how="left", validate="one_to_one")
        .loc[:, display_columns]
        .sort_values(by="rank")
        .reset_index(drop=True)
    )


def _anchor_frame(settings: AppSettings) -> pd.DataFrame:
    return pd.DataFrame([asdict(anchor) for anchor in settings.location_anchors])


def _display_name(row: pd.Series) -> str:
    if row["location"] == "HB_BUSAVG":
        return "ERCOT Bus Average"
    if row["location"] == "HB_HUBAVG":
        return "ERCOT Hub Average"
    suffix = "Hub" if row["location_type"] == "Trading Hub" else "Load Zone"
    return f"{row['anchor_name']} {suffix}"


def _classify_metric(value: float, low: float, high: float) -> str:
    if value >= high:
        return "strong"
    if value <= low:
        return "weak"
    return "moderate"


def _build_readout(row: pd.Series, quantiles: dict[str, tuple[float, float]]) -> str:
    charge_view = _classify_metric(
        float(row["pct_below_20"]),
        quantiles["pct_below_20"][0],
        quantiles["pct_below_20"][1],
    )
    spike_view = _classify_metric(
        float(row["pct_above_100"]),
        quantiles["pct_above_100"][0],
        quantiles["pct_above_100"][1],
    )
    spread_view = _classify_metric(
        float(row["avg_daily_spread"]),
        quantiles["avg_daily_spread"][0],
        quantiles["avg_daily_spread"][1],
    )
    return (
        f"{charge_view.capitalize()} charging windows, "
        f"{spike_view} spike profile, "
        f"{spread_view} daily spreads"
    )


def build_reviewer_table(
    metrics: pd.DataFrame,
    battery: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    merged = build_raw_metric_table(metrics, battery).merge(
        _anchor_frame(settings).loc[:, ["location", "anchor_name"]],
        on="location",
        how="left",
        validate="one_to_one",
    )

    quantiles = {
        "pct_below_20": tuple(merged["pct_below_20"].quantile([0.33, 0.67]).tolist()),
        "pct_above_100": tuple(merged["pct_above_100"].quantile([0.33, 0.67]).tolist()),
        "avg_daily_spread": tuple(merged["avg_daily_spread"].quantile([0.33, 0.67]).tolist()),
    }

    reviewer = pd.DataFrame(
        {
            "Rank": merged["rank"],
            "Location": merged.apply(_display_name, axis=1),
            "Code": merged["location"],
            "Score": merged["battery_opportunity_score"],
            "Cheap Hours (%)": merged["pct_below_20"],
            "Spike Hours (%)": merged["pct_above_100"],
            "Daily Spread ($/MWh)": merged["avg_daily_spread"],
            "Est. Battery Value ($/yr)": merged["annual_battery_gross_margin_usd"],
            "Readout": merged.apply(_build_readout, axis=1, quantiles=quantiles),
        }
    )
    return reviewer.sort_values(by="Rank").reset_index(drop=True)


def build_location_story(raw_row: pd.Series) -> str:
    score = float(raw_row["battery_opportunity_score"])
    cheap_hours = float(raw_row["pct_below_20"])
    spike_hours = float(raw_row["pct_above_100"])
    spread = float(raw_row["avg_daily_spread"])
    annual_value = float(raw_row["annual_battery_gross_margin_usd"])

    if score >= 50:
        lead = "This is one of the strongest screening candidates in the ERCOT set."
    elif score >= 25:
        lead = "This looks like a middle-of-the-pack screening candidate."
    else:
        lead = "This screens as a weaker relative candidate in the ERCOT set."

    return (
        f"{lead} It shows {cheap_hours:.1f}% of hours below $20/MWh, "
        f"{spike_hours:.1f}% of hours above $100/MWh, and an average daily spread "
        f"of ${spread:.1f}/MWh. Under the stylized battery heuristic, that translates "
        f"to roughly ${annual_value:,.0f} per year of gross arbitrage value."
    )
