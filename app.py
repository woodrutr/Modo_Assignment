from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import SETTINGS
from src.presentation.reviewer_table import (
    build_location_story,
    build_raw_metric_table,
    build_reviewer_table,
)
from src.presentation.texas_map import (
    build_location_map_frame,
    build_texas_location_map,
    extract_selected_location,
)


st.set_page_config(
    page_title="ERCOT Battery Flexibility Screener",
    page_icon=":material/electric_bolt:",
    layout="wide",
)

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
}
DISPLAY_FONT = "'SF Pro Display','Avenir Next','Segoe UI',sans-serif"
BODY_FONT = "'SF Pro Text','Avenir Next','Segoe UI',sans-serif"
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SCORE_SCALE = [
    [0.0, PALETTE["score_low"]],
    [0.45, PALETTE["score_mid"]],
    [1.0, PALETTE["score_high"]],
]
HEATMAP_SCALE = [
    [0.0, "#f3ede2"],
    [0.18, "#dfcfbf"],
    [0.45, "#b99674"],
    [0.72, "#7c6e70"],
    [1.0, "#355a66"],
]


def _available_years() -> list[int]:
    metric_files = SETTINGS.metrics_dir.glob("ercot_location_metrics_*.parquet")
    years = sorted(
        {
            int(path.stem.rsplit("_", maxsplit=1)[-1])
            for path in metric_files
            if path.stem.rsplit("_", maxsplit=1)[-1].isdigit()
        },
        reverse=True,
    )
    return years


