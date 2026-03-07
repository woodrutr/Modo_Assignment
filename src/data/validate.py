"""Validation and normalization for ERCOT DAM settlement-point data."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import AppSettings, SETTINGS


@dataclass(frozen=True)
class ValidationIssue:
    category: str
    message: str
    location: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationReport:
    year: int | None
    row_count: int
    location_count: int
    rows_per_location: dict[str, int]
    start_interval_utc: str
    end_interval_utc: str
    issues: tuple[ValidationIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "row_count": self.row_count,
            "location_count": self.location_count,
            "rows_per_location": self.rows_per_location,
            "start_interval_utc": self.start_interval_utc,
            "end_interval_utc": self.end_interval_utc,
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True)
class ValidatedDataset:
    frame: pd.DataFrame
    report: ValidationReport


def _require_columns(frame: pd.DataFrame, settings: AppSettings) -> None:
    missing = [column for column in settings.required_dam_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required DAM columns: {missing}")


def _to_utc_timestamp(series: pd.Series, column_name: str) -> pd.Series:
    if not isinstance(series.dtype, pd.DatetimeTZDtype):
        raise ValueError(f"Column '{column_name}' must be timezone-aware.")
    return pd.to_datetime(series, utc=True)


def _build_processed_frame(raw_frame: pd.DataFrame, settings: AppSettings) -> pd.DataFrame:
    _require_columns(raw_frame, settings)

    markets = raw_frame["Market"].astype("string")
    invalid_market = markets.ne(settings.market_name)
    if invalid_market.any():
        invalid = sorted(markets[invalid_market].dropna().unique().tolist())
        raise ValueError(f"Unexpected market values: {invalid}")

    processed = pd.DataFrame(
        {
            "timestamp_utc": _to_utc_timestamp(raw_frame["Time"], "Time"),
            "interval_start_utc": _to_utc_timestamp(raw_frame["Interval Start"], "Interval Start"),
            "interval_end_utc": _to_utc_timestamp(raw_frame["Interval End"], "Interval End"),
            "location": raw_frame["Location"].astype("string"),
            "location_type": raw_frame["Location Type"].astype("string"),
            "market": markets,
            "spp": pd.to_numeric(raw_frame["SPP"], errors="raise").astype(float),
        }
    )

    local_dates = processed["interval_start_utc"].dt.tz_convert(settings.market_timezone).dt.date
    processed = processed.assign(market_date=local_dates)

    interval_delta = processed["interval_end_utc"] - processed["interval_start_utc"]
    expected_delta = pd.Timedelta(minutes=settings.expected_interval_minutes)
    if not interval_delta.eq(expected_delta).all():
        raise ValueError("Interval widths do not match the expected hourly cadence.")

    processed = processed.loc[
        :,
        [
            "timestamp_utc",
            "interval_start_utc",
            "interval_end_utc",
            "market_date",
            "location",
            "location_type",
            "market",
            "spp",
        ],
    ].sort_values(["location", "interval_start_utc"], kind="mergesort")

    return processed.reset_index(drop=True)


def _validate_interval_integrity(processed: pd.DataFrame, settings: AppSettings) -> tuple[ValidationIssue, ...]:
    expected_delta = pd.Timedelta(minutes=settings.expected_interval_minutes)
    issues: list[ValidationIssue] = []
    reference_index: pd.Index | None = None

    for location, location_frame in processed.groupby("location", sort=True):
        intervals = location_frame["interval_start_utc"]
        duplicate_mask = intervals.duplicated(keep=False)
        if duplicate_mask.any():
            duplicates = intervals[duplicate_mask].astype(str).tolist()
            issues.append(
                ValidationIssue(
                    category="duplicate_intervals",
                    message="Duplicate interval_start_utc values detected.",
                    location=str(location),
                    details={"duplicates": duplicates[:10]},
                )
            )
            continue

        contiguous = intervals.diff().dropna()
        if not contiguous.eq(expected_delta).all():
            bad_positions = contiguous[~contiguous.eq(expected_delta)].index.tolist()[:10]
            issues.append(
                ValidationIssue(
                    category="missing_intervals",
                    message="Non-hourly gap detected in interval_start_utc sequence.",
                    location=str(location),
                    details={"example_row_indices": bad_positions},
                )
            )

        if reference_index is None:
            reference_index = pd.Index(intervals)
            continue

        current_index = pd.Index(intervals)
        if not current_index.equals(reference_index):
            missing = reference_index.difference(current_index).astype(str).tolist()[:10]
            extra = current_index.difference(reference_index).astype(str).tolist()[:10]
            issues.append(
                ValidationIssue(
                    category="misaligned_intervals",
                    message="Location interval index does not align with the reference location index.",
                    location=str(location),
                    details={"missing_vs_reference": missing, "extra_vs_reference": extra},
                )
            )

    return tuple(issues)


def validate_and_normalize_dam_dataset(
    raw_frame: pd.DataFrame,
    settings: AppSettings = SETTINGS,
    expected_year: int | None = None,
) -> ValidatedDataset:
    processed = _build_processed_frame(raw_frame, settings)

    if expected_year is not None:
        years = sorted({value.year for value in processed["market_date"].tolist()})
        if years != [expected_year]:
            raise ValueError(f"Expected market_date year {expected_year}, found {years}.")

    issues = _validate_interval_integrity(processed, settings)
    if issues:
        issue_messages = "; ".join(
            f"{issue.category}:{issue.location or 'global'}:{issue.message}"
            for issue in issues
        )
        raise ValueError(f"Validation failed: {issue_messages}")

    rows_per_location = (
        processed.groupby("location", sort=True).size().astype(int).to_dict()
    )
    report = ValidationReport(
        year=expected_year,
        row_count=int(len(processed)),
        location_count=int(processed["location"].nunique()),
        rows_per_location={str(key): int(value) for key, value in rows_per_location.items()},
        start_interval_utc=processed["interval_start_utc"].min().isoformat(),
        end_interval_utc=processed["interval_start_utc"].max().isoformat(),
        issues=issues,
    )
    return ValidatedDataset(frame=processed, report=report)


def write_validation_report(report: ValidationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True))


__all__ = [
    "ValidatedDataset",
    "ValidationIssue",
    "ValidationReport",
    "validate_and_normalize_dam_dataset",
    "write_validation_report",
]
