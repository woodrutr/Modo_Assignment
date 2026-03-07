from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


LoadProfileKey = Literal["training_24x7", "inference_weekday_9_17"]
BatteryDurationHours = Literal[4, 8]


@dataclass(frozen=True)
class LegacyMetricWeights:
    pct_negative: float = 0.25
    pct_below_20: float = 0.25
    avg_daily_spread: float = 0.25
    pct_above_100: float = 0.25


@dataclass(frozen=True)
class LensScoreWeights:
    effective_avg_price: float = 0.40
    annual_cost_reduction_pct: float = 0.25
    profitable_day_share: float = 0.20
    p95_active_hour_reduction_pct: float = 0.15


@dataclass(frozen=True)
class LegacyBatterySettings:
    charge_hours_per_day: int = 4
    discharge_hours_per_day: int = 4
    charge_mwh_per_hour: float = 100.0
    round_trip_efficiency: float = 0.85


@dataclass(frozen=True)
class FlexBatterySettings:
    load_mw: float = 1.0
    battery_power_mw_per_mw_load: float = 1.0
    round_trip_efficiency: float = 0.85
    supported_durations: tuple[BatteryDurationHours, ...] = (4, 8)


@dataclass(frozen=True)
class LoadProfile:
    key: LoadProfileKey
    label: str
    short_label: str
    description: str
    active_hours: tuple[int, ...]
    charge_hours: tuple[int, ...]
    weekdays_only: bool


@dataclass(frozen=True)
class LocationAnchor:
    location: str
    map_label: str
    anchor_name: str
    anchor_note: str
    lat: float
    lon: float
    text_position: str = "top center"


@dataclass(frozen=True)
class AppSettings:
    root_dir: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    metrics_dir: Path
    target_year: int = 2025
    fallback_year: int = 2024
    market_name: str = "DAY_AHEAD_HOURLY"
    market_timezone: str = "US/Central"
    storage_timezone: str = "UTC"
    expected_interval_minutes: int = 60
    low_price_threshold: float = 20.0
    high_price_threshold: float = 100.0
    required_dam_columns: tuple[str, ...] = (
        "Time",
        "Interval Start",
        "Interval End",
        "Location",
        "Location Type",
        "Market",
        "SPP",
    )
    legacy_metric_weights: LegacyMetricWeights = field(default_factory=LegacyMetricWeights)
    lens_score_weights: LensScoreWeights = field(default_factory=LensScoreWeights)
    legacy_battery: LegacyBatterySettings = field(default_factory=LegacyBatterySettings)
    flex_battery: FlexBatterySettings = field(default_factory=FlexBatterySettings)
    profiles: tuple[LoadProfile, ...] = field(default_factory=tuple)
    location_anchors: tuple[LocationAnchor, ...] = field(default_factory=tuple)

    @property
    def metric_weights(self) -> LegacyMetricWeights:
        return self.legacy_metric_weights

    def raw_dam_path(self, year: int) -> Path:
        return self.raw_dir / f"ercot_dam_spp_{year}.parquet"

    def processed_dam_path(self, year: int) -> Path:
        return self.processed_dir / f"ercot_dam_spp_utc_{year}.parquet"

    def validation_report_path(self, year: int) -> Path:
        return self.processed_dir / f"ercot_validation_report_{year}.json"

    def metrics_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_location_metrics_{year}.parquet"

    def daily_spread_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_daily_spreads_{year}.parquet"

    def battery_value_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_battery_value_{year}.parquet"

    def daily_profile_windows_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_daily_profile_windows_{year}.parquet"

    def hourly_profile_shape_path(self, year: int) -> Path:
        return self.metrics_dir / f"ercot_hourly_profile_shape_{year}.parquet"


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

PALETTE = {
    "paper": "#f3efe8",
    "paper_alt": "#ebe5db",
    "panel": "rgba(255, 252, 247, 0.78)",
    "panel_strong": "rgba(255, 252, 247, 0.92)",
    "ink": "#1f2628",
    "muted": "#697274",
    "line": "rgba(31, 38, 40, 0.10)",
    "line_strong": "rgba(31, 38, 40, 0.18)",
    "sea": "#365b67",
    "sea_soft": "#90a3a8",
    "moss": "#667257",
    "sand": "#b89d7d",
    "clay": "#8b624a",
    "accent": "#7f4f3f",
    "accent_soft": "#d9c6b8",
    "score_low": "#d4c7bb",
    "score_mid": "#90a1a5",
    "score_high": "#355a66",
    "good": "#5f7a58",
}

