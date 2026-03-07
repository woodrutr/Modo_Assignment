"""Human-readable reviewer table and narrative summary helpers.

This module sits strictly in the presentation layer. It transforms raw metric
DataFrames into display-friendly tables and short qualitative narrative strings.
No business logic or I/O lives here.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


# ── Column mapping for the reviewer-friendly view ────────────────────────────

_REVIEWER_COLUMNS = {
    "rank": "#",
    "location": "Location",
    "location_type": "Type",
    "battery_opportunity_score": "Opportunity Score",
    "avg_price": "Avg Price ($/MWh)",
    "avg_daily_spread": "Avg Daily Spread ($/MWh)",
    "pct_negative": "Negative Hours (%)",
    "pct_below_20": "Hours < $20 (%)",
    "pct_above_100": "Hours > $100 (%)",
}

_REVIEWER_COLUMN_ORDER = list(_REVIEWER_COLUMNS.keys())

_FORMAT_MAP = {
    "Opportunity Score": "{:.1f}",
    "Avg Price ($/MWh)": "${:.2f}",
    "Avg Daily Spread ($/MWh)": "${:.2f}",
    "Negative Hours (%)": "{:.1f}%",
    "Hours < $20 (%)": "{:.1f}%",
    "Hours > $100 (%)": "{:.2f}%",
}

_RAW_METRIC_LABELS = {
    "location": "Location Code",
    "location_type": "Location Type",
    "rank": "Rank",
    "observations": "Observations",
    "avg_price": "Average DAM Price ($/MWh)",
    "std_price": "Price Volatility Std Dev ($/MWh)",
    "pct_negative": "Negative Hours (%)",
    "pct_below_20": "Hours Below $20 (%)",
    "pct_above_100": "Hours Above $100 (%)",
    "avg_daily_spread": "Average Daily Spread ($/MWh)",
    "battery_opportunity_score": "Battery Opportunity Score",
    "annual_battery_gross_margin_usd": "Annual Battery Gross Margin ($)",
    "average_daily_battery_value_usd": "Average Daily Battery Value ($)",
    "positive_value_days": "Positive-Value Days",
    "days_modeled": "Days Modeled",
    "pct_positive_value_days": "Positive-Value Days (%)",
    "norm_pct_negative": "Normalized Negative Hours Score",
    "norm_pct_below_20": "Normalized Cheap-Hour Score",
    "norm_avg_daily_spread": "Normalized Daily Spread Score",
    "norm_pct_above_100": "Normalized Spike-Hour Score",
}

_RAW_METRIC_ORDER = [
    "location",
    "location_type",
    "rank",
    "observations",
    "avg_price",
    "std_price",
    "pct_negative",
    "pct_below_20",
    "pct_above_100",
    "avg_daily_spread",
    "battery_opportunity_score",
    "annual_battery_gross_margin_usd",
    "average_daily_battery_value_usd",
    "positive_value_days",
    "days_modeled",
    "pct_positive_value_days",
    "norm_pct_negative",
    "norm_pct_below_20",
    "norm_avg_daily_spread",
    "norm_pct_above_100",
]


def build_reviewer_table(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return a narrow, human-labelled copy of the metrics table."""
    available = [c for c in _REVIEWER_COLUMN_ORDER if c in metrics.columns]
    df = metrics[available].copy()
    df = df.rename(columns=_REVIEWER_COLUMNS)
    return df.reset_index(drop=True)


def format_reviewer_table(df: pd.DataFrame) -> pd.DataFrame:
    """Apply display formatting to a reviewer table (returns string-typed copy)."""
    out = df.copy()
    for col, fmt in _FORMAT_MAP.items():
        if col in out.columns:
            out[col] = out[col].apply(lambda v, f=fmt: f.format(v) if pd.notna(v) else "—")
    return out


def _format_raw_metric_value(metric_key: str, value: object) -> str:
    if pd.isna(value):
        return "—"

    if metric_key in {"avg_price", "std_price", "avg_daily_spread"}:
        return f"${float(value):.2f}"
    if metric_key in {
        "pct_negative",
        "pct_below_20",
        "pct_above_100",
        "pct_positive_value_days",
    }:
        return f"{float(value):.2f}%"
    if metric_key in {
        "annual_battery_gross_margin_usd",
        "average_daily_battery_value_usd",
    }:
        return f"${float(value):,.2f}"
    if metric_key in {"battery_opportunity_score"}:
        return f"{float(value):.2f}"
    if metric_key in {"rank", "observations", "positive_value_days", "days_modeled"}:
        return f"{int(value):,}"
    if metric_key.startswith("norm_"):
        return f"{float(value):.4f}"
    return str(value)


def build_selected_metric_table(
    row: pd.Series,
    battery_row: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Return a long-form key/value table for the selected location."""
    combined: dict[str, object] = row.to_dict()
    if battery_row is not None:
        for key, value in battery_row.to_dict().items():
            combined[key] = value

    ordered_keys = [key for key in _RAW_METRIC_ORDER if key in combined]
    remaining_keys = sorted(key for key in combined if key not in ordered_keys)
    display_keys = ordered_keys + remaining_keys

    return pd.DataFrame(
        {
            "Metric": [_RAW_METRIC_LABELS.get(key, key) for key in display_keys],
            "Value": [_format_raw_metric_value(key, combined[key]) for key in display_keys],
        }
    )


# ── Location narrative summary ───────────────────────────────────────────────

def _price_level_label(avg_price: float) -> str:
    if avg_price < 25:
        return "low"
    if avg_price < 40:
        return "moderate"
    return "elevated"


def _volatility_label(std_price: float) -> str:
    if std_price < 25:
        return "low"
    if std_price < 35:
        return "moderate"
    return "high"


def _opportunity_label(score: float) -> str:
    if score >= 55:
        return "Strong"
    if score >= 35:
        return "Moderate"
    if score >= 18:
        return "Limited"
    return "Weak"


def build_location_narrative(
    row: pd.Series,
    battery_row: Optional[pd.Series] = None,
) -> str:
    """Return a short qualitative summary for a single location."""
    loc = row["location"]
    score = row["battery_opportunity_score"]
    rank = int(row["rank"])
    total = 15  # known location count

    lines = [
        f"**{loc}** ranks **#{rank} of {total}** with an opportunity score "
        f"of **{score:.1f}/100** ({_opportunity_label(score).lower()} signal).",
        "",
        f"Average DAM price is {_price_level_label(row['avg_price'])} "
        f"at **${row['avg_price']:.2f}/MWh** with "
        f"{_volatility_label(row['std_price'])} volatility "
        f"(σ = ${row['std_price']:.1f}).",
        "",
        f"Negative-price hours: **{row['pct_negative']:.1f}%** · "
        f"Hours below $20: **{row['pct_below_20']:.1f}%** · "
        f"Hours above $100: **{row['pct_above_100']:.2f}%**",
        "",
        f"Average daily spread: **${row['avg_daily_spread']:.1f}/MWh**",
    ]

    if battery_row is not None:
        margin = battery_row["annual_battery_gross_margin_usd"]
        lines.append("")
        lines.append(
            f"Stylized battery gross margin: **${margin:,.0f}/yr** "
            f"(100 MW · 4h charge/discharge · 85% RTE)"
        )

    return "\n".join(lines)


__all__ = [
    "build_reviewer_table",
    "format_reviewer_table",
    "build_location_narrative",
    "build_selected_metric_table",
]
