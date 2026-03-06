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
- **Map points are representative anchors.** The interactive Texas map places each ERCOT hub or load zone on a representative lat/lon anchor guided by the official [ERCOT maps](https://www.ercot.com/news/mediakit/maps) plus the relevant metro or service-area center. These are not official ERCOT centroids or nodal coordinates.

## What the Tool Is and Is Not

**Is:** A transparent, reproducible screener that ranks ERCOT locations by battery-friendly price characteristics using public data and defensible metrics.

**Is not:** A production siting model, a price forecast, a dispatch optimizer, or a substitute for nodal-level commercial analysis.

## Latest Local Run Snapshot

Validated on **March 6, 2026** against ERCOT **2025** DAM settlement point prices:

- 131,400 hourly observations across 15 hubs and load zones
- Zero missing intervals and zero duplicate intervals after UTC normalization
- Top-ranked locations by composite battery opportunity score:

| Rank | Location | Score | Avg Daily Spread ($/MWh) | Stylized Annual Battery Gross Margin ($) |
|------|----------|-------|--------------------------|------------------------------------------|
| 1 | `HB_PAN` | 64.0 | 67.0 | 5,902,409 |
| 2 | `LZ_WEST` | 56.8 | 81.9 | 7,676,929 |
| 3 | `LZ_LCRA` | 49.1 | 79.2 | 7,063,245 |
| 4 | `HB_WEST` | 43.8 | 72.3 | 6,437,277 |
| 5 | `LZ_CPS` | 37.2 | 74.0 | 6,505,067 |

This is a screen, not a claim that those sites are commercially superior in absolute terms. The result means these locations exhibited stronger historical combinations of cheap charging windows, spike hours, and daily arbitrage spread than the rest of the ERCOT hub/zone set during 2025.

## How to Run

### Prerequisites

- Python 3.13 recommended for exact reproducibility in this repo (verified locally with `gridstatus==0.29.1`)
- Internet access for initial ERCOT data download (subsequent runs use cached Parquet files)

### Setup

```bash
# Verify Python version
python --version  # Verified locally on 3.13

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

This downloads ERCOT DAM SPP data from the public archive, validates the hourly grid, converts timestamps to UTC, and writes canonical Parquet artifacts to `data/raw/` and `data/processed/`. Takes ~1-2 minutes on first run. Subsequent runs skip the download if cached data is current.

### Build Metric Artifacts

```bash
python -m src.analytics.metrics
```

This computes per-location screener metrics, daily spread panels, and the stylized battery value summary into `data/metrics/`.

### Run the Screener

```bash
streamlit run app.py
```

Opens a browser with the interactive dashboard. The UI reads precomputed Parquet artifacts only; it does not download or recompute business logic. All timestamps are displayed in US/Central time.

The app now includes an interactive Texas map. Clicking a marker updates the location detail view and metric summary for that hub or load zone.

The main screening table is split into two views:

- **Reviewer View** — narrower, human-readable column names plus a short qualitative readout for each location
- **Raw Metrics** — the original machine-readable schema for technical inspection and export

Both views can be downloaded as CSV directly from the app.

### macOS Double-Click Runner

On macOS, you can also double-click `Run_ERCOT_Screener.command`. It will:

- create `.venv` if needed
- install pinned dependencies if missing
- fetch ERCOT data if processed artifacts do not exist yet
- rebuild screener metrics
- launch the Streamlit app

The first run may take a minute or two and requires internet access.

### Windows Double-Click Runner

On Windows, double-click `Run_ERCOT_Screener.bat`. It delegates to
`Run_ERCOT_Screener.ps1` and will:

- create a Windows-specific virtual environment at `.venv-win`
- install pinned dependencies if missing
- fetch ERCOT data if processed artifacts do not exist yet
- rebuild screener metrics
- launch the Streamlit app in the default browser

The Windows launcher uses a separate `.venv-win` directory on purpose so it does not
conflict with the macOS/Linux `.venv`.

### Run Tests

```bash
python -m unittest
```

## Repository Structure

```
ercot-battery-screener/
├── README.md                    # This file
├── ARCHITECTURE.md              # Full technical specification
├── requirements.txt             # Pinned dependencies
├── AI-Assistant.txt             # Notes on how AI/personality constraints shaped the build
├── Run_ERCOT_Screener.bat       # Windows double-click launcher
├── Run_ERCOT_Screener.ps1       # Windows bootstrap logic
├── Run_ERCOT_Screener.command   # macOS double-click launcher
├── app.py                       # Streamlit dashboard (presentation only)
├── src/
│   ├── __init__.py
│   ├── config.py                # Constants, paths, parameters (single source of truth)
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fetch.py             # ERCOT data acquisition → raw Parquet
│   │   └── validate.py          # Schema enforcement, missing-interval detection
│   ├── presentation/
│   │   ├── __init__.py
│   │   ├── reviewer_table.py    # Human-readable screen table builders and summaries
│   │   └── texas_map.py         # Interactive Texas map helpers and selection parsing
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
│   ├── test_battery_model.py    # Unit tests for battery heuristic
│   ├── test_reviewer_table.py   # Unit tests for reviewer-facing table builders
│   ├── test_texas_map.py        # Unit tests for map anchors and selection parsing
│   └── test_validate.py         # Unit tests for validation logic
└── .gitignore
```

## How AI Accelerated This Workflow

This project was built using AI tools throughout the process, as Modo's brief expects and encourages. Here is the specific workflow:

### Architecture and Pre-Screening Phase (Claude Opus 4.6)

The high-token-consumption model (Opus 4.6) was used for the upfront architectural work that has the highest leverage on total project quality:

- **Data source investigation.** Opus researched ERCOT MIS data products, identified the specific report IDs (NP4-180-ER for DAM, NP6-785-ER for RTM), verified public accessibility, and confirmed the `gridstatus` library as the acquisition layer. This included inspecting the library source code to confirm output schemas (`Time`, `Interval Start`, `Interval End`, `Location`, `Location Type`, `Market`, `SPP`) and identifying package-version constraints that needed to be reconciled with the local Python environment during implementation.

- **Pre-screening data wrangling risks.** Opus identified six specific wrangling issues before any code was written: DST transition handling (23/25-hour days), missing interval detection, year boundary archive availability, Python version constraints, network dependency for initial pull, and data volume estimation. Each issue was documented with a concrete mitigation strategy. This pre-screening is the difference between a 4-hour project and a 12-hour debugging session.

- **Scope right-sizing.** Opus provided critical feedback on what to cut (fuel price correlation analysis, fiber connectivity modeling, individual resource nodes) and what to prioritize (the screener metrics themselves over the battery toy model) to keep the project within the 2–4 hour envelope.

- **Architecture specification.** The full `ARCHITECTURE.md` — pipeline design, metric definitions, separation of concerns, technology stack — was produced in collaboration with Opus to ensure the implementation phase could proceed without architectural ambiguity.

### Implementation Phase (Codex)

Codex was used as an implementation agent after the architecture was fixed. The workflow was constrained to preserve a single source of truth and strict separation of concerns:

- **Single-truth-first implementation.** Codex started with `src/config.py` so years, paths, metric thresholds, artifact names, and battery assumptions were defined once and consumed everywhere else.
- **Validation before analytics.** The ingestion layer was implemented to raise hard errors on duplicate or missing hourly intervals instead of filling or smoothing over gaps.
- **Pure analytics modules.** Screener metrics and the battery heuristic were implemented as DataFrame-in/DataFrame-out functions with no file I/O, making them directly testable.
- **Presentation last.** The Streamlit app was built only after raw, processed, and metric artifacts had a stable contract. The UI reads Parquet and never owns core logic.
- **Workflow traceability.** The repo includes `AI-Assistant.txt` documenting where the architectural instructions changed implementation decisions and reduced error risk.

### Why This Matters

The AI workflow here is intentionally front-loaded on architecture and risk pre-screening. The thesis is that for a time-boxed assignment, the highest-ROI use of a high-capability model is not code generation — it's ensuring you don't build the wrong thing or discover a data wrangling blocker at hour 3 of a 4-hour window. Code generation is fast and correctable; architectural missteps and data surprises are not.