DISPLAY_FONT = "'SF Pro Display','Avenir Next','Segoe UI','Helvetica Neue',sans-serif"
BODY_FONT = "'SF Pro Text','Avenir Next','Segoe UI','Helvetica Neue',sans-serif"
MONTH_ORDER = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
SCORE_SCALE = [
    [0.0, PALETTE["score_low"]],
    [0.42, PALETTE["score_mid"]],
    [1.0, PALETTE["score_high"]],
]
HEATMAP_SCALE = [
    [0.0, "#f3ede2"],
    [0.33, "#dfcfbf"],
    [0.67, "#b99674"],
    [1.0, "#7c6e70"],
]
EFFECTIVE_PRICE_SCALE = [
    [0.0, "#dce6ea"],
    [0.5, "#b89d7d"],
    [1.0, "#8b624a"],
]

SETTINGS = AppSettings(
    root_dir=ROOT_DIR,
    data_dir=DATA_DIR,
    raw_dir=DATA_DIR / "raw",
    processed_dir=DATA_DIR / "processed",
    metrics_dir=DATA_DIR / "metrics",
    profiles=(
        LoadProfile(
            key="training_24x7",
            label="24/7 Training",
            short_label="Training",
            description=(
                "Flat 24/7 large load. Battery charges in cheaper same-day hours and "
                "offsets later expensive hours."
            ),
            active_hours=tuple(range(24)),
            charge_hours=tuple(range(24)),
            weekdays_only=False,
        ),
        LoadProfile(
            key="inference_weekday_9_17",
            label="Weekday 9-5 Inference",
            short_label="Inference",
            description=(
                "Weekday daytime load. Battery charges before the workday and offsets "
                "the active delivery window."
            ),
            active_hours=tuple(range(9, 17)),
            charge_hours=tuple(range(0, 9)),
            weekdays_only=True,
        ),
    ),
    location_anchors=(
        LocationAnchor(
            location="HB_PAN",
            map_label="Panhandle Hub",
            anchor_name="Amarillo",
            anchor_note="Representative Panhandle anchor for wind-heavy conditions.",
            lat=35.221997,
            lon=-101.831297,
            text_position="middle right",
        ),
        LocationAnchor(
            location="HB_WEST",
            map_label="West Hub",
            anchor_name="Midland",
            anchor_note="Representative West Texas anchor with strong renewable buildout.",
            lat=31.997346,
            lon=-102.077915,
            text_position="bottom right",
        ),
        LocationAnchor(
            location="HB_NORTH",
            map_label="North Hub",
            anchor_name="Dallas-Fort Worth",
            anchor_note="Representative North hub anchor centered on the DFW load pocket.",
            lat=32.776665,
            lon=-96.796989,
            text_position="top right",
        ),
        LocationAnchor(
            location="HB_SOUTH",
            map_label="South Hub",
            anchor_name="Corpus Christi",
            anchor_note="Representative South hub anchor near the coastal industrial corridor.",
            lat=27.800583,
            lon=-97.396378,
            text_position="top left",
        ),
        LocationAnchor(
            location="HB_HOUSTON",
            map_label="Houston Hub",
            anchor_name="Houston",
            anchor_note="Representative Houston hub anchor near the primary Gulf Coast load center.",
            lat=29.760427,
            lon=-95.369804,
            text_position="bottom left",
        ),
        LocationAnchor(
            location="HB_HUBAVG",
            map_label="Hub Average",
            anchor_name="Central Texas",
            anchor_note="Representative statewide hub-average anchor for the ERCOT hub blend.",
            lat=31.252876,
            lon=-99.25061,
            text_position="top center",
        ),
        LocationAnchor(
            location="HB_BUSAVG",
            map_label="Bus Average",
            anchor_name="ERCOT System Average",
            anchor_note="Representative statewide bus-average anchor for the system-wide price blend.",
            lat=31.0,
            lon=-98.9,
            text_position="bottom center",
        ),
        LocationAnchor(
            location="LZ_WEST",
            map_label="West Zone",
            anchor_name="Abilene",
            anchor_note="Representative West load-zone anchor for western Texas demand.",
            lat=32.448734,
            lon=-99.733147,
            text_position="middle left",
        ),
        LocationAnchor(
            location="LZ_LCRA",
            map_label="LCRA Zone",
            anchor_name="Austin",
            anchor_note="Representative LCRA anchor for central Texas load exposure.",
            lat=30.267153,
            lon=-97.743057,
            text_position="bottom left",
        ),
        LocationAnchor(
            location="LZ_CPS",
            map_label="CPS Zone",
            anchor_name="San Antonio",
            anchor_note="Representative CPS anchor for the San Antonio municipal load footprint.",
            lat=29.424122,
            lon=-98.493629,
            text_position="bottom right",
        ),
        LocationAnchor(
            location="LZ_AEN",
            map_label="AEN Zone",
            anchor_name="Austin Energy",
            anchor_note="Representative Austin Energy anchor for the local municipal load area.",
            lat=30.271129,
            lon=-97.743699,
            text_position="top right",
        ),
        LocationAnchor(
            location="LZ_NORTH",
            map_label="North Zone",
            anchor_name="Fort Worth",
            anchor_note="Representative North load-zone anchor for the broader DFW demand area.",
            lat=32.755489,
            lon=-97.330765,
            text_position="top left",
        ),
        LocationAnchor(
            location="LZ_RAYBN",
            map_label="Rayburn Zone",
            anchor_name="Sherman-Denison",
            anchor_note="Representative Rayburn zone anchor for the north Texas cooperative footprint.",
            lat=33.635662,
            lon=-96.60888,
            text_position="middle right",
        ),
        LocationAnchor(
            location="LZ_HOUSTON",
            map_label="Houston Zone",
            anchor_name="Greater Houston",
            anchor_note="Representative Houston load-zone anchor near the Gulf Coast demand center.",
            lat=29.749907,
            lon=-95.358421,
            text_position="top left",
        ),
        LocationAnchor(
            location="LZ_SOUTH",
            map_label="South Zone",
            anchor_name="McAllen",
            anchor_note="Representative South load-zone anchor for the Rio Grande Valley corridor.",
            lat=26.203407,
            lon=-98.230011,
            text_position="top right",
        ),
    ),
)

