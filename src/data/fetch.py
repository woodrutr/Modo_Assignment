from __future__ import annotations

import argparse

import pandas as pd

from src.config import AppSettings, SETTINGS
from src.data.validate import ValidatedDataset, validate_and_normalize_dam_dataset


def _ensure_parent_directories(settings: AppSettings) -> None:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)


def _download_dam_dataset(year: int) -> pd.DataFrame:
    try:
        from gridstatus import Ercot
    except ImportError as exc:
        raise RuntimeError(
            "gridstatus is required for data downloads. Install requirements.txt first.",
        ) from exc

    ercot_client = Ercot()
    return ercot_client.get_dam_spp(year)


def _load_or_download_year(
    year: int,
    force_download: bool,
    settings: AppSettings,
) -> tuple[pd.DataFrame, str]:
    raw_path = settings.raw_dam_path(year)
    if raw_path.exists() and not force_download:
        return pd.read_parquet(raw_path), "cache"

    raw_frame = _download_dam_dataset(year)
    raw_frame.to_parquet(raw_path, index=False)
    return raw_frame, "download"


def pull_and_validate_dam_data(
    force_download: bool,
    settings: AppSettings = SETTINGS,
) -> tuple[int, str, ValidatedDataset]:
    _ensure_parent_directories(settings)
    errors: list[str] = []

    for candidate_year in (settings.target_year, settings.fallback_year):
        try:
            raw_frame, source = _load_or_download_year(
                year=candidate_year,
                force_download=force_download,
                settings=settings,
            )
            validated = validate_and_normalize_dam_dataset(
                raw_frame,
                settings,
                expected_year=candidate_year,
            )
            validated.frame.to_parquet(
                settings.processed_dam_path(candidate_year),
                index=False,
            )
            settings.validation_report_path(candidate_year).write_text(
                validated.report.to_json(),
                encoding="utf-8",
            )
            return candidate_year, source, validated
        except Exception as exc:
            errors.append(f"{candidate_year}: {exc}")

    joined_errors = "\n".join(errors)
    raise RuntimeError(f"Unable to build ERCOT DAM dataset.\n{joined_errors}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and validate ERCOT DAM settlement point prices.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Bypass cached Parquet files and fetch from ERCOT again.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    year, source, validated = pull_and_validate_dam_data(
        force_download=args.force_download,
        settings=SETTINGS,
    )
    print(f"Resolved analysis year: {year}")
    print(f"Raw source: {source}")
    print(f"Rows: {validated.report.row_count}")
    print(f"Locations: {validated.report.location_count}")
    print(f"Raw parquet: {SETTINGS.raw_dam_path(year)}")
    print(f"Processed parquet: {SETTINGS.processed_dam_path(year)}")
    print(f"Validation report: {SETTINGS.validation_report_path(year)}")


if __name__ == "__main__":
    main()
