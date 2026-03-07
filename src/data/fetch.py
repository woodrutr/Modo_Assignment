"""Fetch, validate, and cache ERCOT DAM settlement-point data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd

from src.config import AppSettings, SETTINGS
from src.data.validate import ValidatedDataset, validate_and_normalize_dam_dataset, write_validation_report


class ErcotClient(Protocol):
    def get_dam_spp(self, year: int) -> pd.DataFrame:
        ...


@dataclass(frozen=True)
class FetchResult:
    year: int
    raw_path: Path
    processed_path: Path
    report_path: Path
    dataset: ValidatedDataset
    source: str


def _load_gridstatus_client() -> ErcotClient:
    import gridstatus  # lazy import keeps core modules light until fetch is invoked

    return gridstatus.Ercot()


def _ensure_parent_directories(settings: AppSettings) -> None:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)


def _download_dam_dataset(year: int, ercot_client: ErcotClient | None = None) -> pd.DataFrame:
    client = ercot_client or _load_gridstatus_client()
    return client.get_dam_spp(year)


def _candidate_years(requested_year: int, settings: AppSettings) -> tuple[int, ...]:
    if requested_year == settings.fallback_year:
        return (requested_year,)
    return (requested_year, settings.fallback_year)


def _read_or_download_raw_frame(
    year: int,
    force_download: bool,
    settings: AppSettings,
    ercot_client: ErcotClient | None,
) -> tuple[pd.DataFrame, Path, str]:
    raw_path = settings.raw_dam_path(year)
    if raw_path.exists() and not force_download:
        return pd.read_parquet(raw_path), raw_path, "cache"

    raw_frame = _download_dam_dataset(year, ercot_client=ercot_client)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_frame.to_parquet(raw_path, index=False)
    return raw_frame, raw_path, "download"


def pull_and_validate_dam_data(
    year: int | None = None,
    force_download: bool = False,
    settings: AppSettings = SETTINGS,
    ercot_client: ErcotClient | None = None,
) -> FetchResult:
    _ensure_parent_directories(settings)
    requested_year = year or settings.target_year
    last_error: Exception | None = None

    for candidate_year in _candidate_years(requested_year, settings):
        try:
            raw_frame, raw_path, source = _read_or_download_raw_frame(
                year=candidate_year,
                force_download=force_download,
                settings=settings,
                ercot_client=ercot_client,
            )
            dataset = validate_and_normalize_dam_dataset(
                raw_frame=raw_frame,
                settings=settings,
                expected_year=candidate_year,
            )
            processed_path = settings.processed_dam_path(candidate_year)
            report_path = settings.validation_report_path(candidate_year)
            dataset.frame.to_parquet(processed_path, index=False)
            write_validation_report(dataset.report, report_path)
            return FetchResult(
                year=candidate_year,
                raw_path=raw_path,
                processed_path=processed_path,
                report_path=report_path,
                dataset=dataset,
                source=source,
            )
        except Exception as error:  # noqa: BLE001 - fallback behavior is explicit
            last_error = error
            if candidate_year == requested_year and candidate_year != settings.fallback_year:
                continue
            raise

    assert last_error is not None
    raise last_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=SETTINGS.target_year)
    parser.add_argument("--force-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = pull_and_validate_dam_data(year=args.year, force_download=args.force_download)
    rows = len(result.dataset.frame)
    locations = result.dataset.frame["location"].nunique()
    print(
        f"Validated ERCOT DAM data for {result.year}: {rows} rows across {locations} locations "
        f"({result.source})."
    )
    print(f"Raw parquet: {result.raw_path}")
    print(f"Processed parquet: {result.processed_path}")
    print(f"Validation report: {result.report_path}")


if __name__ == "__main__":
    main()
