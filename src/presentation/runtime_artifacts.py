"""Runtime artifact orchestration for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.config import AppSettings, SETTINGS


FetchFn = Callable[[int, bool, AppSettings, Any | None], Any]
BuildFn = Callable[[int, AppSettings], Any]


def required_dashboard_artifact_paths(
    year: int,
    settings: AppSettings = SETTINGS,
) -> tuple[Path, Path, Path]:
    return (
        settings.metrics_path(year),
        settings.daily_profile_windows_path(year),
        settings.hourly_profile_shape_path(year),
    )


def missing_dashboard_artifact_paths(
    year: int,
    settings: AppSettings = SETTINGS,
) -> tuple[Path, ...]:
    return tuple(path for path in required_dashboard_artifact_paths(year, settings) if not path.exists())


def ensure_dashboard_artifacts(
    year: int,
    settings: AppSettings = SETTINGS,
    fetch_fn: FetchFn | None = None,
    build_fn: BuildFn | None = None,
) -> tuple[Path, ...]:
    missing = missing_dashboard_artifact_paths(year, settings)
    if not missing:
        return ()

    if fetch_fn is None:
        from src.data.fetch import pull_and_validate_dam_data

        fetch_fn = pull_and_validate_dam_data

    if build_fn is None:
        from src.analytics.metrics import write_metric_artifacts

        build_fn = write_metric_artifacts

    processed_path = settings.processed_dam_path(year)
    if not processed_path.exists():
        fetch_fn(year, False, settings, None)

    build_fn(year, settings)
    remaining = missing_dashboard_artifact_paths(year, settings)
    if remaining:
        missing_list = ", ".join(str(path) for path in remaining)
        raise FileNotFoundError(f"Missing dashboard artifacts after attempted bootstrap: {missing_list}")

    return missing
