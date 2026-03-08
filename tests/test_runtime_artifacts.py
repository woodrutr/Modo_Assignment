from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from src.config import SETTINGS
from src.presentation.runtime_artifacts import ensure_dashboard_artifacts


class RuntimeArtifactsTests(unittest.TestCase):
    def test_existing_artifacts_do_not_trigger_fetch_or_build(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = self._make_settings(Path(temp_dir))
            self._touch_required_artifacts(settings)
            calls: list[str] = []

            def fetch_fn(year: int, force_download: bool, settings_arg, ercot_client) -> None:
                calls.append(f"fetch:{year}")

            def build_fn(year: int, settings_arg) -> None:
                calls.append(f"build:{year}")

            created = ensure_dashboard_artifacts(
                year=2025,
                settings=settings,
                fetch_fn=fetch_fn,
                build_fn=build_fn,
            )

            self.assertEqual(created, ())
            self.assertEqual(calls, [])

    def test_missing_metrics_with_processed_path_only_triggers_build(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = self._make_settings(Path(temp_dir))
            settings.processed_dir.mkdir(parents=True, exist_ok=True)
            settings.processed_dam_path(2025).write_text("processed")
            calls: list[str] = []

            def fetch_fn(year: int, force_download: bool, settings_arg, ercot_client) -> None:
                calls.append(f"fetch:{year}")

            def build_fn(year: int, settings_arg) -> None:
                calls.append(f"build:{year}")
                self._touch_required_artifacts(settings_arg)

            created = ensure_dashboard_artifacts(
                year=2025,
                settings=settings,
                fetch_fn=fetch_fn,
                build_fn=build_fn,
            )

            self.assertEqual(len(created), 3)
            self.assertEqual(calls, ["build:2025"])

    def test_missing_processed_triggers_fetch_then_build(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = self._make_settings(Path(temp_dir))
            calls: list[str] = []

            def fetch_fn(year: int, force_download: bool, settings_arg, ercot_client) -> None:
                calls.append(f"fetch:{year}")
                settings_arg.processed_dir.mkdir(parents=True, exist_ok=True)
                settings_arg.processed_dam_path(year).write_text("processed")

            def build_fn(year: int, settings_arg) -> None:
                calls.append(f"build:{year}")
                self._touch_required_artifacts(settings_arg)

            created = ensure_dashboard_artifacts(
                year=2025,
                settings=settings,
                fetch_fn=fetch_fn,
                build_fn=build_fn,
            )

            self.assertEqual(len(created), 3)
            self.assertEqual(calls, ["fetch:2025", "build:2025"])

    def test_missing_artifacts_after_build_raise_hard_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = self._make_settings(Path(temp_dir))

            def fetch_fn(year: int, force_download: bool, settings_arg, ercot_client) -> None:
                settings_arg.processed_dir.mkdir(parents=True, exist_ok=True)
                settings_arg.processed_dam_path(year).write_text("processed")

            def build_fn(year: int, settings_arg) -> None:
                settings_arg.metrics_dir.mkdir(parents=True, exist_ok=True)
                settings_arg.metrics_path(year).write_text("partial")

            with self.assertRaisesRegex(FileNotFoundError, "Missing dashboard artifacts after attempted bootstrap"):
                ensure_dashboard_artifacts(
                    year=2025,
                    settings=settings,
                    fetch_fn=fetch_fn,
                    build_fn=build_fn,
                )

    def _make_settings(self, temp_root: Path):
        data_dir = temp_root / "data"
        return replace(
            SETTINGS,
            root_dir=temp_root,
            data_dir=data_dir,
            raw_dir=data_dir / "raw",
            processed_dir=data_dir / "processed",
            metrics_dir=data_dir / "metrics",
        )

    def _touch_required_artifacts(self, settings) -> None:
        settings.metrics_dir.mkdir(parents=True, exist_ok=True)
        settings.metrics_path(2025).write_text("metrics")
        settings.daily_profile_windows_path(2025).write_text("daily")
        settings.hourly_profile_shape_path(2025).write_text("hourly")


if __name__ == "__main__":
    unittest.main()