PROFILE_ORDER = tuple(profile.key for profile in SETTINGS.profiles)
PROFILE_LOOKUP = {profile.key: profile for profile in SETTINGS.profiles}
PROFILE_LABELS = {profile.key: profile.label for profile in SETTINGS.profiles}
PROFILE_SHORT_LABELS = {profile.key: profile.short_label for profile in SETTINGS.profiles}
DURATION_OPTIONS = SETTINGS.flex_battery.supported_durations
DURATION_LABELS = {4: "4h", 8: "8h"}
LENS_KEYS = tuple(
    (profile.key, duration)
    for profile in SETTINGS.profiles
    for duration in SETTINGS.flex_battery.supported_durations
)


def get_profile(profile_key: LoadProfileKey) -> LoadProfile:
    return PROFILE_LOOKUP[profile_key]


def lens_prefix(profile_key: LoadProfileKey, duration_hours: int) -> str:
    return f"{profile_key}_{duration_hours}h"


def lens_metric_column(profile_key: LoadProfileKey, duration_hours: int, metric_name: str) -> str:
    return f"{lens_prefix(profile_key, duration_hours)}_{metric_name}"


def lens_label(profile_key: LoadProfileKey, duration_hours: int) -> str:
    return f"{PROFILE_SHORT_LABELS[profile_key]} {duration_hours}h"


__all__ = [
    "AppSettings",
    "BatteryDurationHours",
    "BODY_FONT",
    "DISPLAY_FONT",
    "DURATION_OPTIONS",
    "DURATION_LABELS",
    "EFFECTIVE_PRICE_SCALE",
    "FlexBatterySettings",
    "HEATMAP_SCALE",
    "LENS_KEYS",
    "LegacyBatterySettings",
    "LegacyMetricWeights",
    "LensScoreWeights",
    "LoadProfile",
    "LoadProfileKey",
    "LocationAnchor",
    "MONTH_ORDER",
    "PALETTE",
    "PROFILE_LABELS",
    "PROFILE_LOOKUP",
    "PROFILE_ORDER",
    "PROFILE_SHORT_LABELS",
    "ROOT_DIR",
    "SCORE_SCALE",
    "SETTINGS",
    "get_profile",
    "lens_label",
    "lens_metric_column",
    "lens_prefix",
]
