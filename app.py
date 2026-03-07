"""ERCOT Battery Flexibility Location Screener — Streamlit Dashboard.

Presentation layer only. Reads pre-computed Parquet artifacts from data/metrics/
and renders an interactive dashboard. No business logic or data transformation
lives in this file.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    BODY_FONT,
    DISPLAY_FONT,
    HEATMAP_SCALE,
    MONTH_ORDER,
    PALETTE,
    SCORE_SCALE,
    SETTINGS,
)
from src.presentation.reviewer_table import (
    build_location_narrative,
    build_reviewer_table,
    build_selected_metric_table,
    format_reviewer_table,
)
from src.presentation.texas_map import (
    build_location_map_frame,
    build_texas_location_map,
    extract_selected_location,
)


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ERCOT Battery Flexibility Screener",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS — Apple-inspired visual system
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
    /* ── Base ──────────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {{
        background-color: {PALETTE["paper"]};
        font-family: 'Inter', {BODY_FONT};
    }}

    /* Remove default Streamlit padding bloat */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }}

    /* ── Typography ───────────────────────────────────────────────── */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Inter', {DISPLAY_FONT};
        color: {PALETTE["ink"]};
        letter-spacing: -0.01em;
    }}

    h1 {{
        font-size: 1.75rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.25rem !important;
    }}

    h3 {{
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: {PALETTE["sea"]} !important;
        margin-top: 2.5rem !important;
        margin-bottom: 0.75rem !important;
    }}

    p, li, span, div {{
        color: {PALETTE["ink"]};
    }}

    /* ── Metric cards ─────────────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: {PALETTE["panel_strong"]};
        border: 1px solid {PALETTE["line"]};
        border-radius: 12px;
        padding: 16px 20px;
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 0.72rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: {PALETTE["muted"]} !important;
    }}

    [data-testid="stMetricValue"] {{
        font-size: 1.55rem !important;
        font-weight: 600 !important;
        color: {PALETTE["ink"]} !important;
    }}

    /* ── Tables ───────────────────────────────────────────────────── */
    .stDataFrame {{
        border-radius: 10px;
        overflow: hidden;
    }}

    [data-testid="stDataFrame"] th {{
        background-color: {PALETTE["paper_alt"]} !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        color: {PALETTE["muted"]} !important;
    }}

    /* ── Tabs ─────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0px;
        border-bottom: 1px solid {PALETTE["line_strong"]};
    }}

    .stTabs [data-baseweb="tab"] {{
        font-size: 0.82rem;
        font-weight: 500;
        color: {PALETTE["muted"]};
        padding: 8px 20px;
        border-bottom: 2px solid transparent;
    }}

    .stTabs [aria-selected="true"] {{
        color: {PALETTE["sea"]} !important;
        border-bottom-color: {PALETTE["sea"]} !important;
        font-weight: 600;
    }}

    /* ── Expanders ────────────────────────────────────────────────── */
    .streamlit-expanderHeader {{
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: {PALETTE["muted"]} !important;
    }}

    /* ── Dividers ─────────────────────────────────────────────────── */
    hr {{
        border: none;
        border-top: 1px solid {PALETTE["line"]};
        margin: 2rem 0;
    }}

    /* ── Sidebar ──────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background-color: {PALETTE["paper_alt"]};
    }}

    /* ── Caption styling ──────────────────────────────────────────── */
    .source-note {{
        font-size: 0.7rem;
        color: {PALETTE["muted"]};
        line-height: 1.5;
        margin-top: 0.25rem;
    }}

    .hero-subtitle {{
        font-size: 0.92rem;
        color: {PALETTE["muted"]};
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
        line-height: 1.6;
    }}

    /* ── Plotly chart containers ──────────────────────────────────── */
    [data-testid="stPlotlyChart"] {{
        border-radius: 12px;
        overflow: hidden;
    }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data
def load_metrics() -> pd.DataFrame:
    return pd.read_parquet(SETTINGS.metrics_path(SETTINGS.target_year))


@st.cache_data
def load_battery() -> pd.DataFrame:
    return pd.read_parquet(SETTINGS.battery_value_path(SETTINGS.target_year))


@st.cache_data
def load_spreads() -> pd.DataFrame:
    return pd.read_parquet(SETTINGS.daily_spread_path(SETTINGS.target_year))


@st.cache_data
def load_prices() -> pd.DataFrame:
    return pd.read_parquet(SETTINGS.processed_dam_path(SETTINGS.target_year))


metrics = load_metrics()
battery = load_battery()
spreads = load_spreads()
prices = load_prices()


# ─────────────────────────────────────────────────────────────────────────────
# Map frame (shared state)
# ─────────────────────────────────────────────────────────────────────────────

map_frame = build_location_map_frame(metrics, battery)
top_location = str(map_frame.iloc[0]["location"])

valid_locations = map_frame["location"].tolist()
if (
    "selected_location" not in st.session_state
    or st.session_state["selected_location"] not in valid_locations
):
    st.session_state["selected_location"] = top_location


# ─────────────────────────────────────────────────────────────────────────────
# § 1 — Hero header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("# ERCOT Battery Flexibility Screener")
st.markdown(
    '<p class="hero-subtitle">'
    "Which ERCOT locations show the strongest conditions for "
    "battery-backed large-load flexibility, based on price volatility "
    "and low-price availability?"
    "</p>",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# § 2 — Summary metrics (top-level KPIs)
# ─────────────────────────────────────────────────────────────────────────────

top_row = metrics.iloc[0]
best_spread_row = metrics.loc[metrics["avg_daily_spread"].idxmax()]
best_battery_row = battery.sort_values("annual_battery_gross_margin_usd", ascending=False).iloc[0]
best_neg_row = metrics.loc[metrics["pct_negative"].idxmax()]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Top Location",
        value=str(top_row["location"]),
        delta=f"Score {top_row['battery_opportunity_score']:.0f}/100",
    )

with col2:
    st.metric(
        label="Best Daily Spread",
        value=f"${best_spread_row['avg_daily_spread']:.1f}/MWh",
        delta=f"{best_spread_row['location']}",
    )

with col3:
    st.metric(
        label="Top Battery Margin",
        value=f"${best_battery_row['annual_battery_gross_margin_usd']:,.0f}/yr",
        delta=f"{best_battery_row['location']}",
    )

with col4:
    st.metric(
        label="Most Negative Hours",
        value=f"{best_neg_row['pct_negative']:.1f}%",
        delta=f"{best_neg_row['location']}",
    )

st.markdown(
    '<p class="source-note">'
    f"Data: ERCOT Day-Ahead Market settlement point prices · {SETTINGS.target_year} · "
    f"{int(metrics.iloc[0]['observations']):,} hourly observations per location · "
    f"{len(metrics)} locations"
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# § 3 — Map + location focus panel
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("### Geography")

map_col, detail_col = st.columns([3, 2], gap="large")

with map_col:
    st.caption("Click a marker to inspect a location.")
    current_location = st.session_state["selected_location"]
    selection = st.plotly_chart(
        build_texas_location_map(map_frame, current_location),
        use_container_width=True,
        key="texas_map",
        on_select="rerun",
        selection_mode="points",
    )

clicked_location = extract_selected_location(
    selection,
    map_frame,
    st.session_state["selected_location"],
)
if clicked_location != st.session_state["selected_location"]:
    st.session_state["selected_location"] = clicked_location
    st.rerun()

selected_location = st.session_state["selected_location"]
sel_metrics = metrics.loc[metrics["location"] == selected_location].iloc[0]
sel_battery = battery.loc[battery["location"] == selected_location]
sel_battery_row = sel_battery.iloc[0] if len(sel_battery) > 0 else None

with detail_col:
    st.markdown(f"#### {selected_location}")
    st.markdown(
        build_location_narrative(sel_metrics, sel_battery_row),
        unsafe_allow_html=True,
    )

    with st.expander("Raw metric values"):
        raw_metric_table = build_selected_metric_table(sel_metrics, sel_battery_row)
        st.dataframe(
            raw_metric_table,
            use_container_width=True,
            hide_index=True,
            height=min(38 * len(raw_metric_table) + 38, 560),
        )

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# § 4 — Screener table
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("### Location Rankings")

tab_reviewer, tab_raw = st.tabs(["Reviewer View", "Full Metrics"])

with tab_reviewer:
    reviewer_df = build_reviewer_table(metrics)
    formatted = format_reviewer_table(reviewer_df)
    st.dataframe(
        formatted,
        use_container_width=True,
        hide_index=True,
        height=min(42 * len(formatted) + 38, 680),
    )
    st.download_button(
        label="Download CSV",
        data=reviewer_df.to_csv(index=False),
        file_name="ercot_screener_reviewer.csv",
        mime="text/csv",
    )

with tab_raw:
    st.dataframe(
        metrics,
        use_container_width=True,
        hide_index=True,
        height=min(42 * len(metrics) + 38, 680),
    )
    st.download_button(
        label="Download CSV",
        data=metrics.to_csv(index=False),
        file_name="ercot_screener_raw_metrics.csv",
        mime="text/csv",
    )

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# § 5 — Evidence charts
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("### Evidence")

chart_tab1, chart_tab2, chart_tab3, chart_tab4 = st.tabs([
    "Score Breakdown",
    "Daily Spread Heatmap",
    "Price Distribution",
    "Battery Value",
])

# ── 5a: Score breakdown bar chart ────────────────────────────────────────────

with chart_tab1:
    score_components = metrics.sort_values("rank")[
        ["location", "norm_pct_negative", "norm_pct_below_20",
         "norm_avg_daily_spread", "norm_pct_above_100"]
    ].set_index("location")

    component_labels = {
        "norm_pct_negative": "Negative Hours",
        "norm_pct_below_20": "Hours < $20",
        "norm_avg_daily_spread": "Daily Spread",
        "norm_pct_above_100": "Hours > $100",
    }
    component_colors = [PALETTE["sea"], PALETTE["moss"], PALETTE["sand"], PALETTE["clay"]]

    fig_score = go.Figure()
    for i, (col, label) in enumerate(component_labels.items()):
        fig_score.add_trace(go.Bar(
            name=label,
            x=score_components.index,
            y=score_components[col] * 0.25,
            marker_color=component_colors[i],
            marker_line_width=0,
            hovertemplate=f"{label}: %{{y:.1f}}<extra></extra>",
        ))

    fig_score.update_layout(
        barmode="stack",
        height=380,
        margin={"l": 48, "r": 16, "t": 24, "b": 80},
        font={"family": f"'Inter', {BODY_FONT}", "size": 12, "color": PALETTE["ink"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis={
            "title": "Score (0–100)",
            "gridcolor": PALETTE["line"],
            "zeroline": False,
        },
        xaxis={"tickangle": -45},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11},
        },
    )
    st.plotly_chart(fig_score, use_container_width=True)

# ── 5b: Daily spread heatmap ────────────────────────────────────────────────

with chart_tab2:
    spread_pivot = spreads.copy()
    spread_pivot["market_date"] = pd.to_datetime(spread_pivot["market_date"])
    spread_pivot["month"] = spread_pivot["market_date"].dt.strftime("%b")
    spread_pivot["month_num"] = spread_pivot["market_date"].dt.month

    monthly_spread = (
        spread_pivot
        .groupby(["location", "month", "month_num"], as_index=False)["daily_spread"]
        .mean()
        .sort_values("month_num")
    )

    # Order locations by rank
    location_order = metrics.sort_values("rank")["location"].tolist()
    heat_data = monthly_spread.pivot(index="location", columns="month", values="daily_spread")
    heat_data = heat_data.reindex(index=location_order, columns=list(MONTH_ORDER))

    fig_heat = go.Figure(data=go.Heatmap(
        z=heat_data.values,
        x=list(MONTH_ORDER),
        y=heat_data.index.tolist(),
        colorscale=HEATMAP_SCALE,
        hovertemplate="<b>%{y}</b><br>%{x}: $%{z:.1f}/MWh<extra></extra>",
        colorbar={
            "title": {"text": "Avg Spread<br>($/MWh)", "font": {"size": 11}},
            "thickness": 12,
            "len": 0.6,
            "tickfont": {"size": 10},
            "outlinewidth": 0,
        },
    ))

    fig_heat.update_layout(
        height=420,
        margin={"l": 100, "r": 16, "t": 24, "b": 40},
        font={"family": f"'Inter', {BODY_FONT}", "size": 12, "color": PALETTE["ink"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis={"autorange": "reversed"},
        xaxis={"side": "top"},
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ── 5c: Price distribution (selected location vs system) ────────────────────

with chart_tab3:
    loc_prices = prices.loc[prices["location"] == selected_location, "spp"]
    sys_prices = prices.loc[prices["location"] == "HB_BUSAVG", "spp"]

    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=sys_prices,
        nbinsx=120,
        name="HB_BUSAVG (system)",
        marker_color=PALETTE["sea_soft"],
        opacity=0.6,
        hovertemplate="$%{x:.0f}/MWh: %{y} hours<extra></extra>",
    ))
    if selected_location != "HB_BUSAVG":
        fig_dist.add_trace(go.Histogram(
            x=loc_prices,
            nbinsx=120,
            name=selected_location,
            marker_color=PALETTE["accent"],
            opacity=0.7,
            hovertemplate="$%{x:.0f}/MWh: %{y} hours<extra></extra>",
        ))

    fig_dist.update_layout(
        barmode="overlay",
        height=380,
        margin={"l": 48, "r": 16, "t": 24, "b": 48},
        font={"family": f"'Inter', {BODY_FONT}", "size": 12, "color": PALETTE["ink"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={
            "title": "DAM Price ($/MWh)",
            "gridcolor": PALETTE["line"],
            "zeroline": True,
            "zerolinecolor": PALETTE["line_strong"],
            "range": [-50, 250],
        },
        yaxis={
            "title": "Hours",
            "gridcolor": PALETTE["line"],
            "zeroline": False,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11},
        },
    )
    st.plotly_chart(fig_dist, use_container_width=True)

# ── 5d: Battery value comparison ─────────────────────────────────────────────

with chart_tab4:
    batt_sorted = battery.merge(
        metrics[["location", "rank"]], on="location"
    ).sort_values("rank")

    bar_colors = [
        PALETTE["accent"] if loc == selected_location else PALETTE["sea_soft"]
        for loc in batt_sorted["location"]
    ]

    fig_batt = go.Figure(data=go.Bar(
        x=batt_sorted["location"],
        y=batt_sorted["annual_battery_gross_margin_usd"],
        marker_color=bar_colors,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}/yr<extra></extra>",
    ))

    fig_batt.update_layout(
        height=380,
        margin={"l": 60, "r": 16, "t": 24, "b": 80},
        font={"family": f"'Inter', {BODY_FONT}", "size": 12, "color": PALETTE["ink"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis={
            "title": "Annual Gross Margin ($)",
            "gridcolor": PALETTE["line"],
            "zeroline": False,
            "tickformat": "$,.0f",
        },
        xaxis={"tickangle": -45},
    )
    st.plotly_chart(fig_batt, use_container_width=True)
    st.caption(
        "Stylized heuristic: 100 MW battery, 4h charge/discharge cycle, "
        "85% round-trip efficiency. Not a dispatch optimization."
    )


# ─────────────────────────────────────────────────────────────────────────────
# § 6 — Methodology note (collapsed)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")

with st.expander("Methodology & assumptions"):
    st.markdown(f"""
