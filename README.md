# ERCOT Flexibility Opportunity Screener

This tool is designed to help developers, investors, and large-load planners identify which ERCOT regions appear most sensitive to flexibility, and therefore where deeper forward-looking modeling is most likely to add value.

It is a triage tool, not a siting engine. The app uses historical ERCOT day-ahead settlement point prices to rank hubs and load zones under two load profiles and two battery durations:

- `24/7 Training`
- `Weekday 9-5 Inference`
- `4h battery`
- `8h battery`

## What This Helps You Decide

- which ERCOT regions look most flexibility-sensitive under the active annual lens
- where battery-backed load shaping appears to reduce delivered cost the most
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

The app remains presentation-only. Core metrics are computed upstream and read from Parquet artifacts.

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

On macOS you can also double-click [Run_ERCOT_Screener.command](Run_ERCOT_Screener.command). It expects `Python 3.12.x`, bootstraps `.venv`, validates data availability, builds missing metrics artifacts, and launches Streamlit.

On Windows, the repo also includes [Run_ERCOT_Screener.bat](Run_ERCOT_Screener.bat) and [Run_ERCOT_Screener.ps1](Run_ERCOT_Screener.ps1). Those launchers were aligned to the same `Python 3.12.x` contract, but they were not runtime-verified in this macOS environment.

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

## AI Workflow

This take-home explicitly allowed and encouraged AI use. The reviewer-facing summary is in [AI-Assistant.txt](AI-Assistant.txt).

- AI was used to accelerate architecture framing, implementation sequencing, UI refinement, and verification tracking
- final behavior was kept anchored to the single truth path and validated with local commands
- AI-assisted diagnostics and cleanup were kept separate from the reviewer-facing product claim
