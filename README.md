# ERCOT Flexibility Opportunity Screener

> **Live app:** [Open the hosted Streamlit dashboard](https://settings-mug9d7tln2vtar3wyvdrdw.streamlit.app)

This tool is designed to help developers, investors, and large-load planners identify which ERCOT regions appear most sensitive to flexibility, and therefore where deeper forward-looking modeling is most likely to add value.

It is a triage tool, not a siting engine. The app uses historical ERCOT day-ahead settlement point prices to rank hubs and load zones under two load profiles and two battery durations:

- `24/7 Training`
- `Weekday 9-5 Inference`
- `4h battery`
- `8h battery`

## What This Helps You Decide

- which ERCOT regions look most flexibility-sensitive under the active annual lens
- where an upper-bound historical battery-backed load-shaping signal looks strongest
- which regions merit deeper forward-looking modeling next

## What This Is Not

- not a nodal siting engine
- not a forecast
- not an interconnection screen
- not a full dispatch optimization model

## App Structure

The Streamlit app is organized into 3 tabs:

### `Screen`

- ranked annual triage table
- clickable Texas map with persistent shared selection
- deterministic `Why it ranks high` explainer
- one-sentence next-step prompt for deeper analysis

### `Evidence`

- one raw price-shape heatmap
- one before/after annual economics comparison
- one seasonal view
- additional diagnostics hidden behind a single expander

### `Next Step`

- explicit scope boundary
- what deeper modeling would add
- concise current limitations

## Supported Environment

- verified against `Python 3.12.x`
- includes `.python-version` and `runtime.txt` markers for that runtime
- `gridstatus==0.34.0` may fail under `Python 3.13`, so `3.12.x` is the supported submission path

## Data and Method

- market surface: ERCOT Day-Ahead Market settlement point prices
- scope: historical annual ERCOT hubs and load zones
- load profiles: `training_24x7` and `inference_weekday_9_17`
- battery convention: `1 MW` battery power per `1 MW` load, `4h` and `8h` durations, `85%` round-trip efficiency, same-day causal charge then discharge only
- score inputs: effective delivered cost, annual cost reduction, profitable-day share, and active-hour tail-risk reduction

### Battery Heuristic

- the `4h` and `8h` cases are **not fixed TOU schedules**
- they are **not vendor capture-rate inputs**
- they are closer to a constrained, ex-post historical oracle on realized DAM prices
- for each local day, profile, and battery duration, the model enumerates all eligible same-day charge and discharge windows, requires charge to finish before discharge starts, and chooses the best positive spread after `85%` round-trip efficiency
- if no positive spread exists, the battery stays idle for that day
- the resulting `4h` and `8h` values should be read as **upper-bound historical flexibility signals**, not realized project economics

### `$ / MW-year` Convention

- load is normalized to `1 MW`
- baseline annual cost is the sum of active-hour DAM prices across the year for that normalized `1 MW` load
- annual cost reduction in `USD / MW-year` is the sum of daily battery net value across the year
- effective annual cost is baseline annual cost minus annual battery value
- effective average price in `USD / MWh` is effective annual cost divided by annual active-load MWh
- for `24/7 Training`, annual active-load MWh comes from all hours; for `Weekday 9-5 Inference`, it comes only from active weekday daytime hours
- these are gross screening values only; the repo does not include capex, degradation, augmentation, financing, or production dispatch economics

### Score Construction

- `40%` inverse effective average price
- `25%` annual cost reduction %
- `20%` profitable-day share
- `15%` active-hour `p95` price reduction
- scores are min-max scaled within the screened hub/load-zone sample, so they are cross-sectional triage signals rather than absolute ERCOT-wide indexes

The app remains presentation-only. Core metrics are computed upstream and read from Parquet artifacts.
If the derived metrics artifacts are missing at startup, the app now attempts a deterministic bootstrap: it first ensures the processed DAM parquet exists, then rebuilds the derived metrics artifacts before rendering.

## Single Truth Path

`src/config.py` -> `src/data/fetch.py` / `src/data/validate.py` -> `src/analytics/battery_model.py` / `src/analytics/metrics.py` -> `app.py`

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

### 3. Build annual metrics

```bash
python -m src.analytics.metrics --year 2025
```

### 4. Launch the app

```bash
streamlit run app.py
```

On macOS you can also double-click [Run_ERCOT_Screener.command](scripts/Run_ERCOT_Screener.command). It expects `Python 3.12.x`, bootstraps `.venv`, validates data availability, builds missing metrics artifacts, and launches Streamlit.

On Windows, the repo also includes [Run_ERCOT_Screener.bat](scripts/Run_ERCOT_Screener.bat) and [Run_ERCOT_Screener.ps1](scripts/Run_ERCOT_Screener.ps1). Those launchers were aligned to the same `Python 3.12.x` contract, but they were not runtime-verified in this macOS environment.

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
python scripts/qa_check.py
```

## Repository Structure

```text
Modo_Assignment/
├── .python-version
├── app.py
├── README.md
├── docs/
│   └── ARCHITECTURE.md
├── requirements.txt
├── runtime.txt
├── scripts/
│   ├── Run_ERCOT_Screener.command
│   ├── Run_ERCOT_Screener.bat
│   ├── Run_ERCOT_Screener.ps1
│   └── qa_check.py
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
│       ├── runtime_artifacts.py
│       └── texas_map.py
└── tests/
    ├── fixtures.py
    ├── test_battery_model.py
    ├── test_metrics.py
    ├── test_runtime_artifacts.py
    ├── test_reviewer_table.py
    ├── test_texas_map.py
    └── test_validate.py
```

## AI Workflow

This take-home explicitly allowed and encouraged AI use. 

- AI was used to accelerate architecture framing, implementation sequencing, UI refinement, and verification tracking
- Final behavior was kept anchored to the single truth path and validated with local commands
- AI-assisted diagnostics and cleanup were kept separate from the reviewer-facing product claim
