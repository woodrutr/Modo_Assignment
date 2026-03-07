from __future__ import annotations

from datetime import date

import pandas as pd


def location_type_for(location: str) -> str:
    return "Trading Hub" if location.startswith("HB_") else "Load Zone"


def make_raw_frame(
    location_prices: dict[str, list[float]],
    start_local: str = "2025-01-06 00:00",
    timezone: str = "US/Central",
) -> pd.DataFrame:
    lengths = {len(values) for values in location_prices.values()}
    if len(lengths) != 1:
        raise ValueError("All location price vectors must have the same length.")
    periods = lengths.pop()
    timestamps = pd.date_range(start=start_local, periods=periods, freq="h", tz=timezone)
    rows: list[dict[str, object]] = []
    for timestamp in timestamps:
        for location, values in sorted(location_prices.items()):
            index = int((timestamp - timestamps[0]) / pd.Timedelta(hours=1))
            rows.append(
                {
                    "Time": timestamp,
                    "Interval Start": timestamp,
                    "Interval End": timestamp + pd.Timedelta(hours=1),
                    "Location": location,
                    "Location Type": location_type_for(location),
                    "Market": "DAY_AHEAD_HOURLY",
                    "SPP": float(values[index]),
                }
            )
    return pd.DataFrame(rows)


def make_processed_frame(
    location_prices: dict[str, list[float]],
    start_local: str = "2025-01-06 00:00",
    timezone: str = "US/Central",
) -> pd.DataFrame:
    raw = make_raw_frame(location_prices, start_local=start_local, timezone=timezone)
    interval_start_utc = pd.to_datetime(raw["Interval Start"], utc=True)
    return pd.DataFrame(
        {
            "timestamp_utc": pd.to_datetime(raw["Time"], utc=True),
            "interval_start_utc": interval_start_utc,
            "interval_end_utc": pd.to_datetime(raw["Interval End"], utc=True),
            "market_date": [value.date() if hasattr(value, "date") else value for value in raw["Interval Start"]],
            "location": raw["Location"].astype("string"),
            "location_type": raw["Location Type"].astype("string"),
            "market": raw["Market"].astype("string"),
            "spp": raw["SPP"].astype(float),
        }
    )
