# ERCOT Annual Large-Load Flexibility Screener

Which ERCOT hubs and load zones look strongest for large-load deployment when cheap charging windows and battery-backed flexibility can materially reduce annual delivered cost?

This project is an annual screener, not a daily dashboard. It uses historical ERCOT day-ahead settlement point prices to rank locations under two load archetypes and two battery durations:

- `24/7 Training`
- `Weekday 9-5 Inference`
- `4h battery`
- `8h battery`

The app stays honest about scope. It screens **ERCOT hubs and load zones**, not individual nodes.

## Supported Environment

- verified against `Python 3.12.x`
- includes `.python-version` and `runtime.txt` markers for that runtime
- `gridstatus==0.34.0` may fail to install under `Python 3.13`, so `3.12.x` is the supported submission path

## What The App Does

- ranks every ERCOT hub/load-zone location for the selected annual lens
- compares `4h` and `8h` battery flexibility side by side
- maps locations on a clickable Texas screen with persistent selection
- shows annual effective delivered cost, annual cost reduction, profitable-day share, and active-hour tail-risk reduction
- provides drilldown evidence:
  - month-by-hour price heatmaps
  - effective shaped-price heatmaps
  - monthly profitable-day share
  - daily causal window diagnostics
  - raw key/value metrics tables for review

## Core Method

### Market surface

- ERCOT Day-Ahead Market settlement point prices
- calendar year `2025`
- hourly data
- ~15 hubs and load zones

### Load profiles

- `training_24x7`
  - active all local hours
  - battery may charge in any earlier same-day hours and discharge later the same day
- `inference_weekday_9_17`
  - active during local hours `09:00-16:59` on weekdays only
  - battery may charge only before the workday and discharge only inside the active window

### Battery convention

- normalized to `1 MW load`
- `1 MW battery power per 1 MW load`
- `4h` and `8h` energy durations
- `85%` round-trip efficiency
- same-day charge then discharge only
- no cross-day state of charge
- no ancillary services, degradation, or transmission constraints

### Annual score

Each profile-duration lens scores locations from `0-100` using:

- inverse normalized effective average price
- normalized annual cost reduction %
- normalized profitable-day share
- normalized active-hour `p95` price reduction %

Daily best-spread metrics remain drilldown diagnostics only. They do not drive the primary annual score.

## Single Truth Path

`src/config.py` -> `src/data/fetch.py` / `src/data/validate.py` -> `src/analytics/battery_model.py` / `src/analytics/metrics.py` -> `app.py`

The Streamlit app is presentation-only. Core business metrics are precomputed and read from Parquet artifacts.

## Artifacts

The analytics pipeline writes:

- `data/processed/ercot_dam_spp_utc_2025.parquet`
- `data/processed/ercot_validation_report_2025.json`
- `data/metrics/ercot_location_metrics_2025.parquet`
- `data/metrics/ercot_daily_spreads_2025.parquet`
- `data/metrics/ercot_battery_value_2025.parquet`
- `data/metrics/ercot_daily_profile_windows_2025.parquet`
- `data/metrics/ercot_hourly_profile_shape_2025.parquet`

The expanded annual metrics artifact now includes:

- legacy annual screening columns for parity
- profile-aware and duration-aware annual cost metrics
- score and rank columns for all four annual lenses
- `best_fit_lens` and `best_fit_rank`

## Quickstart

### 1. Install dependencies

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Pull and validate ERCOT data

```bash
python -m src.data.fetch --year 2025
```

### 3. Build annual metrics and drilldown artifacts

```bash
python -m src.analytics.metrics --year 2025
```

### 4. Launch the app

```bash
streamlit run app.py
```

On macOS you can also double-click [Run_ERCOT_Screener.command](Run_ERCOT_Screener.command). It expects `Python 3.12.x`, bootstraps `.venv`, validates data availability, builds missing metrics artifacts, and launches Streamlit.

On Windows, the repo also includes [Run_ERCOT_Screener.bat](Run_ERCOT_Screener.bat) and [Run_ERCOT_Screener.ps1](Run_ERCOT_Screener.ps1). Those launchers are aligned to the same `Python 3.12.x` requirement, but they were not runtime-verified in this macOS environment.

The submitted artifact is the Git repo. Local virtual environments, caches, generated Parquet outputs, and OS-specific archive folders are intentionally excluded from version control.

## Verification Commands

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m src.data.fetch --year 2025
python -m src.analytics.metrics --year 2025
streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8510
python qa_check.py
```

## Repository Structure

```text
Modo_Assignment/
├── .python-version
├── app.py
├── README.md
├── ARCHITECTURE.md
├── AI-Assistant.txt
├── Run_ERCOT_Screener.command
├── Run_ERCOT_Screener.bat
├── Run_ERCOT_Screener.ps1
├── qa_check.py
├── requirements.txt
├── runtime.txt
├── data/
│   ├── raw/
│   ├── processed/
│   └── metrics/
├── src/
│   ├── config.py
│   ├── data/
│   │   ├── fetch.py
│   │   └── validate.py
│   ├── analytics/
│   │   ├── battery_model.py
│   │   └── metrics.py
│   └── presentation/
│       ├── reviewer_table.py
│       └── texas_map.py
└── tests/
    ├── fixtures.py
    ├── test_battery_model.py
    ├── test_metrics.py
    ├── test_reviewer_table.py
    ├── test_texas_map.py
    └── test_validate.py
```

## Limitations

- hub/load-zone screening only; not nodal analysis
- historical descriptive analysis only; not forecasting
- no transmission, interconnection, land, fiber, water, or infrastructure overlays
- stylized battery heuristic only; not an optimization model

## AI Workflow

This repo intentionally documents AI usage because the take-home explicitly values it.

- architecture and scope control were front-loaded so the project stayed within a defensible 2-4 hour product envelope
- the reviewer-facing AI note is summarized in [AI-Assistant.txt](AI-Assistant.txt)
- architectural decisions stayed anchored to the single truth path, with presentation logic kept downstream of precomputed Parquet artifacts

The AI note is meant to be readable by a human reviewer without requiring terminal logs or chat history.
