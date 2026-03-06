from __future__ import annotations

import unittest

import pandas as pd

from src.data.validate import validate_and_normalize_dam_dataset


def _raw_frame() -> pd.DataFrame:
    interval_start = pd.date_range(
        start="2025-01-01 00:00:00",
        periods=4,
        freq="h",
        tz="US/Central",
    )
    interval_end = interval_start + pd.Timedelta(hours=1)
    return pd.DataFrame(
        {
            "Time": interval_start,
            "Interval Start": interval_start,
            "Interval End": interval_end,
            "Location": ["HB_HOUSTON"] * 4,
            "Location Type": ["Trading Hub"] * 4,
            "Market": ["DAY_AHEAD_HOURLY"] * 4,
            "SPP": [10.0, 20.0, 30.0, 40.0],
        }
    )


class ValidationTests(unittest.TestCase):
    def test_validate_and_normalize_succeeds_on_complete_hourly_grid(self) -> None:
        validated = validate_and_normalize_dam_dataset(_raw_frame(), expected_year=None)
        self.assertEqual(len(validated.frame), 4)
        self.assertEqual(validated.report.missing_interval_count, 0)

    def test_validate_and_normalize_raises_on_missing_interval(self) -> None:
        with self.assertRaises(ValueError):
            validate_and_normalize_dam_dataset(_raw_frame().drop(index=2), expected_year=None)

    def test_validate_and_normalize_raises_on_duplicate_interval(self) -> None:
        duplicate_frame = pd.concat([_raw_frame(), _raw_frame().iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            validate_and_normalize_dam_dataset(duplicate_frame, expected_year=None)


if __name__ == "__main__":
    unittest.main()
