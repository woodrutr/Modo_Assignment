# Architecture Specification

## Problem Statement

**Question:** Which ERCOT locations show the strongest conditions for battery-backed large-load flexibility, based on price volatility and low-price availability?

**Why it matters:** Large flexible loads (e.g., data centers, electrolyzers) co-located with battery storage can exploit price volatility to reduce effective energy costs. Locations with frequent negative or near-zero prices provide cheap charging windows, while high-price spikes create arbitrage revenue. A screener that quantifies these patterns across ERCOT settlement points directly informs siting and commercial structuring decisions.

---

## Data Source

### ERCOT Historical Settlement Point Prices

**Source:** ERCOT Market Information System (MIS), publicly available, no authentication required.

**Data Products Used:**

| Product | ERCOT ID | Content | Granularity | Format |
|---------|----------|---------|-------------|--------|
| Historical DAM Load Zone and Hub Prices | NP4-180-ER | Day-ahead SPPs for hubs + load zones | Hourly | Excel via ZIP |
| Historical RTM Load Zone and Hub Prices | NP6-785-ER | Real-time SPPs for hubs + load zones | 15-minute | Excel via ZIP |

**Access Method:** The `gridstatus` Python library (v0.34.0) provides `Ercot.get_dam_spp(year)` and `Ercot.get_rtm_spp(year)` methods that download these archives directly from ERCOT's public document server. No API key or market participant credentials are required.

**Coverage Period:** 12 months. Calendar year 2025 (January 1 – December 31). If 2025 archive is not yet available at run time, the pipeline falls back to 2024.

**Primary Market:** Day-Ahead Market (DAM) hourly SPPs. DAM is the primary analysis surface because:

- Hourly granularity aligns with battery charge/discharge cycle modeling
- DAM prices reflect forward expectations and are the basis for most commercial contracts
- Simpler temporal alignment (no 15-min interval aggregation required)

RTM data is included as a secondary validation layer but is not required for the screener to function.

### Settlement Points Included

**Trading Hubs:**

| Name | Description |
|------|-------------|
| HB_BUSAVG | Bus average (system-wide) |
| HB_HOUSTON | Houston hub |
| HB_NORTH | North hub |
| HB_SOUTH | South hub |
| HB_WEST | West hub |
| HB_PAN | Panhandle hub |
| HB_HUBAVG | Hub average |

**Load Zones:**

| Name | Description |
|------|-------------|
| LZ_HOUSTON | Houston load zone |
| LZ_NORTH | North load zone |
| LZ_SOUTH | South load zone |
| LZ_WEST | West load zone |
| LZ_AEN | AEN load zone |
| LZ_CPS | CPS load zone |
| LZ_LCRA | LCRA load zone |
| LZ_RAYBN | Rayburn load zone |

These ~15 locations are the complete set of hubs and load zones returned by `get_dam_spp()`. No individual resource nodes are included (that would require different data products and add complexity without proportional analytical value for a screener).

---

## Output Schema from gridstatus

The `get_dam_spp(year)` method returns a pandas DataFrame with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `Time` | datetime64[ns, tz] | Timestamp (timezone-aware, US/Central) |
| `Interval Start` | datetime64[ns, tz] | Start of delivery interval |
| `Interval End` | datetime64[ns, tz] | End of delivery interval |
| `Location` | str | Settlement point name (e.g., `HB_HOUSTON`, `LZ_NORTH`) |
| `Location Type` | str | One of: `Trading Hub`, `Load Zone` |
| `Market` | str | `DAY_AHEAD_HOURLY` |
| `SPP` | float64 | Settlement point price, $/MWh |

---

## Known Data Wrangling Issues

### 1. DST Transitions (Critical)

ERCOT operates on Central Prevailing Time (CPT). DST creates:

- **Spring forward (March):** 23-hour day. The 2:00 AM hour is skipped.
- **Fall back (November):** 25-hour day. The 2:00 AM hour is duplicated.

**Mitigation:** `gridstatus` handles DST internally via timezone-aware timestamps. After ingestion, all timestamps are converted to UTC for storage and computation. Local time is derived only at the Streamlit presentation layer.

### 2. Missing Intervals

ERCOT archives occasionally contain missing rows for specific hours/intervals.

**Mitigation:** After ingestion, validate expected row counts per location per day (24 for DAM, 96 for RTM). Log missing intervals. Metrics are computed on available data with explicit `NaN` handling — no forward-filling or interpolation.

### 3. Year Boundary for Archives

`get_dam_spp(year)` returns a full calendar year. If the current year's archive is not yet published, the call will fail.

**Mitigation:** The data pull script attempts the target year first, catches the exception, and falls back to the prior year. The actual date range used is recorded in pipeline metadata.

### 4. Python Version Constraint

`gridstatus` v0.34.0 requires Python ≥3.11 (uses `StrEnum` from the standard library, introduced in 3.11).

**Mitigation:** `requirements.txt` and `README.md` specify Python ≥3.11 explicitly. The setup instructions include version verification.

### 5. Network Dependency

`gridstatus` downloads ZIP/Excel files from ERCOT's document server at runtime. This requires internet access and is subject to ERCOT server availability.

**Mitigation:** The data pipeline caches raw downloads to `data/raw/` as Parquet files. If cached data exists and is current, the pipeline skips the download. This also enables offline development after the initial pull.

### 6. Data Volume

One year of DAM data for ~15 locations × 8,760 hours ≈ 131,400 rows. This fits comfortably in memory. No out-of-core processing needed.