@st.cache_data(show_spinner=False)
def load_artifacts(year: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics = pd.read_parquet(SETTINGS.metrics_path(year))
    daily_spreads = pd.read_parquet(SETTINGS.daily_spread_path(year))
    battery = pd.read_parquet(SETTINGS.battery_value_path(year))
    processed = pd.read_parquet(SETTINGS.processed_dam_path(year))
    return metrics, daily_spreads, battery, processed


def _apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --paper: {PALETTE["paper"]};
            --paper-alt: {PALETTE["paper_alt"]};
            --panel: {PALETTE["panel"]};
            --panel-strong: {PALETTE["panel_strong"]};
            --ink: {PALETTE["ink"]};
            --muted: {PALETTE["muted"]};
            --line: {PALETTE["line"]};
            --line-strong: {PALETTE["line_strong"]};
            --sea: {PALETTE["sea"]};
            --sea-soft: {PALETTE["sea_soft"]};
            --moss: {PALETTE["moss"]};
            --sand: {PALETTE["sand"]};
            --clay: {PALETTE["clay"]};
            --accent: {PALETTE["accent"]};
            --accent-soft: {PALETTE["accent_soft"]};
        }}
        html, body, [class*="css"] {{
            font-family: {BODY_FONT};
        }}
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(143, 163, 168, 0.12), transparent 32%),
                radial-gradient(circle at top right, rgba(127, 79, 63, 0.10), transparent 28%),
                linear-gradient(180deg, var(--paper) 0%, #efeae2 100%);
            color: var(--ink);
        }}
        header[data-testid="stHeader"] {{
            background: transparent;
        }}
        [data-testid="stToolbar"] {{
            right: 1rem;
        }}
        .block-container {{
            max-width: 1420px;
            padding-top: 1.15rem;
            padding-bottom: 4.2rem;
        }}
        [data-testid="stSidebar"] {{
            background:
                linear-gradient(180deg, rgba(247, 243, 238, 0.96) 0%, rgba(239, 233, 224, 0.96) 100%);
            border-right: 1px solid var(--line);
        }}
        [data-testid="stSidebar"] .block-container {{
            padding-top: 1.3rem;
        }}
        h1, h2, h3, h4 {{
            font-family: {DISPLAY_FONT};
            letter-spacing: -0.02em;
            color: var(--ink);
        }}
        .eyebrow {{
            color: var(--muted);
            font-size: 0.77rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }}
        .hero-shell {{
            background: linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,250,244,0.62));
            border: 1px solid var(--line);
            border-radius: 30px;
            padding: 1.7rem 1.8rem;
            box-shadow: 0 22px 42px rgba(31, 38, 40, 0.07);
            margin-bottom: 1.15rem;
        }}
        .hero-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1.8fr) minmax(270px, 0.9fr);
            gap: 1.2rem;
            align-items: start;
        }}
        .hero-title {{
            margin: 0;
            font-size: 2.35rem;
            line-height: 1.02;
        }}
        .hero-copy {{
            margin: 0.75rem 0 0;
            max-width: 64rem;
            color: var(--muted);
            font-size: 1.02rem;
            line-height: 1.52;
        }}
        .hero-side {{
            background: rgba(255,255,255,0.56);
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 1rem 1.05rem;
        }}
        .side-row {{
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.78rem;
        }}
        .side-row:last-child {{
            margin-bottom: 0;
        }}
        .side-label {{
            color: var(--muted);
            font-size: 0.84rem;
        }}
        .side-value {{
            color: var(--ink);
            font-size: 0.98rem;
            font-weight: 600;
            text-align: right;
        }}
        .summary-card {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 1rem 1.05rem;
            min-height: 8.6rem;
            box-shadow: 0 14px 32px rgba(31, 38, 40, 0.05);
        }}
        .summary-label {{
            color: var(--muted);
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }}
        .summary-value {{
            margin-top: 0.45rem;
            font-size: 1.28rem;
            font-weight: 700;
            line-height: 1.15;
            color: var(--ink);
        }}
        .summary-detail {{
            margin-top: 0.45rem;
            font-size: 0.92rem;
            color: var(--muted);
            line-height: 1.42;
        }}
        .section-head {{
            margin: 0 0 0.55rem 0;
        }}
        .section-title {{
            margin: 0;
            font-size: 1.35rem;
        }}
        .section-copy {{
            margin: 0.35rem 0 0;
            color: var(--muted);
            line-height: 1.45;
        }}
        .focus-shell {{
            background: linear-gradient(180deg, rgba(255,255,255,0.84), rgba(251,246,240,0.72));
            border: 1px solid var(--line);
            border-radius: 28px;
            padding: 1.2rem 1.2rem 1.1rem;
            box-shadow: 0 18px 36px rgba(31, 38, 40, 0.06);
        }}
        .focus-name {{
            margin: 0;
            font-size: 1.8rem;
            line-height: 1.05;
        }}
        .focus-meta {{
            margin-top: 0.35rem;
            color: var(--muted);
            font-size: 0.93rem;
        }}
        .focus-score {{
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin-top: 1rem;
            margin-bottom: 0.3rem;
        }}
        .focus-score-number {{
            font-size: 3rem;
            font-weight: 700;
            line-height: 1;
            color: var(--sea);
        }}
        .focus-score-label {{
            color: var(--muted);
            font-size: 0.95rem;
        }}
        .focus-pill-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.9rem 0 1rem;
        }}
        .focus-pill {{
            background: rgba(53, 90, 102, 0.08);
            color: var(--sea);
            border: 1px solid rgba(53, 90, 102, 0.14);
            border-radius: 999px;
            padding: 0.36rem 0.7rem;
            font-size: 0.8rem;
        }}
        .mini-stat {{
            background: rgba(255,255,255,0.7);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.8rem 0.9rem;
            min-height: 5.6rem;
        }}
        .mini-label {{
            color: var(--muted);
            font-size: 0.75rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .mini-value {{
            margin-top: 0.35rem;
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--ink);
        }}
        .mini-sub {{
            margin-top: 0.3rem;
            color: var(--muted);
            font-size: 0.85rem;
        }}
        .support-note {{
            margin-top: 0.95rem;
            color: var(--muted);
            font-size: 0.87rem;
            line-height: 1.45;
        }}
        .narrative-shell {{
            background: rgba(255,255,255,0.72);
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 1rem 1.05rem;
        }}
        .narrative-title {{
            margin: 0 0 0.45rem;
            font-size: 1rem;
            color: var(--ink);
        }}
        .narrative-copy {{
            margin: 0;
            color: var(--muted);
            line-height: 1.6;
            font-size: 0.97rem;
        }}
        .sidebar-title {{
            margin: 0;
            font-size: 1.45rem;
        }}
        .sidebar-copy {{
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.45;
            margin-bottom: 1rem;
        }}
        .sidebar-block {{
            background: rgba(255,255,255,0.52);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 0.95rem 1rem;
            margin-top: 0.9rem;
        }}
        .sidebar-block h4 {{
            margin: 0 0 0.35rem;
            font-size: 0.94rem;
        }}
        .sidebar-block p {{
            margin: 0;
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.45;
        }}
        .top-list {{
            margin-top: 0.5rem;
            display: grid;
            gap: 0.45rem;
        }}
        .top-item {{
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            font-size: 0.88rem;
            color: var(--ink);
        }}
        .top-item span:last-child {{
            color: var(--muted);
        }}
        .stTabs [role="tablist"] {{
            gap: 0.5rem;
        }}
        .stTabs [role="tab"] {{
            background: rgba(255,255,255,0.56);
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 0.45rem 0.9rem;
            color: var(--muted);
        }}
        .stTabs [aria-selected="true"] {{
            background: rgba(53, 90, 102, 0.10);
            color: var(--ink);
            border-color: rgba(53, 90, 102, 0.18);
        }}
        .stDownloadButton button, .stButton button {{
            background: rgba(255,255,255,0.7);
            color: var(--ink);
            border-radius: 999px;
            border: 1px solid var(--line);
            padding: 0.5rem 0.9rem;
        }}
        .stDownloadButton button:hover, .stButton button:hover {{
            border-color: rgba(53, 90, 102, 0.22);
            color: var(--sea);
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--line);
            border-radius: 22px;
            overflow: hidden;
            box-shadow: 0 10px 24px rgba(31, 38, 40, 0.04);
            background: rgba(255,255,255,0.74);
        }}
        details {{
            background: rgba(255,255,255,0.66);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 0.3rem 0.75rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _style_figure(figure: go.Figure, height: int) -> go.Figure:
    figure.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": BODY_FONT, "color": PALETTE["ink"]},
        margin={"l": 0, "r": 0, "t": 18, "b": 0},
        legend={"title": None, "orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    )
    figure.update_xaxes(
        gridcolor=PALETTE["line"],
        zeroline=False,
        title_font={"family": BODY_FONT},
        tickfont={"family": BODY_FONT},
    )
    figure.update_yaxes(
        gridcolor=PALETTE["line"],
        zeroline=False,
        title_font={"family": BODY_FONT},
        tickfont={"family": BODY_FONT},
    )
    return figure


def _render_hero(year: int, metrics: pd.DataFrame, reviewer_table: pd.DataFrame) -> None:
    top_row = reviewer_table.iloc[0]
    st.markdown(
        f"""
        <section class="hero-shell">
          <div class="hero-grid">
            <div>
              <div class="eyebrow">Battery-backed flexible load screening</div>
              <h1 class="hero-title">Find the ERCOT locations where price shape matters most.</h1>
              <p class="hero-copy">
                This screen ranks ERCOT hubs and load zones by the mix that matters for
                battery-backed flexible load: cheap charging windows, meaningful spike hours,
                and enough intra-day spread to create arbitrage headroom. Start on the map,
                compare the short list in the reviewer table, then inspect one location in detail.
              </p>
            </div>
            <aside class="hero-side">
              <div class="side-row"><span class="side-label">Artifact year</span><span class="side-value">{year}</span></div>
              <div class="side-row"><span class="side-label">Locations screened</span><span class="side-value">{len(metrics)}</span></div>
              <div class="side-row"><span class="side-label">Market surface</span><span class="side-value">ERCOT DAM hourly SPP</span></div>
              <div class="side-row"><span class="side-label">Current top screen</span><span class="side-value">{top_row["Location"]}</span></div>
            </aside>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_cards(raw_metric_table: pd.DataFrame, reviewer_table: pd.DataFrame) -> None:
    top_row = reviewer_table.iloc[0]
    best_charge = reviewer_table.loc[reviewer_table["Cheap Hours (%)"].idxmax()]
    widest_spread = reviewer_table.loc[reviewer_table["Daily Spread ($/MWh)"].idxmax()]
    highest_value = reviewer_table.loc[reviewer_table["Est. Battery Value ($/yr)"].idxmax()]

    cards = [
        (
            "Best overall screen",
            top_row["Location"],
            f"Score {top_row['Score']:.1f}",
            "Best composite balance of charging windows, spike hours, and spread.",
        ),
        (
            "Best charging profile",
            best_charge["Location"],
            f"{best_charge['Cheap Hours (%)']:.1f}% below $20/MWh",
            "Strongest availability of low-cost charging hours in the set.",
        ),
        (
            "Widest market shape",
            widest_spread["Location"],
            f"${widest_spread['Daily Spread ($/MWh)']:.1f}/MWh daily spread",
            "Largest average intraday price range across the year.",
        ),
        (
            "Highest stylized value",
            highest_value["Location"],
            f"${highest_value['Est. Battery Value ($/yr)']:,.0f}/yr",
            "Highest gross arbitrage value under the toy battery heuristic.",
        ),
    ]

    for column, card in zip(st.columns(4, gap="medium"), cards, strict=True):
        label, value, detail, note = card
        with column:
            st.markdown(
                f"""
                <div class="summary-card">
                  <div class="summary-label">{label}</div>
                  <div class="summary-value">{value}</div>
                  <div class="summary-detail"><strong>{detail}</strong><br>{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _initialize_location_focus(year: int, default_location: str, locations: list[str]) -> None:
    current_location = st.session_state.get("location_focus")
    current_year = st.session_state.get("location_focus_year")
    if current_year != year or current_location not in locations:
        st.session_state["location_focus_year"] = year
        st.session_state["location_focus"] = default_location


def _render_section_head(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="section-head">
          <div class="eyebrow">Analysis layer</div>
          <h3 class="section-title">{title}</h3>
          <p class="section-copy">{copy}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_focus_panel(
    selected_raw: pd.Series,
    selected_review: pd.Series,
    selected_map: pd.Series,
) -> None:
    chips = "".join(
        [f'<span class="focus-pill">{phrase.strip()}</span>' for phrase in selected_review["Readout"].split(",")]
    )
    st.markdown(
        f"""
        <div class="focus-shell">
          <div class="eyebrow">Selected location</div>
          <h2 class="focus-name">{selected_review["Location"]}</h2>
          <div class="focus-meta">{selected_raw["location"]} · {selected_raw["location_type"]} · Ranked #{int(selected_raw["rank"])}</div>
          <div class="focus-score">
            <div class="focus-score-number">{float(selected_raw["battery_opportunity_score"]):.1f}</div>
            <div class="focus-score-label">composite opportunity score</div>
          </div>
          <div class="focus-pill-row">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(2, gap="small")
    metric_cards = [
        (
            "Cheap charge hours",
            f'{float(selected_raw["pct_below_20"]):.1f}%',
            "share of hours below $20/MWh",
        ),
        (
            "Spike hours",
            f'{float(selected_raw["pct_above_100"]):.1f}%',
            "share of hours above $100/MWh",
        ),
        (
            "Daily spread",
            f'${float(selected_raw["avg_daily_spread"]):.1f}',
            "average intraday price range",
        ),
        (
            "Battery value",
            f'${float(selected_raw["annual_battery_gross_margin_usd"]):,.0f}',
            "stylized gross arbitrage value",
        ),
    ]
    for column, card in zip(metric_cols * 2, metric_cards, strict=True):
        label, value, sub = card
        with column:
            st.markdown(
                f"""
                <div class="mini-stat">
                  <div class="mini-label">{label}</div>
                  <div class="mini-value">{value}</div>
                  <div class="mini-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f"""
        <div class="narrative-shell" style="margin-top: 0.9rem;">
          <h4 class="narrative-title">What stands out</h4>
          <p class="narrative-copy">{build_location_story(selected_raw)}</p>
          <div class="support-note">
            Texas anchor: <strong>{selected_map["anchor_name"]}</strong>. {selected_map["anchor_note"]}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_map_section(map_frame: pd.DataFrame, selected_location: str, selected_year: int) -> object:
    _render_section_head(
        "Navigate the ERCOT geography",
        "Use the Texas map to move through hubs and load zones. Marker color reflects the composite score, while marker size reflects screen strength.",
    )
    return st.plotly_chart(
        build_texas_location_map(map_frame, selected_location),
        use_container_width=True,
        key=f"texas_map_{selected_year}",
        on_select="rerun",
        selection_mode=("points",),
    )


def _render_screen_table(reviewer_table: pd.DataFrame, raw_metric_table: pd.DataFrame, selected_year: int) -> None:
    _render_section_head(
        "Compare the short list",
        "The reviewer view is tuned for scanning and discussion. Raw metrics stay available for technical review and CSV export without crowding the main page.",
    )
    reviewer_view = reviewer_table.copy()
    reviewer_view["Location"] = reviewer_view["Location"] + " · " + reviewer_view["Code"]
    reviewer_view = reviewer_view.drop(columns=["Code"])

    reviewer_tab, raw_tab = st.tabs(["Reviewer View", "Raw Metrics"])
    with reviewer_tab:
        st.download_button(
            "Download reviewer CSV",
            reviewer_view.to_csv(index=False).encode("utf-8"),
            file_name=f"ercot_reviewer_table_{selected_year}.csv",
            mime="text/csv",
        )
        st.dataframe(
            reviewer_view,
            use_container_width=True,
            hide_index=True,
            height=520,
            column_config={
                "Rank": st.column_config.NumberColumn(format="%d", width="small"),
                "Location": st.column_config.TextColumn(width="medium"),
                "Score": st.column_config.NumberColumn(format="%.1f", width="small"),
                "Cheap Hours (%)": st.column_config.NumberColumn(format="%.1f"),
                "Spike Hours (%)": st.column_config.NumberColumn(format="%.1f"),
                "Daily Spread ($/MWh)": st.column_config.NumberColumn(format="%.1f"),
                "Est. Battery Value ($/yr)": st.column_config.NumberColumn(format="$%.0f"),
                "Readout": st.column_config.TextColumn(width="large"),
            },
        )
    with raw_tab:
        st.download_button(
            "Download raw metric CSV",
            raw_metric_table.to_csv(index=False).encode("utf-8"),
            file_name=f"ercot_raw_metric_table_{selected_year}.csv",
            mime="text/csv",
        )
        st.dataframe(
            raw_metric_table,
            use_container_width=True,
            hide_index=True,
            height=520,
            column_config={
                "rank": st.column_config.NumberColumn("rank", format="%d", width="small"),
                "battery_opportunity_score": st.column_config.NumberColumn(format="%.1f"),
                "avg_price": st.column_config.NumberColumn(format="%.1f"),
                "std_price": st.column_config.NumberColumn(format="%.1f"),
                "pct_negative": st.column_config.NumberColumn(format="%.1f"),
                "pct_below_20": st.column_config.NumberColumn(format="%.1f"),
                "pct_above_100": st.column_config.NumberColumn(format="%.1f"),
                "avg_daily_spread": st.column_config.NumberColumn(format="%.1f"),
                "annual_battery_gross_margin_usd": st.column_config.NumberColumn(format="$%.0f"),
                "pct_positive_value_days": st.column_config.NumberColumn(format="%.1f"),
            },
        )


def _render_rank_chart(reviewer_table: pd.DataFrame, selected_location: str) -> None:
    chart_frame = reviewer_table.sort_values("Score", ascending=True).copy()
    colors = [
        PALETTE["accent"] if code == selected_location else PALETTE["sea"]
        for code in chart_frame["Code"]
    ]
    figure = go.Figure(
        go.Bar(
            x=chart_frame["Score"],
            y=chart_frame["Location"],
            orientation="h",
            marker={"color": colors, "line": {"color": "rgba(255,255,255,0.5)", "width": 0}},
            customdata=chart_frame[["Code", "Readout"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "ERCOT code: %{customdata[0]}<br>"
                "Score: %{x:.1f}<br>"
                "%{customdata[1]}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(title="Opportunity score", range=[0, 100])
    figure.update_yaxes(title="")
    _style_figure(figure, 470)
    st.plotly_chart(figure, use_container_width=True)


def _render_frontier_chart(reviewer_table: pd.DataFrame, selected_location: str) -> None:
    chart_frame = reviewer_table.copy()
    figure = go.Figure(
        go.Scatter(
            x=chart_frame["Cheap Hours (%)"],
            y=chart_frame["Daily Spread ($/MWh)"],
            mode="markers",
            customdata=chart_frame[["Location", "Code", "Score", "Spike Hours (%)"]],
            marker={
                "size": 16 + chart_frame["Spike Hours (%)"] * 2.2,
                "color": chart_frame["Score"],
                "colorscale": SCORE_SCALE,
                "line": {"color": "rgba(255,255,255,0.7)", "width": 1.2},
                "cmin": 0,
                "cmax": 100,
                "colorbar": {"title": "Score"},
                "opacity": 0.9,
            },
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "ERCOT code: %{customdata[1]}<br>"
                "Score: %{customdata[2]:.1f}<br>"
                "Cheap hours: %{x:.1f}%<br>"
                "Daily spread: %{y:.1f} $/MWh<br>"
                "Spike hours: %{customdata[3]:.1f}%<extra></extra>"
            ),
        )
    )
    selected_row = chart_frame.loc[chart_frame["Code"] == selected_location]
    if not selected_row.empty:
        row = selected_row.iloc[0]
        figure.add_trace(
            go.Scatter(
                x=[row["Cheap Hours (%)"]],
                y=[row["Daily Spread ($/MWh)"]],
                mode="markers",
                marker={
                    "size": 34,
                    "color": "rgba(0,0,0,0)",
                    "line": {"color": PALETTE["accent"], "width": 2.8},
                },
                hoverinfo="skip",
                showlegend=False,
            )
        )
    figure.update_xaxes(title="Hours below $20/MWh (%)")
    figure.update_yaxes(title="Average daily spread ($/MWh)")
    _style_figure(figure, 470)
    st.plotly_chart(figure, use_container_width=True)


def _render_price_distribution(processed: pd.DataFrame, selected_location: str) -> None:
    location_frame = processed.loc[processed["location"] == selected_location].copy()
    location_frame["month"] = pd.Categorical(
        pd.to_datetime(location_frame["market_date"]).dt.strftime("%b"),
        categories=MONTH_ORDER,
        ordered=True,
    )
    figure = px.box(
        location_frame.sort_values("month"),
        x="month",
        y="spp",
        category_orders={"month": MONTH_ORDER},
        points=False,
    )
    figure.update_traces(
        fillcolor="rgba(54, 91, 103, 0.22)",
        line={"color": PALETTE["sea"], "width": 1.4},
        marker={"color": PALETTE["sea"]},
        hovertemplate="Month: %{x}<br>Price: %{y:.1f} $/MWh<extra></extra>",
    )
    figure.update_xaxes(title="")
    figure.update_yaxes(title="Price ($/MWh)")
    _style_figure(figure, 430)
    st.plotly_chart(figure, use_container_width=True)


def _render_daily_spread_heatmap(daily_spreads: pd.DataFrame, selected_location: str) -> None:
    location_spreads = daily_spreads.loc[daily_spreads["location"] == selected_location].copy()
    location_spreads["market_date"] = pd.to_datetime(location_spreads["market_date"])
    location_spreads["month"] = pd.Categorical(
        location_spreads["market_date"].dt.strftime("%b"),
        categories=MONTH_ORDER,
        ordered=True,
    )
    location_spreads["day"] = location_spreads["market_date"].dt.day
    heatmap_frame = (
        location_spreads.pivot(index="day", columns="month", values="daily_spread")
        .reindex(columns=MONTH_ORDER)
    )
    figure = px.imshow(
        heatmap_frame,
        aspect="auto",
        color_continuous_scale=HEATMAP_SCALE,
        origin="lower",
        labels={"x": "", "y": "Day of month", "color": "$/MWh"},
    )
    figure.update_xaxes(side="top")
    _style_figure(figure, 430)
    st.plotly_chart(figure, use_container_width=True)


def _render_selected_story(selected_raw: pd.Series) -> None:
    story_left, story_right = st.columns([1.5, 1], gap="large")
    with story_left:
        st.markdown(
            f"""
            <div class="narrative-shell">
              <h4 class="narrative-title">Commercial read</h4>
              <p class="narrative-copy">{build_location_story(selected_raw)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with story_right:
        metrics_table = pd.DataFrame(
            {
                "Metric": [
                    "Rank",
                    "Score",
                    "Average price",
                    "Cheap hours",
                    "Spike hours",
                    "Daily spread",
                    "Battery value",
                ],
                "Value": [
                    f"{int(selected_raw['rank'])}",
                    f"{float(selected_raw['battery_opportunity_score']):.1f}",
                    f"${float(selected_raw['avg_price']):.1f}/MWh",
                    f"{float(selected_raw['pct_below_20']):.1f}%",
                    f"{float(selected_raw['pct_above_100']):.1f}%",
                    f"${float(selected_raw['avg_daily_spread']):.1f}/MWh",
                    f"${float(selected_raw['annual_battery_gross_margin_usd']):,.0f}/yr",
                ],
            }
        )
        st.dataframe(metrics_table, use_container_width=True, hide_index=True, height=292)


def main() -> None:
    _apply_theme()
    available_years = _available_years()
    if not available_years:
        st.error(
            "No metric artifacts found. Run `python -m src.data.fetch` and "
            "`python -m src.analytics.metrics` first.",
        )
        return

    with st.sidebar:
        st.markdown('<div class="eyebrow">Navigation</div>', unsafe_allow_html=True)
        st.markdown('<h2 class="sidebar-title">Control Room</h2>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sidebar-copy">Use the controls below to navigate the historical screen. The interface is designed to move from geography to ranking to evidence.</p>',
            unsafe_allow_html=True,
        )
        selected_year = st.selectbox("Artifact year", options=available_years, index=0)

    metrics, daily_spreads, battery, processed = load_artifacts(selected_year)
    raw_metric_table = build_raw_metric_table(metrics, battery)
    reviewer_table = build_reviewer_table(metrics, battery)
    map_frame = build_location_map_frame(metrics, battery)
    default_location = str(metrics.iloc[0]["location"])
    location_options = metrics["location"].tolist()
    _initialize_location_focus(selected_year, default_location, location_options)

    with st.sidebar:
        st.selectbox("Focus settlement point", options=location_options, key="location_focus")
        st.markdown(
            """
            <div class="sidebar-block">
              <h4>Score logic</h4>
              <p>Higher scores reflect more low-price charging hours, enough spike hours to monetize discharge, and wider average daily spreads.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        top_rows = reviewer_table.head(5)
        top_markup = "".join(
            [
                f'<div class="top-item"><span>{int(row["Rank"])}. {row["Location"]}</span><span>{row["Score"]:.1f}</span></div>'
                for _, row in top_rows.iterrows()
            ]
        )
        st.markdown(
            f"""
            <div class="sidebar-block">
              <h4>Current short list</h4>
              <div class="top-list">{top_markup}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    selected_location = st.session_state["location_focus"]
    selected_raw = raw_metric_table.loc[raw_metric_table["location"] == selected_location].iloc[0]
    selected_review = reviewer_table.loc[reviewer_table["Code"] == selected_location].iloc[0]
    selected_map = map_frame.loc[map_frame["location"] == selected_location].iloc[0]

    _render_hero(selected_year, metrics, reviewer_table)
    _render_summary_cards(raw_metric_table, reviewer_table)

    overview_left, overview_right = st.columns([1.95, 1], gap="large")
    with overview_left:
        map_event = _render_map_section(map_frame, selected_location, selected_year)
    with overview_right:
        _render_focus_panel(selected_raw, selected_review, selected_map)

    clicked_location = extract_selected_location(
        map_event,
        map_frame,
        fallback_location=selected_location,
    )
    if clicked_location != st.session_state["location_focus"]:
        st.session_state["location_focus"] = clicked_location
        st.rerun()

    st.markdown("<div style='height: 0.55rem;'></div>", unsafe_allow_html=True)
    _render_screen_table(reviewer_table, raw_metric_table, selected_year)

    insight_left, insight_right = st.columns(2, gap="large")
    with insight_left:
        _render_section_head(
            "Who screens best overall",
            "Use this view to see where the composite score concentrates after balancing cheap hours, spike hours, and daily spread.",
        )
        _render_rank_chart(reviewer_table, selected_location)
    with insight_right:
        _render_section_head(
            "Where cheap hours meet spread",
            "A strong screen usually needs both ingredients: enough low-price hours to charge and enough daily spread to matter economically.",
        )
        _render_frontier_chart(reviewer_table, selected_location)

    deep_left, deep_right = st.columns([1.15, 0.85], gap="large")
    with deep_left:
        _render_section_head(
            f"{selected_review['Location']}: monthly price shape",
            "This chart shows how the selected location’s price distribution moves through the year, not just its average.",
        )
        _render_price_distribution(processed, selected_location)
    with deep_right:
        _render_section_head(
            f"{selected_review['Location']}: spread calendar",
            "This heatmap shows when the location produces wider daily spreads, which often matters more than the annual mean alone.",
        )
        _render_daily_spread_heatmap(daily_spreads, selected_location)

    _render_selected_story(selected_raw)

    with st.expander("Technical diagnostics", expanded=False):
        diagnostic_left, diagnostic_right = st.columns([1.4, 1], gap="large")
        with diagnostic_left:
            st.dataframe(raw_metric_table, hide_index=True, use_container_width=True)
        with diagnostic_right:
            st.json(
                {
                    "location": selected_location,
                    "rank": int(selected_raw["rank"]),
                    "battery_opportunity_score": round(
                        float(selected_raw["battery_opportunity_score"]),
                        2,
                    ),
                    "avg_price_usd_per_mwh": round(float(selected_raw["avg_price"]), 2),
                    "avg_daily_spread_usd_per_mwh": round(
                        float(selected_raw["avg_daily_spread"]),
                        2,
                    ),
                    "annual_battery_gross_margin_usd": round(
                        float(selected_raw["annual_battery_gross_margin_usd"]),
                        2,
                    ),
                },
                expanded=False,
            )


if __name__ == "__main__":
    main()