**Data source:** ERCOT Day-Ahead Market settlement point prices for {SETTINGS.target_year},
accessed via the `gridstatus` open-source library. {int(metrics.iloc[0]['observations']):,}
hourly observations per location across {len(metrics)} trading hubs and load zones.

**Battery opportunity score** is a normalized composite (0–100) of four equally-weighted
components: frequency of negative pricing, frequency of sub-$20 hours, average daily
price spread, and frequency of $100+ spikes. Min-max normalization across all locations.
This is a relative ranking, not an absolute economic valuation.

**Battery toy model** uses a simple heuristic — charge in the 4 cheapest hours, discharge
in the 4 most expensive hours each day — with 85% round-trip efficiency and a stylized
100 MW system. This is not dispatch optimization and excludes ancillary service revenue,
degradation, and capacity constraints beyond a single daily cycle.

**Limitations:** Hub/zone granularity only (not nodal). Historical patterns, not forecasts.
No infrastructure proximity (fiber, substation, water). No transmission constraints.
See ARCHITECTURE.md for the full specification.
    """)

st.markdown(
    '<p class="source-note" style="text-align:center; margin-top:2rem;">'
    "ERCOT Battery Flexibility Screener · Built with Streamlit + Plotly · "
    "Data via gridstatus"
    "</p>",
    unsafe_allow_html=True,
)
