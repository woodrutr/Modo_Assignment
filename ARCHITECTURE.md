# Architecture Specification

## Objective

Build a deterministic annual ERCOT screener for large-load deployment with battery flexibility. The product answers:

> Which ERCOT hubs and load zones show the strongest historical conditions for large-load deployment when a 4-hour or 8-hour battery can shift energy purchases across the day?

This implementation remains **hub/load-zone only**. It is explicitly not nodal.

## Execution Mode

- strict annual screening mode
- deterministic Parquet artifacts
- presentation-only Streamlit app
- no compiled-shim dependency in the active core pipeline

## Single Truth Path

`src/config.py` -> `src/data/fetch.py` -> `src/data/validate.py` -> `src/analytics/battery_model.py` -> `src/analytics/metrics.py` -> `app.py`

Rules:

- `src/config.py` is the single source of truth for paths, profiles, durations, thresholds, and display constants
- `src/data/*` may fetch and validate, but may not compute business metrics
- `src/analytics/*` owns all primary business metrics and drilldown artifact generation
- `app.py` may filter, format, aggregate for display, and render charts, but may not recompute core domain logic

## Data Contract

### Raw input

Source: `gridstatus.Ercot().get_dam_spp(year)`

Required columns:

- `Time`
- `Interval Start`
- `Interval End`
- `Location`
- `Location Type`
- `Market`
- `SPP`

Expected market:

- `DAY_AHEAD_HOURLY`

### Processed dataset

Canonical path:

- `data/processed/ercot_dam_spp_utc_{year}.parquet`

Schema:

- `timestamp_utc`
- `interval_start_utc`
- `interval_end_utc`
- `market_date`
- `location`
- `location_type`
- `market`
- `spp`

Integrity rules:

- all backend timestamps are timezone-aware UTC
- interval width must equal `60` minutes
- missing or duplicate intervals are hard failures
- all locations must share the same hourly interval index

Validation report path:

- `data/processed/ercot_validation_report_{year}.json`

## Analytical Lenses

### Load profiles

`training_24x7`

- active every local hour
- charge may occur in any earlier same-day hours
- discharge may occur in any later same-day hours

`inference_weekday_9_17`

- active only on weekdays during local hours `09:00-16:59`
- charge may occur only before the active window on the same weekday
- discharge must occur inside the active window
- weekends have zero active load and zero battery value

### Battery durations

- `4h`
- `8h`

### Economic normalization

- baseline load: `1.0 MW`
- battery power: `1.0 MW per MW of load`
- battery energy: `duration_hours MWh per MW of load`
- round-trip efficiency: `0.85`
- same-day charge then discharge only
- if the best causal spread is non-positive, the battery remains idle for that day

## Artifact Contract

### Expanded annual metrics

Path:

- `data/metrics/ercot_location_metrics_{year}.parquet`

Contains:

- legacy annual screening metrics for parity
- annual inference day-vs-overnight context
- legacy battery-value context
- profile-duration annual metrics for all four lenses
- `best_fit_lens`
- `best_fit_rank`

Per lens naming pattern:

- `{profile}_{duration}h_baseline_annual_cost_usd_per_mw_year`
- `{profile}_{duration}h_effective_annual_cost_usd_per_mw_year`
- `{profile}_{duration}h_effective_avg_price_usd_per_mwh`
- `{profile}_{duration}h_annual_cost_reduction_usd_per_mw_year`
- `{profile}_{duration}h_annual_cost_reduction_pct`
- `{profile}_{duration}h_profitable_day_share`
- `{profile}_{duration}h_count_profitable_days`
- `{profile}_{duration}h_p50_daily_best_spread_usd_per_mwh`
- `{profile}_{duration}h_p90_daily_best_spread_usd_per_mwh`
- `{profile}_{duration}h_p95_active_hour_price_usd_per_mwh`
- `{profile}_{duration}h_p95_active_hour_effective_price_usd_per_mwh`
- `{profile}_{duration}h_p95_active_hour_reduction_pct`
- `{profile}_{duration}h_score`
- `{profile}_{duration}h_rank`

### Daily profile windows

Path:

- `data/metrics/ercot_daily_profile_windows_{year}.parquet`

Grain:

- `location x profile x local_date`

Contains:

- baseline daily cost
- active-load MWh
- `4h` causal charge/discharge window diagnostics
- `8h` causal charge/discharge window diagnostics
- profitable flags and effective daily cost outputs

### Hourly profile shape

Path:

- `data/metrics/ercot_hourly_profile_shape_{year}.parquet`

Grain:

- `location x profile x duration_hours x local_month x local_hour`

Contains:

- average market price
- average effective shaped active-hour price
- observation counts
- active-hour flag
- selected charge/discharge observation counts

### Legacy context artifacts

Still generated for parity and reviewer transparency:

- `data/metrics/ercot_daily_spreads_{year}.parquet`
- `data/metrics/ercot_battery_value_{year}.parquet`

These are no longer primary ranking inputs in the dashboard.

## Scoring Logic

Each profile-duration lens is normalized across locations within that exact lens only.

Score weights:

- `40%` inverse normalized `effective_avg_price_usd_per_mwh`
- `25%` normalized `annual_cost_reduction_pct`
- `20%` normalized `profitable_day_share`
- `15%` normalized `p95_active_hour_reduction_pct`

Daily best-spread metrics remain diagnostic only and are excluded from the primary score to avoid double-counting arbitrage.

`best_fit_lens` selection:

- choose the lens with the lowest `rank`
- tie-break by highest `annual_cost_reduction_pct`
- final deterministic tie-break by score, then lens label

## UI Contract

Primary controls:

- `Load profile`
- `Primary battery duration`

Session state:

- `selected_profile`
- `selected_duration`
- `selected_location`

Top-level layout:

1. annual lens controls and hero metrics
2. clickable Texas location map with persistent selection
3. narrow reviewer table showing 4h vs 8h side by side
4. analyst console tabs

Analyst console tabs:

1. `Annual Summary`
2. `Temporal Shape`
3. `4h Flexibility`
4. `8h Flexibility`

Raw diagnostics must render as key/value tables, not JSON blobs.

## Determinism and Verification

Deterministic requirements:

- identical cached raw input produces identical processed schema and annual rank order
- current 2025 legacy rank order is enforced as a guardrail during metrics generation
- launchers and the app read artifact paths from `src.config.SETTINGS`

Expected verification commands:

- `python -m unittest discover -s tests`
- `python -m src.data.fetch --year 2025`
- `python -m src.analytics.metrics --year 2025`
- `streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8510`

## Non-Goals

- nodal siting
- congestion decomposition
- production dispatch optimization
- transmission, interconnection, land, fiber, or water overlays
- forward price forecasting
