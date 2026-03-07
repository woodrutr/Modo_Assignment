from __future__ import annotations

import unittest

from src.data.validate import validate_and_normalize_dam_dataset
from tests.fixtures import make_raw_frame


class ValidateTests(unittest.TestCase):
    def test_validate_normalizes_to_expected_processed_schema(self) -> None:
        raw = make_raw_frame(
            {
                "HB_PAN": [10.0, 12.0, 14.0, 16.0],
                "LZ_WEST": [11.0, 13.0, 15.0, 17.0],
            }
        )
        result = validate_and_normalize_dam_dataset(raw, expected_year=2025)
        self.assertEqual(
            result.frame.columns.tolist(),
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
        )
        self.assertEqual(result.report.row_count, 8)
        self.assertEqual(result.report.location_count, 2)

    def test_missing_interval_raises_hard_error(self) -> None:
        raw = make_raw_frame({"HB_PAN": [10.0, 12.0, 14.0, 16.0]})
        raw = raw.drop(index=[2]).reset_index(drop=True)
        with self.assertRaisesRegex(ValueError, "Validation failed"):
            validate_and_normalize_dam_dataset(raw, expected_year=2025)


if __name__ == "__main__":
    unittest.main()
