# ERCOT Battery Flexibility Location Screener

## What Question This Answers

**Which ERCOT locations show the strongest conditions for battery-backed large-load flexibility, based on price volatility and low-price availability?**

Large flexible loads — data centers, industrial electrolyzers, bitcoin mining operations — increasingly co-locate with battery energy storage to exploit electricity price patterns. The economic case depends on three local price characteristics: how often prices go negative or near-zero (cheap charging), how often they spike (profitable discharge), and how wide the daily spread is (arbitrage headroom). This tool screens ERCOT settlement points across all three dimensions and produces a ranked composite score.

## Why It Matters

ERCOT is the largest competitive wholesale market in the US with no capacity market, meaning energy prices carry the full investment signal. Texas also leads the US in utility-scale battery deployment and large-load interconnection (data centers, hydrogen). For developers, traders, and asset owners evaluating where to site flexible load + storage, the first-order question is: where do the price patterns favor this strategy? This screener answers that question using public data.

## What Data Is Used

Historical Day-Ahead Market (DAM) Settlement Point Prices from the ERCOT Market Information System, covering all trading hubs and load zones (~15 locations) for 12 months. Data is accessed via the `gridstatus` open-source library, which downloads directly from ERCOT's public document archives. No API keys or market participant credentials are required.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full data specification, schema, known data wrangling issues, and mitigation strategies.

## What Assumptions Are Stylized

This is a screening tool, not a siting model. Key simplifications:

- **Hub/zone granularity only.** Real siting decisions require nodal (bus-level) analysis. Hub and zone prices are aggregates that mask local congestion patterns.
- **No infrastructure proximity.** Real siting considers fiber connectivity, substation capacity, water access, and land availability — none of which are modeled here.
- **Historical patterns, not forecasts.** The screener describes what happened, not what will happen. Price patterns shift with generation mix changes, transmission buildouts, and load growth.
- **Battery model is a heuristic.** The optional toy model uses a simple "charge in cheapest 4 hours, discharge in most expensive 4 hours" rule with 85% round-trip efficiency. This is not dispatch optimization — it's a directional estimate.
- **No ancillary service revenue.** Real battery economics include regulation, reserves, and other grid services. Only energy arbitrage is modeled.

## What the Tool Is and Is Not

**Is:** A transparent, reproducible screener that ranks ERCOT locations by battery-friendly price characteristics using public data and defensible metrics.

**Is not:** A production siting model, a price forecast, a dispatch optimizer, or a substitute for nodal-level commercial analysis.

## How to Run

### Prerequisites

- Python ≥ 3.11 (required — `gridstatus` uses `StrEnum` from the standard library)
- Internet access for initial ERCOT data download (subsequent runs use cached Parquet files)

### Setup

```bash
# Verify Python version
python --version  # Must be 3.11+

# Clone and install
git clone <repo-url>
cd ercot-battery-screener
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Pull Data

```bash
python -m src.data.fetch
```

This downloads ERCOT DAM SPP data from the public archive and caches it to `data/raw/` as Parquet. Takes ~1-2 minutes on first run. Subsequent runs skip the download if cached data is current.

### Run the Screener

```bash
streamlit run app.py
```

Opens a browser with the interactive dashboard. All timestamps are displayed in US/Central time.

## Repository Structure

```
ercot-battery-screener/
├── README.md                    # This file
├── ARCHITECTURE.md              # Full technical specification
├── requirements.txt             # Pinned dependencies
├── app.py                       # Streamlit dashboard (presentation only)
├── src/
│   ├── __init__.py
│   ├── config.py                # Constants, paths, parameters (single source of truth)
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fetch.py             # ERCOT data acquisition → raw Parquet
│   │   └── validate.py          # Schema enforcement, missing-interval detection
│   └── analytics/
│       ├── __init__.py
│       ├── metrics.py           # Screener metric computations (pure functions)
│       └── battery_model.py     # Toy battery heuristic (pure functions)
├── data/
│   ├── raw/                     # Cached ERCOT downloads (Parquet, gitignored)
│   ├── processed/               # Validated, UTC-normalized data (Parquet, gitignored)
│   └── metrics/                 # Computed screener results (Parquet, gitignored)
├── tests/
│   ├── __init__.py
│   ├── test_metrics.py          # Unit tests for metric computations
│   └── test_battery_model.py    # Unit tests for battery heuristic
└── .gitignore
```

## How AI Accelerated This Workflow

This project was built using AI tools throughout the process, as Modo's brief expects and encourages. Here is the specific workflow:

### Architecture and Pre-Screening Phase (Claude Opus 4.6)

The high-token-consumption model (Opus 4.6) was used for the upfront architectural work that has the highest leverage on total project quality:

- **Data source investigation.** Opus researched ERCOT MIS data products, identified the specific report IDs (NP4-180-ER for DAM, NP6-785-ER for RTM), verified public accessibility, and confirmed the `gridstatus` library as the acquisition layer. This included inspecting the library source code to confirm output schemas (`Time`, `Interval Start`, `Interval End`, `Location`, `Location Type`, `Market`, `SPP`) and the Python ≥3.11 version constraint (`StrEnum` dependency).

- **Pre-screening data wrangling risks.** Opus identified six specific wrangling issues before any code was written: DST transition handling (23/25-hour days), missing interval detection, year boundary archive availability, Python version constraints, network dependency for initial pull, and data volume estimation. Each issue was documented with a concrete mitigation strategy. This pre-screening is the difference between a 4-hour project and a 12-hour debugging session.

- **Scope right-sizing.** Opus provided critical feedback on what to cut (fuel price correlation analysis, fiber connectivity modeling, individual resource nodes) and what to prioritize (the screener metrics themselves over the battery toy model) to keep the project within the 2–4 hour envelope.

- **Architecture specification.** The full `ARCHITECTURE.md` — pipeline design, metric definitions, separation of concerns, technology stack — was produced in collaboration with Opus to ensure the implementation phase could proceed without architectural ambiguity.

### Implementation Phase

[To be documented after implementation — will include specific AI tools and prompts used for code generation, debugging, and Streamlit layout.]

### Why This Matters

The AI workflow here is intentionally front-loaded on architecture and risk pre-screening. The thesis is that for a time-boxed assignment, the highest-ROI use of a high-capability model is not code generation — it's ensuring you don't build the wrong thing or discover a data wrangling blocker at hour 3 of a 4-hour window. Code generation is fast and correctable; architectural missteps and data surprises are not.