---

## Computed Metrics

For each settlement point location, computed over the analysis period:

| Metric | Formula | Units | Purpose |
|--------|---------|-------|---------|
| `avg_price` | `mean(SPP)` | $/MWh | Baseline cost level |
| `std_price` | `std(SPP)` | $/MWh | Overall volatility |
| `pct_negative` | `count(SPP < 0) / count(SPP)` | % | Frequency of negative pricing (charging opportunity) |
| `pct_below_20` | `count(SPP < 20) / count(SPP)` | % | Frequency of low-cost hours |
| `pct_above_100` | `count(SPP > 100) / count(SPP)` | % | Frequency of price spikes (discharge opportunity) |
| `avg_daily_spread` | `mean(daily_max - daily_min)` | $/MWh | Average intra-day price range |
| `battery_opportunity_score` | Composite (see below) | 0–100 | Screener ranking metric |

### Battery Opportunity Score

A normalized composite ranking that combines:

```
score = w1 * norm(pct_negative)
      + w2 * norm(pct_below_20)
      + w3 * norm(avg_daily_spread)
      + w4 * norm(pct_above_100)
```

Where `norm()` is min-max normalization across all locations and `w1–w4` are configurable weights (default equal). The score ranks locations on a 0–100 scale. This is explicitly a relative ranking tool, not an absolute economic valuation.

---

## Optional: Battery Toy Model

### Stylized Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Load profile | Flat 100 MW, 24/7 | Stylized data-center-like baseload |
| Battery capacity | 100 MWh (1-hour duration at load rating) | Representative grid-scale Li-ion |
| Battery power | 100 MW charge / 100 MW discharge | Symmetric |
| Round-trip efficiency | 85% | Conservative Li-ion assumption |
| Charge window | 4 lowest-price hours per day | Heuristic, not optimized |
| Discharge window | 4 highest-price hours per day | Heuristic, not optimized |
| Cycle constraint | 1 full cycle per day | Simplification |

### Logic (Heuristic, Not Optimization)

For each day at each location:

1. Sort 24 hourly prices ascending
2. Charge hours = bottom 4 hours. Charging cost = `sum(price[0:4]) * 100 MWh / 0.85`
3. Discharge hours = top 4 hours. Avoided cost = `sum(price[-4:]) * 100 MWh`
4. Net benefit per day = `avoided_cost - charging_cost`
5. Annual avoided cost = `sum(daily_net_benefit)`

This is intentionally transparent and not a production-grade dispatch optimizer. It translates the price signal into a dollar figure that contextualizes the screener metrics.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Data Layer                          │
│                                                         │
│  ERCOT MIS ──► gridstatus ──► raw DataFrame             │
│                                  │                      │
│                                  ▼                      │
│                          data/raw/*.parquet              │
│                          (cached, immutable)             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Transform Layer                        │
│                                                         │
│  1. Validate schema + row counts                        │
│  2. Convert timestamps to UTC                           │
│  3. Tag location metadata (hub vs zone)                 │
│  4. Persist to data/processed/*.parquet                 │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Analytics Layer                        │
│                                                         │
│  1. Compute per-location summary metrics                │
│  2. Compute battery opportunity score                   │
│  3. (Optional) Run battery toy model                    │
│  4. Persist to data/metrics/*.parquet                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 Presentation Layer                      │
│                                                         │
│  Streamlit app (app.py)                                 │
│  - Screener table with sortable columns                 │
│  - Price distribution charts per location               │
│  - Daily spread heatmap                                 │
│  - Battery model results (if computed)                  │
│  - All timestamps displayed in US/Central               │
└─────────────────────────────────────────────────────────┘
```

### Separation of Concerns

- **`src/data/fetch.py`** — Data acquisition only. Downloads from ERCOT, writes raw Parquet. No business logic.
- **`src/data/validate.py`** — Schema enforcement, missing-interval detection, dtype coercion. Returns validated DataFrame or raises.
- **`src/analytics/metrics.py`** — All metric computations. Pure functions: DataFrame in, DataFrame out. No I/O.
- **`src/analytics/battery_model.py`** — Toy battery heuristic. Pure functions. No I/O.
- **`src/config.py`** — All constants: file paths (via pathlib), metric parameters, model assumptions. Single source of truth.
- **`app.py`** — Streamlit presentation only. Reads from `data/metrics/`, renders UI. No computation.

---

## Technology Stack

| Component | Choice | Version Constraint |
|-----------|--------|--------------------|
| Language | Python | ≥ 3.11 |
| Data acquisition | gridstatus | 0.34.0 |
| Data manipulation | pandas | ≥ 2.0 |
| Serialization | pyarrow | (for Parquet I/O) |
| Visualization | plotly | (interactive charts in Streamlit) |
| Presentation | streamlit | ≥ 1.30 |
| Configuration | pydantic | (typed settings validation) |

---

## What This Tool Is and Is Not

**Is:**

- A screening tool that ranks ERCOT locations by battery-friendly price patterns
- Built on publicly available, reproducible data
- Transparent in its assumptions and methodology
- Designed to run on any machine with Python ≥3.11 and internet access

**Is not:**

- A production siting model (ignores transmission constraints, interconnection queues, land costs, fiber/network proximity, water availability)
- A battery dispatch optimizer (uses heuristic, not mathematical optimization)
- A price forecast (descriptive analysis of historical patterns only)
- A substitute for nodal-level analysis (uses hub/zone aggregates, not individual buses)
