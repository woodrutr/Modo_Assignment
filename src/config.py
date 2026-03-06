from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class MetricWeights:
    pct_negative: float = 0.25
    pct_below_20: float = 0.25
    avg_daily_spread: float = 0.25
    pct_above_100: float = 0.25

    def __post_init__(self) -> None:
        total = (
            self.pct_negative
            + self.pct_below_20
            + self.avg_daily_spread
            + self.pct_above_100
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Metric weights must sum to 1.0.")


@dataclass(frozen=True)
class BatteryAssumptions:
    charge_mwh_per_hour: float = 100.0
    charge_hours_per_day: int = 4
    discharge_hours_per_day: int = 4
    round_trip_efficiency: float = 0.85

    def __post_init__(self) -> None:
        if self.charge_mwh_per_hour <= 0:
            raise ValueError("charge_mwh_per_hour must be positive.")
        if self.charge_hours_per_day <= 0 or self.discharge_hours_per_day <= 0:
            raise ValueError("Charge and discharge windows must be positive.")
        if not 0 < self.round_trip_efficiency <= 1:
            raise ValueError("round_trip_efficiency must be in (0, 1].")


@dataclass(frozen=True)
class LocationAnchor:
    location: str
    map_label: str
    anchor_name: str
    anchor_note: str
    lat: float
    lon: float
    text_position: str = "top center"


def _default_location_anchors() -> tuple[LocationAnchor, ...]:
    return (
        LocationAnchor(
            location="HB_BUSAVG",
            map_label="HB_BUSAVG",
            anchor_name="Central Texas",
            anchor_note="Representative statewide anchor for ERCOT bus average pricing.",
            lat=31.10,
            lon=-99.90,
            text_position="top left",
        ),
        LocationAnchor(
            location="HB_HOUSTON",
            map_label="HB_HOUSTON",
            anchor_name="Houston",
            anchor_note="Representative anchor near the Houston trading hub.",
            lat=29.7604,
            lon=-95.3698,
            text_position="top center",
        ),
        LocationAnchor(
            location="HB_HUBAVG",
            map_label="HB_HUBAVG",
            anchor_name="Central Texas",
            anchor_note="Representative statewide anchor for ERCOT hub average pricing.",
            lat=31.55,
            lon=-99.15,
            text_position="bottom right",
        ),
        LocationAnchor(
            location="HB_NORTH",
            map_label="HB_NORTH",
            anchor_name="Dallas-Fort Worth",
            anchor_note="Representative anchor near the North trading hub.",
            lat=32.7767,
            lon=-96.7970,
            text_position="top center",
        ),
        LocationAnchor(
            location="HB_PAN",
            map_label="HB_PAN",
            anchor_name="Amarillo",
            anchor_note="Representative anchor near the Panhandle trading hub.",
            lat=35.2220,
            lon=-101.8313,
            text_position="top center",
        ),
        LocationAnchor(
            location="HB_SOUTH",
            map_label="HB_SOUTH",
            anchor_name="Corpus Christi",
            anchor_note="Representative anchor near the South trading hub.",
            lat=27.8006,
            lon=-97.3964,
            text_position="top center",
        ),
        LocationAnchor(
            location="HB_WEST",
            map_label="HB_WEST",
            anchor_name="Midland-Odessa",
            anchor_note="Representative anchor near the West trading hub.",
            lat=31.9974,
            lon=-102.0779,
            text_position="top center",
        ),
        LocationAnchor(
            location="LZ_AEN",
            map_label="LZ_AEN",
            anchor_name="Austin",
            anchor_note="Representative anchor for the Austin Energy load zone.",
            lat=30.2672,
            lon=-97.7431,
            text_position="left center",
        ),
        LocationAnchor(
            location="LZ_CPS",
            map_label="LZ_CPS",
            anchor_name="San Antonio",
            anchor_note="Representative anchor for the CPS Energy load zone.",
            lat=29.4241,
            lon=-98.4936,
            text_position="left center",
        ),
        LocationAnchor(
            location="LZ_HOUSTON",
            map_label="LZ_HOUSTON",
            anchor_name="Houston",
            anchor_note="Representative anchor for the Houston load zone.",
            lat=29.5500,
            lon=-95.0500,
            text_position="bottom center",
        ),
        LocationAnchor(
            location="LZ_LCRA",
            map_label="LZ_LCRA",
            anchor_name="Bastrop",
            anchor_note="Representative anchor for the LCRA load zone.",
            lat=30.1105,
            lon=-97.3153,
            text_position="right center",
        ),
        LocationAnchor(
            location="LZ_NORTH",
            map_label="LZ_NORTH",
            anchor_name="Dallas",
            anchor_note="Representative anchor for the North load zone.",
            lat=32.9500,
            lon=-96.8500,
            text_position="bottom center",
        ),
        LocationAnchor(
            location="LZ_RAYBN",
            map_label="LZ_RAYBN",
            anchor_name="Rockwall",
            anchor_note="Representative anchor for the Rayburn load zone.",
            lat=32.9312,
            lon=-96.4597,
            text_position="right center",
        ),
        LocationAnchor(
            location="LZ_SOUTH",
            map_label="LZ_SOUTH",
            anchor_name="McAllen",
            anchor_note="Representative anchor for the South load zone.",
            lat=26.2034,
            lon=-98.2300,
            text_position="bottom center",
        ),
        LocationAnchor(
            location="LZ_WEST",
            map_label="LZ_WEST",
            anchor_name="Midland",
            anchor_note="Representative anchor for the West load zone.",
            lat=31.6500,
            lon=-102.2500,
            text_position="bottom center",
        ),
    )


@dataclass(frozen=True)
class AppSettings:
    project_root: Path = field(default_factory=_project_root)
    market_timezone: str = "US/Central"
    storage_timezone: str = "UTC"
    target_year: int = 2025
    fallback_year: int = 2024
    market_name: str = "DAY_AHEAD_HOURLY"
    low_price_threshold: float = 20.0
    high_price_threshold: float = 100.0
    metric_weights: MetricWeights = field(default_factory=MetricWeights)
    battery: BatteryAssumptions = field(default_factory=BatteryAssumptions)
    location_anchors: tuple[LocationAnchor, ...] = field(default_factory=_default_location_anchors)
    required_dam_columns: tuple[str, ...] = (
        "Time",
        "Interval Start",
        "Interval End",
        "Location",
        "Location Type",
        "Market",
        "SPP",
    )
    expected_interval_minutes: int = 60

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def metrics_dir(self) -> Path:
        return self.data_dir / "metrics"

    def raw_dam_path(self, year: int) -> Path:
        return self.raw_dir / f"ercot_dam_spp_{year}.parquet"

    def processed_dam_path(self, year: int) -> Path:
        return self.processed_dir / f"ercot_dam_spp_utc_{year}.parquet"

    def validation_report_path(self, year: int) -> Path:
        return self.processed_dir / f"ercot_dam_validation_{year}.json"

    def metrics_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_location_metrics_{year}.parquet"

    def daily_spread_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_daily_spreads_{year}.parquet"

    def battery_value_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_battery_value_{year}.parquet"

    def __post_init__(self) -> None:
        if self.fallback_year >= self.target_year:
            raise ValueError("fallback_year must be earlier than target_year.")
        known_locations = {anchor.location for anchor in self.location_anchors}
        if len(known_locations) != len(self.location_anchors):
            raise ValueError("location_anchors must contain unique location values.")


SETTINGS = AppSettings()
