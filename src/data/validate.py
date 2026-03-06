from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd

from src.config import AppSettings, SETTINGS


@dataclass(frozen=True)
class ValidationIssue:
    location: str
    issue: str
    count: int


@dataclass(frozen=True)
class ValidationReport:
    row_count: int
    location_count: int
    expected_intervals_per_location: int
    duplicate_interval_count: int
    missing_interval_count: int
    start_utc: str
    end_utc: str
    issues: tuple[ValidationIssue, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


@dataclass(frozen=True)
class ValidatedDataset:
    frame: pd.DataFrame
    report: ValidationReport


def _require_columns(frame: pd.DataFrame, required_columns: Iterable[str]) -> None:
    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def _coerce_timezone_aware(series: pd.Series, column_name: str) -> pd.Series:
    if not pd.api.types.is_datetime64_any_dtype(series):
        series = pd.to_datetime(series, utc=False)
    if getattr(series.dt, "tz", None) is None:
        raise ValueError(f"Column '{column_name}' must be timezone-aware.")
    return series


def _build_expected_index(
    settings: AppSettings,
    expected_year: int | None,
    frame: pd.DataFrame,
) -> pd.DatetimeIndex:
    if expected_year is not None:
        market_start = pd.Timestamp(
            year=expected_year,
            month=1,
            day=1,
            hour=0,
            tz=settings.market_timezone,
        )
        market_end = pd.Timestamp(
            year=expected_year,
            month=12,
            day=31,
            hour=23,
            tz=settings.market_timezone,
        )
        market_index = pd.date_range(
            start=market_start,
            end=market_end,
            freq=f"{settings.expected_interval_minutes}min",
        )
        return market_index.tz_convert(settings.storage_timezone)

    start = frame["interval_start_utc"].min()
    end = frame["interval_start_utc"].max()
    return pd.date_range(start=start, end=end, freq=f"{settings.expected_interval_minutes}min")


def validate_and_normalize_dam_dataset(
    frame: pd.DataFrame,
    settings: AppSettings = SETTINGS,
    expected_year: int | None = None,
) -> ValidatedDataset:
    _require_columns(frame, settings.required_dam_columns)

    working_frame = frame.loc[:, list(settings.required_dam_columns)].copy()
    working_frame["Time"] = _coerce_timezone_aware(working_frame["Time"], "Time")
    working_frame["Interval Start"] = _coerce_timezone_aware(
        working_frame["Interval Start"],
        "Interval Start",
    )
    working_frame["Interval End"] = _coerce_timezone_aware(
        working_frame["Interval End"],
        "Interval End",
    )

    if not working_frame["Market"].eq(settings.market_name).all():
        unexpected_markets = sorted(working_frame["Market"].dropna().unique().tolist())
        raise ValueError(f"Unexpected market values: {unexpected_markets}")

    normalized_frame = pd.DataFrame(
        {
            "timestamp_utc": working_frame["Time"].dt.tz_convert(settings.storage_timezone),
            "interval_start_utc": working_frame["Interval Start"].dt.tz_convert(
                settings.storage_timezone,
            ),
            "interval_end_utc": working_frame["Interval End"].dt.tz_convert(
                settings.storage_timezone,
            ),
            "market_date": working_frame["Interval Start"]
            .dt.tz_convert(settings.market_timezone)
            .dt.date,
            "location": working_frame["Location"].astype("string"),
            "location_type": working_frame["Location Type"].astype("string"),
            "market": working_frame["Market"].astype("string"),
            "spp": working_frame["SPP"].astype("float64"),
        }
    )

    normalized_frame = normalized_frame.sort_values(
        by=["location", "interval_start_utc"],
    ).reset_index(drop=True)

    duplicate_mask = normalized_frame.duplicated(
        subset=["location", "interval_start_utc"],
        keep=False,
    )
    duplicate_count = int(duplicate_mask.sum())

    expected_index = _build_expected_index(settings, expected_year, normalized_frame)
    issues: list[ValidationIssue] = []
    missing_total = 0

    for location, location_frame in normalized_frame.groupby("location", sort=True):
        observed_index = pd.DatetimeIndex(location_frame["interval_start_utc"])
        missing_index = expected_index.difference(observed_index)
        if len(missing_index) > 0:
            missing_total += len(missing_index)
            issues.append(
                ValidationIssue(
                    location=str(location),
                    issue="missing_intervals",
                    count=len(missing_index),
                )
            )

    if duplicate_count > 0:
        duplicate_locations = (
            normalized_frame.loc[duplicate_mask, "location"].astype(str).unique().tolist()
        )
        for location in sorted(duplicate_locations):
            location_duplicates = normalized_frame.loc[
                duplicate_mask & normalized_frame["location"].eq(location)
            ]
            issues.append(
                ValidationIssue(
                    location=location,
                    issue="duplicate_intervals",
                    count=int(len(location_duplicates)),
                )
            )

    report = ValidationReport(
        row_count=int(len(normalized_frame)),
        location_count=int(normalized_frame["location"].nunique()),
        expected_intervals_per_location=int(len(expected_index)),
        duplicate_interval_count=duplicate_count,
        missing_interval_count=missing_total,
        start_utc=str(normalized_frame["interval_start_utc"].min()),
        end_utc=str(normalized_frame["interval_start_utc"].max()),
        issues=tuple(issues),
    )

    if report.duplicate_interval_count > 0 or report.missing_interval_count > 0:
        raise ValueError(report.to_json())

    return ValidatedDataset(frame=normalized_frame, report=report)
