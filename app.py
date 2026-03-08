"""ERCOT flexibility opportunity screener."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    BODY_FONT,
    DISPLAY_FONT,
    DURATION_OPTIONS,
    EFFECTIVE_PRICE_SCALE,
    HEATMAP_SCALE,
    LENS_KEYS,
    MONTH_ORDER,
    PALETTE,
    PROFILE_LABELS,
    PROFILE_ORDER,
    SETTINGS,
    lens_label,
    lens_metric_column,
)
from src.presentation.reviewer_table import (
    build_next_step_prompt,
    build_rank_context,
    build_reviewer_table,
    build_selected_metric_table,
    format_reviewer_table,
)
from src.presentation.texas_map import (
    build_location_map_frame,
    build_texas_location_map,
    extract_selected_location,
)


st.set_page_config(
    page_title="ERCOT Flexibility Opportunity Screener",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    f"""
<style>
    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(255,255,255,0.78), rgba(255,255,255,0) 28%),
            linear-gradient(180deg, #f6f2eb 0%, #efe8dd 48%, #ece5da 100%);
        color: {PALETTE["ink"]};
        font-family: {BODY_FONT};
    }}

    .block-container {{
        max-width: 1240px;
        padding-top: 1.55rem;
        padding-bottom: 2.5rem;
    }}

    [data-testid="stAppViewContainer"] > .main {{
        padding-top: 0.2rem;
    }}

    header[data-testid="stHeader"] {{
        background: rgba(246, 242, 235, 0.84);
        border-bottom: 1px solid {PALETTE["line"]};
        backdrop-filter: blur(12px);
    }}

    h1, h2, h3, h4 {{
        color: {PALETTE["ink"]};
        font-family: {DISPLAY_FONT};
        letter-spacing: -0.02em;
    }}

    h1 {{
        font-size: 2.1rem !important;
        font-weight: 650 !important;
        margin-bottom: 0.2rem !important;
    }}

    h3 {{
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: {PALETTE["sea"]} !important;
        margin-top: 1.6rem !important;
        margin-bottom: 0.7rem !important;
    }}

    [data-testid="stMetric"] {{
        background: rgba(255, 252, 247, 0.82);
        border: 1px solid {PALETTE["line"]};
        border-radius: 18px;
        padding: 15px 18px;
        box-shadow: 0 10px 24px rgba(31, 38, 40, 0.05);
    }}

    [data-testid="stMetricLabel"] {{
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: {PALETTE["muted"]} !important;
        font-size: 0.70rem !important;
        font-weight: 600 !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        line-height: 1.25 !important;
        min-height: 2.4em;
    }}

    [data-testid="stMetricLabel"] > div,
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] label,
    [data-testid="stMetricLabel"] span {{
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        display: block !important;
        word-break: break-word !important;
    }}

    [data-testid="stMetricValue"] {{
        color: {PALETTE["ink"]} !important;
        font-size: 1.55rem !important;
        font-weight: 620 !important;
    }}

    [data-testid="stDataFrame"] {{
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid {PALETTE["line"]};
        background: rgba(255, 252, 247, 0.76);
    }}

    [data-testid="stDataFrame"] th {{
        background-color: rgba(233, 226, 215, 0.92) !important;
        color: {PALETTE["muted"]} !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.25rem;
        border-bottom: 1px solid {PALETTE["line_strong"]};
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 999px 999px 0 0;
        padding: 0.55rem 1rem;
        color: {PALETTE["muted"]};
    }}

    .stTabs [aria-selected="true"] {{
        color: {PALETTE["sea"]} !important;
        font-weight: 600;
        background: rgba(255, 252, 247, 0.66);
    }}

    .hero-subtitle {{
        color: {PALETTE["muted"]};
        max-width: 860px;
        line-height: 1.55;
        margin-top: 0;
        margin-bottom: 0.65rem;
    }}

    .hero-kicker {{
        color: {PALETTE["sea"]};
        font-family: {DISPLAY_FONT};
        font-size: 1rem;
        font-weight: 650;
        letter-spacing: -0.02em;
        margin-bottom: 0.3rem;
    }}

    .hero-title {{
        color: {PALETTE["ink"]};
        font-family: {DISPLAY_FONT};
        font-size: 2.4rem;
        font-weight: 675;
        letter-spacing: -0.03em;
        line-height: 1.02;
        margin: 0 0 0.45rem 0;
        max-width: 900px;
    }}

    [data-testid="stRadio"] {{
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 0;
    }}

    [data-testid="stRadio"] > div {{
        background: rgba(255, 252, 247, 0.72);
        border: 1px solid {PALETTE["line"]};
        border-radius: 20px;
        padding: 0.9rem 1rem 0.8rem 1rem;
        box-shadow: 0 12px 28px rgba(31, 38, 40, 0.05);
    }}

    [data-testid="stSkeleton"],
    .stSkeleton,
    [class*="skeleton"] {{
        display: none !important;
    }}

    .section-caption {{
        color: {PALETTE["muted"]};
        font-size: 0.8rem;
        line-height: 1.45;
        margin-top: 0.6rem;
    }}

    .control-note {{
        color: {PALETTE["muted"]};
        font-size: 0.92rem;
        line-height: 1.5;
        padding: 0.9rem 0 0 0.15rem;
        max-width: 34rem;
    }}

    .chart-kicker {{
        color: {PALETTE["ink"]};
        font-family: {DISPLAY_FONT};
        font-size: 0.95rem;
        font-weight: 620;
        margin-bottom: 0.45rem;
    }}

    .panel-card {{
        background: rgba(255, 252, 247, 0.76);
        border: 1px solid {PALETTE["line"]};
        border-radius: 20px;
        padding: 1rem 1.1rem;
        box-shadow: 0 12px 28px rgba(31, 38, 40, 0.05);
    }}

    .panel-title {{
        color: {PALETTE["sea"]};
        font-family: {DISPLAY_FONT};
        font-size: 0.95rem;
        font-weight: 630;
        margin-bottom: 0.35rem;
    }}

    .panel-body {{
        color: {PALETTE["ink"]};
        line-height: 1.58;
        margin: 0;
    }}

    .panel-list {{
        color: {PALETTE["ink"]};
        line-height: 1.58;
        margin: 0;
        padding-left: 1.1rem;
    }}

    .summary-stack {{
        background: rgba(255, 252, 247, 0.82);
        border: 1px solid {PALETTE["line"]};
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 10px 24px rgba(31, 38, 40, 0.05);
        margin-bottom: 0.95rem;
    }}

    .summary-row {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.95rem 1rem;
        border-bottom: 1px solid rgba(31, 38, 40, 0.07);
    }}

    .summary-row:last-child {{
        border-bottom: none;
    }}

    .summary-key {{
        color: {PALETTE["muted"]};
        font-size: 0.76rem;
        font-weight: 620;
        letter-spacing: 0.08em;
        line-height: 1.35;
        text-transform: uppercase;
        max-width: 52%;
    }}

    .summary-value {{
        color: {PALETTE["ink"]};
        font-family: {DISPLAY_FONT};
        font-size: 1.55rem;
        font-weight: 660;
        letter-spacing: -0.03em;
        line-height: 1.05;
        white-space: nowrap;
        text-align: right;
        flex-shrink: 0;
    }}

    .benchmark-card {{
        background: rgba(255, 252, 247, 0.82);
        border: 1px solid {PALETTE["line"]};
        border-radius: 18px;
        padding: 0.95rem 1rem;
        box-shadow: 0 10px 24px rgba(31, 38, 40, 0.05);
        margin-bottom: 0.85rem;
    }}

    .benchmark-title {{
        color: {PALETTE["muted"]};
        font-size: 0.74rem;
        font-weight: 620;
        letter-spacing: 0.08em;
        line-height: 1.35;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }}

    .benchmark-selected {{
        color: {PALETTE["ink"]};
        font-family: {DISPLAY_FONT};
        font-size: 1.55rem;
        font-weight: 660;
        letter-spacing: -0.03em;
        line-height: 1.05;
        margin-bottom: 0.3rem;
    }}

    .benchmark-median {{
        color: {PALETTE["muted"]};
        font-size: 0.92rem;
        line-height: 1.45;
    }}

    [data-testid="stPlotlyChart"] {{
        border-radius: 18px;
        overflow: hidden;
    }}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def _read_parquet_cached(path_str: str, mtime_ns: int) -> pd.DataFrame:
    _ = mtime_ns
    return pd.read_parquet(path_str)


def _required_metric_columns() -> set[str]:
    required = {
        "location",
        "location_type",
        "best_fit_lens",
        "best_fit_rank",
        "observations",
    }
    for profile_key, duration_hours in LENS_KEYS:
        required.update(
            {
                lens_metric_column(profile_key, duration_hours, "rank"),
                lens_metric_column(profile_key, duration_hours, "score"),
                lens_metric_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "annual_cost_reduction_pct"),
                lens_metric_column(profile_key, duration_hours, "annual_cost_reduction_usd_per_mw_year"),
                lens_metric_column(profile_key, duration_hours, "effective_annual_cost_usd_per_mw_year"),
                lens_metric_column(profile_key, duration_hours, "baseline_annual_cost_usd_per_mw_year"),
                lens_metric_column(profile_key, duration_hours, "profitable_day_share"),
                lens_metric_column(profile_key, duration_hours, "p95_active_hour_price_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "p95_active_hour_effective_price_usd_per_mwh"),
                lens_metric_column(profile_key, duration_hours, "p95_active_hour_reduction_pct"),
            }
        )
    return required


def _load_parquet_artifact(path: Path) -> pd.DataFrame:
    return _read_parquet_cached(str(path), path.stat().st_mtime_ns)


def _stop_for_schema_error(path: Path, missing_columns: list[str]) -> None:
    st.error(
        "The dashboard found a stale metrics artifact that does not match the V3 schema. "
        "Rebuild the analytics artifacts, then refresh the app."
    )
    st.code(f".venv/bin/python -m src.analytics.metrics --year {SETTINGS.target_year}")
    st.caption(f"Artifact: {path}")
    st.caption(f"Missing columns: {', '.join(missing_columns[:12])}")
    st.stop()


def load_metrics() -> pd.DataFrame:
    path = SETTINGS.metrics_path(SETTINGS.target_year)
    metrics_frame = _load_parquet_artifact(path)
    missing_columns = sorted(_required_metric_columns().difference(metrics_frame.columns))
    if missing_columns:
        _stop_for_schema_error(path, missing_columns)
    return metrics_frame


def load_daily_profile_windows() -> pd.DataFrame:
    path = SETTINGS.daily_profile_windows_path(SETTINGS.target_year)
    daily_frame = _load_parquet_artifact(path)
    required = {
        "location",
        "profile",
        "local_date",
        "4h_profitable",
        "8h_profitable",
        "4h_best_spread_usd_per_mwh",
        "8h_best_spread_usd_per_mwh",
    }
    missing_columns = sorted(required.difference(daily_frame.columns))
    if missing_columns:
        _stop_for_schema_error(path, missing_columns)
    return daily_frame


def load_hourly_profile_shape() -> pd.DataFrame:
    path = SETTINGS.hourly_profile_shape_path(SETTINGS.target_year)
    shape_frame = _load_parquet_artifact(path)
    required = {
        "location",
        "profile",
        "duration_hours",
        "local_month_label",
        "local_hour",
        "market_price_avg_usd_per_mwh",
        "effective_active_price_avg_usd_per_mwh",
    }
    missing_columns = sorted(required.difference(shape_frame.columns))
    if missing_columns:
        _stop_for_schema_error(path, missing_columns)
    return shape_frame


metrics = load_metrics()
daily_windows = load_daily_profile_windows()
hourly_shape = load_hourly_profile_shape()


def _lens_column(profile_key: str, duration_hours: int, metric_name: str) -> str:
    return lens_metric_column(profile_key, duration_hours, metric_name)


def _init_session_state() -> None:
    if "selected_profile" not in st.session_state:
        st.session_state["selected_profile"] = PROFILE_ORDER[0]
    if "selected_duration" not in st.session_state:
        st.session_state["selected_duration"] = DURATION_OPTIONS[0]

    top_location = (
        metrics.sort_values(
            _lens_column(st.session_state["selected_profile"], st.session_state["selected_duration"], "rank"),
            kind="mergesort",
        )
        .iloc[0]["location"]
    )
    valid_locations = metrics["location"].tolist()
    if (
        "selected_location" not in st.session_state
        or st.session_state["selected_location"] not in valid_locations
    ):
        st.session_state["selected_location"] = str(top_location)


def _active_metrics_frame(profile_key: str, duration_hours: int) -> pd.DataFrame:
    rank_column = _lens_column(profile_key, duration_hours, "rank")
    return metrics.sort_values([rank_column, "location"], kind="mergesort").reset_index(drop=True)


def _render_controls() -> tuple[str, int]:
    st.markdown('<div class="hero-kicker">Annual Triage Tool</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="hero-title">ERCOT Flexibility Opportunity Screener</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-subtitle">This tool is designed to help developers, investors, and large-load planners '
        'identify which ERCOT regions appear most sensitive to flexibility, and therefore where deeper '
        'forward-looking modeling is most likely to add value.</p>',
        unsafe_allow_html=True,
    )

    controls_profile, controls_duration, controls_note = st.columns([1.75, 1.05, 2.25], gap="large")
    with controls_profile:
        selected_profile = st.radio(
            "Load profile",
            options=list(PROFILE_ORDER),
            format_func=lambda key: PROFILE_LABELS[key],
            horizontal=True,
            key="selected_profile",
        )
    with controls_duration:
        selected_duration = st.radio(
            "Primary battery duration",
            options=list(DURATION_OPTIONS),
            format_func=lambda duration: f"{duration}h",
            horizontal=True,
            key="selected_duration",
        )
    with controls_note:
        st.markdown(
            '<div class="control-note">Use the active lens to decide where deeper analysis should go first. '
            'The screen stays annual and historical, while the evidence view shows why a region screens as '
            'flexibility-sensitive.</div>',
            unsafe_allow_html=True,
        )
    return selected_profile, int(selected_duration)


def _render_hero_cards(active_frame: pd.DataFrame, profile_key: str, duration_hours: int) -> None:
    score_column = _lens_column(profile_key, duration_hours, "score")
    price_column = _lens_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh")
    reduction_column = _lens_column(profile_key, duration_hours, "annual_cost_reduction_pct")
    p95_column = _lens_column(profile_key, duration_hours, "p95_active_hour_reduction_pct")

    leader = active_frame.iloc[0]
    lowest_price = active_frame.loc[active_frame[price_column].idxmin()]
    highest_reduction = active_frame.loc[active_frame[reduction_column].idxmax()]
    strongest_tail = active_frame.loc[active_frame[p95_column].idxmax()]

    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        st.metric("Look here first", str(leader["location"]), delta=f"Score {leader[score_column]:.1f}")
    with col2:
        st.metric("Lowest effective delivered cost", f"${lowest_price[price_column]:.2f}/MWh", delta=str(lowest_price["location"]))
    with col3:
        st.metric("Largest annual cost reduction", f"{highest_reduction[reduction_column]:.1f}%", delta=str(highest_reduction["location"]))
    with col4:
        st.metric("Strongest active-hour risk reduction", f"{strongest_tail[p95_column]:.1f}%", delta=str(strongest_tail["location"]))

    observations = int(metrics.iloc[0]["observations"])
    st.caption(
        f"ERCOT DAM {SETTINGS.target_year} · {len(metrics)} locations · {observations:,} hourly observations per location · "
        f"Primary lens: {lens_label(profile_key, duration_hours)}"
    )


def _selected_row(location: str) -> pd.Series:
    return metrics.loc[metrics["location"].eq(location)].iloc[0]


def _sync_focus_selector_from_widget() -> None:
    st.session_state["selected_location"] = st.session_state["selected_location_widget"]


def _render_focus_selector(
    active_frame: pd.DataFrame,
    rank_column: str,
    label: str,
) -> None:
    location_order = active_frame["location"].tolist()
    location_type_lookup = active_frame.set_index("location")["location_type"].to_dict()
    rank_lookup = active_frame.set_index("location")[rank_column].astype(int).to_dict()
    current_location = st.session_state["selected_location"]
    if current_location not in location_order:
        current_location = location_order[0]
        st.session_state["selected_location"] = current_location

    widget_key = "selected_location_widget"
    if widget_key not in st.session_state or st.session_state[widget_key] not in location_order:
        st.session_state[widget_key] = current_location
    elif st.session_state[widget_key] != current_location:
        st.session_state[widget_key] = current_location

    st.selectbox(
        label,
        options=location_order,
        format_func=lambda location: (
            f"#{rank_lookup[location]} · {location} · {location_type_lookup[location]}"
        ),
        key=widget_key,
        on_change=_sync_focus_selector_from_widget,
    )


def _style_ranking_table(table: pd.DataFrame, selected_location: str) -> pd.io.formats.style.Styler:
    zebra_light = "#efe5d8"
    zebra_dark = "#e4d5c3"
    selected_fill = "#d9c5a7"

    def _row_fill(row: pd.Series) -> list[str]:
        if str(row.get("Location", "")) == selected_location:
            background = selected_fill
        else:
            background = zebra_light if int(row.name) % 2 == 0 else zebra_dark
        return [f"background-color: {background}; color: {PALETTE['ink']};"] * len(row)

    return (
        table.style.apply(_row_fill, axis=1)
        .set_properties(**{"border-color": "rgba(31, 38, 40, 0.08)"})
        .format(na_rep="—")
    )


def _render_ranking_table(profile_key: str) -> None:
    reviewer_table = build_reviewer_table(metrics, profile_key)
    formatted = format_reviewer_table(reviewer_table)
    styled = _style_ranking_table(formatted, st.session_state["selected_location"]).hide(axis="index")
    st.table(styled)
    st.download_button(
        label="Download reviewer CSV",
        data=reviewer_table.to_csv(index=False),
        file_name=f"ercot_{profile_key}_annual_screener.csv",
        mime="text/csv",
    )


def _render_panel_card(title: str, body_html: str) -> None:
    st.markdown(
        (
            f'<div class="panel-card">'
            f'<div class="panel-title">{title}</div>'
            f'<div class="panel-body">{body_html}</div>'
            f"</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_summary_stack(items: list[tuple[str, str]]) -> None:
    rows = "".join(
        (
            '<div class="summary-row">'
            f'<div class="summary-key">{label}</div>'
            f'<div class="summary-value">{value}</div>'
            "</div>"
        )
        for label, value in items
    )
    st.markdown(
        f'<div class="summary-stack">{rows}</div>',
        unsafe_allow_html=True,
    )


def _render_benchmark_card(title: str, selected_value: str, median_value: str) -> None:
    st.markdown(
        (
            '<div class="benchmark-card">'
            f'<div class="benchmark-title">{title}</div>'
            f'<div class="benchmark-selected">{selected_value}</div>'
            f'<div class="benchmark-median">ERCOT median: {median_value}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_interpretation_panel(active_frame: pd.DataFrame, profile_key: str, duration_hours: int) -> None:
    leader = active_frame.iloc[0]
    _render_panel_card(
        "How to read this screen",
        (
            f"Under the <strong>{lens_label(profile_key, duration_hours)}</strong> lens, higher-ranked regions combine "
            f"lower effective delivered cost, stronger battery-enabled cost reduction, and better active-hour risk "
            f"shaping for <strong>{PROFILE_LABELS[profile_key]}</strong>. Start with <strong>{leader['location']}</strong> "
            f"and the other top-ranked regions below, then use the evidence tab to decide where deeper forward-looking "
            f"modeling should go next."
        ),
    )


def _render_location_map(profile_key: str, duration_hours: int) -> None:
    map_frame = build_location_map_frame(metrics, profile_key, duration_hours)
    valid_locations = map_frame["location"].tolist()
    if st.session_state["selected_location"] not in valid_locations:
        st.session_state["selected_location"] = str(map_frame.iloc[0]["location"])

    st.caption(
        "Marker color reflects annual lens score. Marker size reflects annual cost reduction %. "
        "Click a location to persist selection."
    )
    map_event = st.plotly_chart(
        build_texas_location_map(
            map_frame=map_frame,
            selected_location=st.session_state["selected_location"],
            profile_label=PROFILE_LABELS[profile_key],
            duration_label=f"{duration_hours}h",
        ),
        use_container_width=True,
        key=f"texas_map_{profile_key}_{duration_hours}",
        on_select="rerun",
        selection_mode="points",
    )

    clicked_location = extract_selected_location(
        selection_event=map_event,
        map_frame=map_frame,
        fallback_location=st.session_state["selected_location"],
    )
    if clicked_location != st.session_state["selected_location"]:
        st.session_state["selected_location"] = clicked_location
        st.rerun()


def _render_selected_location_card(active_frame: pd.DataFrame, profile_key: str, duration_hours: int) -> None:
    rank_column = _lens_column(profile_key, duration_hours, "rank")
    selected = _selected_row(st.session_state["selected_location"])

    rank_value = int(selected[rank_column])
    effective_price = selected[_lens_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh")]
    reduction_pct = selected[_lens_column(profile_key, duration_hours, "annual_cost_reduction_pct")]
    profitable_share = selected[_lens_column(profile_key, duration_hours, "profitable_day_share")]

    st.markdown(f"#### {selected['location']}")
    st.caption(
        f"Active-lens rank #{rank_value} · {selected['location_type']} · Best-fit lens: {selected['best_fit_lens']}"
    )

    _render_summary_stack(
        [
            ("Effective price", f"${effective_price:.2f}/MWh"),
            ("Cost reduction", f"{reduction_pct:.1f}%"),
            ("Profitable days", f"{profitable_share:.1f}%"),
        ]
    )

    explainer_title, explainer_body = build_rank_context(selected, active_frame, profile_key, duration_hours)
    _render_panel_card(explainer_title, explainer_body)
    st.markdown("")
    _render_panel_card(
        "What to do next",
        build_next_step_prompt(str(selected["location"])),
    )


def _render_screen_tab(profile_key: str, duration_hours: int) -> None:
    active_frame = _active_metrics_frame(profile_key, duration_hours)
    rank_column = _lens_column(profile_key, duration_hours, "rank")
    _render_interpretation_panel(active_frame, profile_key, duration_hours)
    st.markdown("")
    _render_hero_cards(active_frame, profile_key, duration_hours)
    st.markdown("")
    _render_focus_selector(
        active_frame,
        rank_column,
        "Focus location (active-lens rank)",
    )
    st.markdown("")

    map_col, detail_col = st.columns([1.8, 1.05], gap="large")
    with map_col:
        st.markdown("### Screen Map")
        _render_location_map(profile_key, duration_hours)
    with detail_col:
        st.markdown("### Selected Region")
        _render_selected_location_card(active_frame, profile_key, duration_hours)

    st.markdown("")
    st.markdown("### Ranked Regions")
    st.caption("Selected region is highlighted. Use the focus control or map click to keep all screen surfaces aligned.")
    _render_ranking_table(profile_key)


def _economics_waterfall_figure(selected: pd.Series, profile_key: str) -> go.Figure:
    baseline = selected[_lens_column(profile_key, 4, "baseline_annual_cost_usd_per_mw_year")]
    savings_4h = selected[_lens_column(profile_key, 4, "annual_cost_reduction_usd_per_mw_year")]
    savings_8h = selected[_lens_column(profile_key, 8, "annual_cost_reduction_usd_per_mw_year")]
    incremental_8h = savings_8h - savings_4h
    fig = go.Figure(
        data=[
            go.Waterfall(
                x=[
                    "Baseline annual cost",
                    "4h savings",
                    "8h incremental savings",
                    "8h effective annual cost",
                ],
                measure=["absolute", "relative", "relative", "total"],
                y=[baseline, -savings_4h, -incremental_8h, 0.0],
                connector={"line": {"color": "rgba(105, 114, 116, 0.28)", "width": 1.1}},
                decreasing={"marker": {"color": PALETTE["sea_soft"]}},
                increasing={"marker": {"color": "#cf9b8b"}},
                totals={"marker": {"color": PALETTE["accent"]}},
                text=[f"${baseline:,.0f}", f"${savings_4h:,.0f}", f"${incremental_8h:,.0f}", ""],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{x}<br>$%{y:,.2f}/MW-yr<extra></extra>",
            )
        ]
    )
    fig.update_yaxes(title="Annual cost ($/MW-yr)", gridcolor=PALETTE["line"], zeroline=False)
    fig.update_xaxes(tickangle=0)
    return _style_plot(fig, 360)


def _monthly_profitable_frame(selected_location: str, profile_key: str, duration_hours: int) -> pd.DataFrame:
    prefix = f"{duration_hours}h"
    frame = daily_windows.loc[
        daily_windows["location"].eq(selected_location)
        & daily_windows["profile"].eq(profile_key)
        & daily_windows["active_load_mwh"].gt(0),
        :,
    ].copy()
    return (
        frame.groupby(["local_month", "local_month_label"], as_index=False)
        .agg(
            profitable_day_share=(f"{prefix}_profitable", lambda series: float(series.mean() * 100.0)),
            average_best_spread=(f"{prefix}_best_spread_usd_per_mwh", "mean"),
        )
        .sort_values("local_month", kind="mergesort")
    )


def _render_economic_takeaway(selected: pd.Series, profile_key: str) -> None:
    location = str(selected["location"])
    profile_label = PROFILE_LABELS[profile_key]
    savings_4h = selected[_lens_column(profile_key, 4, "annual_cost_reduction_usd_per_mw_year")]
    savings_8h = selected[_lens_column(profile_key, 8, "annual_cost_reduction_usd_per_mw_year")]
    incremental_8h = savings_8h - savings_4h
    effective_8h_price = selected[_lens_column(profile_key, 8, "effective_avg_price_usd_per_mwh")]
    _render_panel_card(
        "Economic takeaway",
        (
            f"For <strong>1 MW</strong> of <strong>{profile_label}</strong> load at <strong>{location}</strong>, "
            f"<strong>4h</strong> storage cuts annual delivered cost by <strong>${savings_4h:,.0f}/MW-yr</strong>. "
            f"Moving to <strong>8h</strong> adds <strong>${incremental_8h:,.0f}/MW-yr</strong> of incremental value, "
            f"bringing the effective delivered price to <strong>${effective_8h_price:.2f}/MWh</strong>."
        ),
    )


def _render_selected_vs_median_benchmarks(
    active_frame: pd.DataFrame,
    selected: pd.Series,
    profile_key: str,
    duration_hours: int,
) -> None:
    effective_col = _lens_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh")
    reduction_col = _lens_column(profile_key, duration_hours, "annual_cost_reduction_pct")
    p95_col = _lens_column(profile_key, duration_hours, "p95_active_hour_reduction_pct")

    _render_benchmark_card(
        "Effective delivered cost",
        f"${selected[effective_col]:.2f}/MWh",
        f"${active_frame[effective_col].median():.2f}/MWh",
    )
    _render_benchmark_card(
        "Annual cost reduction",
        f"{selected[reduction_col]:.1f}%",
        f"{active_frame[reduction_col].median():.1f}%",
    )
    _render_benchmark_card(
        "Active-hour risk reduction",
        f"{selected[p95_col]:.1f}%",
        f"{active_frame[p95_col].median():.1f}%",
    )


def _monthly_driver_figure(selected_location: str, profile_key: str, duration_hours: int) -> tuple[str, go.Figure]:
    if profile_key == "inference_weekday_9_17":
        frame = hourly_shape.loc[
            hourly_shape["location"].eq(selected_location)
            & hourly_shape["profile"].eq(profile_key)
            & hourly_shape["duration_hours"].eq(duration_hours),
            :,
        ].copy()
        active = (
            frame.loc[frame["active_hour_flag"]]
            .groupby(["local_month", "local_month_label"], as_index=False)
            .agg(value=("market_price_avg_usd_per_mwh", "mean"))
            .assign(series="Weekday active hours")
        )
        overnight = (
            frame.loc[frame["local_hour"].between(0, 8)]
            .groupby(["local_month", "local_month_label"], as_index=False)
            .agg(value=("market_price_avg_usd_per_mwh", "mean"))
            .assign(series="Overnight charge window")
        )
        compare = pd.concat([active, overnight], ignore_index=True)
        fig = go.Figure()
        color_map = {
            "Weekday active hours": PALETTE["sea"],
            "Overnight charge window": PALETTE["sand"],
        }
        for series_name, series_frame in compare.groupby("series", sort=False):
            series_frame = series_frame.sort_values("local_month", kind="mergesort")
            fig.add_trace(
                go.Scatter(
                    x=series_frame["local_month_label"],
                    y=series_frame["value"],
                    mode="lines+markers",
                    name=series_name,
                    marker={"size": 8},
                    line={"width": 2.6, "color": color_map[series_name]},
                    hovertemplate=f"{series_name}<br>%{{x}}: $%{{y:.2f}}/MWh<extra></extra>",
                )
            )
        fig.update_yaxes(title="Average price ($/MWh)", gridcolor=PALETTE["line"], zeroline=False)
        fig.update_xaxes(categoryorder="array", categoryarray=list(MONTH_ORDER))
        return ("Monthly daytime vs overnight price driver", _style_plot(fig, 320))

    monthly = _monthly_profitable_frame(selected_location, profile_key, duration_hours)
    fig = go.Figure(
        data=[
            go.Bar(
                x=monthly["local_month_label"],
                y=monthly["average_best_spread"],
                marker_color=PALETTE["sand"] if duration_hours == 4 else PALETTE["accent"],
                marker_line_width=0,
                hovertemplate="%{x}<br>$%{y:.2f}/MWh average best spread<extra></extra>",
                showlegend=False,
            )
        ]
    )
    fig.update_yaxes(title="Average best spread ($/MWh)", gridcolor=PALETTE["line"], zeroline=False)
    fig.update_xaxes(categoryorder="array", categoryarray=list(MONTH_ORDER))
    return (f"Monthly {duration_hours}h spread driver", _style_plot(fig, 320))


def _render_incremental_value_footer(selected: pd.Series, profile_key: str) -> None:
    incremental_savings = (
        selected[_lens_column(profile_key, 8, "annual_cost_reduction_usd_per_mw_year")]
        - selected[_lens_column(profile_key, 4, "annual_cost_reduction_usd_per_mw_year")]
    )
    incremental_pct = (
        selected[_lens_column(profile_key, 8, "annual_cost_reduction_pct")]
        - selected[_lens_column(profile_key, 4, "annual_cost_reduction_pct")]
    )
    incremental_price = (
        selected[_lens_column(profile_key, 4, "effective_avg_price_usd_per_mwh")]
        - selected[_lens_column(profile_key, 8, "effective_avg_price_usd_per_mwh")]
    )
    _render_panel_card(
        "8h incremental value vs 4h",
        (
            f"Relative to <strong>4h</strong>, the <strong>8h</strong> case adds "
            f"<strong>${incremental_savings:,.0f}/MW-yr</strong> of annual value, improves cost reduction by "
            f"<strong>{incremental_pct:.1f} percentage points</strong>, and lowers effective delivered price by "
            f"<strong>${incremental_price:.2f}/MWh</strong>."
        ),
    )


def _render_evidence_tab(profile_key: str, duration_hours: int) -> None:
    active_frame = _active_metrics_frame(profile_key, duration_hours)
    selected = _selected_row(st.session_state["selected_location"])
    location = str(selected["location"])
    st.markdown(f"### Evidence For {location}")
    st.caption(
        f"These views support the {lens_label(profile_key, duration_hours)} screen and help explain "
        "why this region looks flexibility-sensitive."
    )
    _render_economic_takeaway(selected, profile_key)
    st.markdown("")

    heatmap_frame = hourly_shape.loc[
        hourly_shape["location"].eq(location)
        & hourly_shape["profile"].eq(profile_key)
        & hourly_shape["duration_hours"].eq(duration_hours),
        :,
    ]
    st.markdown('<div class="chart-kicker">Raw price shape</div>', unsafe_allow_html=True)
    st.plotly_chart(
        _heatmap_figure(
            heatmap_frame,
            "market_price_avg_usd_per_mwh",
            "Market price<br>($/MWh)",
        ),
        use_container_width=True,
    )

    econ_left, econ_right = st.columns([1.35, 1.0], gap="large")
    with econ_left:
        st.markdown('<div class="chart-kicker">Savings bridge</div>', unsafe_allow_html=True)
        st.plotly_chart(
            _economics_waterfall_figure(selected, profile_key),
            use_container_width=True,
        )
    with econ_right:
        st.markdown('<div class="chart-kicker">Selected vs ERCOT median</div>', unsafe_allow_html=True)
        _render_selected_vs_median_benchmarks(active_frame, selected, profile_key, duration_hours)

    driver_title, driver_figure = _monthly_driver_figure(location, profile_key, duration_hours)
    st.markdown(f'<div class="chart-kicker">{driver_title}</div>', unsafe_allow_html=True)
    st.plotly_chart(
        driver_figure,
        use_container_width=True,
    )
    _render_incremental_value_footer(selected, profile_key)

    with st.expander("Additional diagnostics"):
        diagnostics_left, diagnostics_right = st.columns([1.25, 1.0], gap="large")
        with diagnostics_left:
            st.markdown('<div class="chart-kicker">Daily causal window log</div>', unsafe_allow_html=True)
            st.dataframe(
                _daily_window_log(location, profile_key, duration_hours),
                use_container_width=True,
                hide_index=True,
                height=360,
            )
        with diagnostics_right:
            st.markdown('<div class="chart-kicker">Raw metric values</div>', unsafe_allow_html=True)
            st.dataframe(
                build_selected_metric_table(selected, profile_key),
                use_container_width=True,
                hide_index=True,
                height=360,
            )


def _render_next_step_tab(profile_key: str, duration_hours: int) -> None:
    selected = _selected_row(st.session_state["selected_location"])
    st.markdown(f"### Next Step For {selected['location']}")
    st.caption(
        f"The current focus remains {selected['location']} under the {lens_label(profile_key, duration_hours)} lens."
    )

    col_left, col_mid, col_right = st.columns(3, gap="large")
    with col_left:
        _render_panel_card(
            "What this is not",
            (
                '<ul class="panel-list">'
                "<li>not a nodal siting engine</li>"
                "<li>not a forecast</li>"
                "<li>not an interconnection screen</li>"
                "<li>not a full dispatch optimization model</li>"
                "</ul>"
            ),
        )
    with col_mid:
        _render_panel_card(
            "What deeper modeling would add",
            (
                '<ul class="panel-list">'
                "<li>nodal and congestion detail</li>"
                "<li>forward-looking scenario analysis</li>"
                "<li>site-specific load shape assumptions</li>"
                "<li>interconnection, land, fiber, and infrastructure constraints</li>"
                "<li>more realistic dispatch and battery operating assumptions</li>"
                "</ul>"
            ),
        )
    with col_right:
        _render_panel_card(
            "Current limitations",
            (
                '<ul class="panel-list">'
                "<li>historical annual ERCOT hubs and load zones only</li>"
                "<li>no nodal or transmission overlays in the current screen</li>"
                "<li>stylized same-day battery convention, not production dispatch</li>"
                "<li>results identify where deeper analysis may be worth doing next</li>"
                "</ul>"
            ),
        )


def _style_plot(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": 40, "r": 16, "t": 28, "b": 48},
        font={"family": BODY_FONT, "size": 12, "color": PALETTE["ink"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _heatmap_figure(frame: pd.DataFrame, value_column: str, colorbar_title: str) -> go.Figure:
    pivot = (
        frame.pivot(index="local_hour", columns="local_month_label", values=value_column)
        .reindex(index=list(range(24)), columns=list(MONTH_ORDER))
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=HEATMAP_SCALE if "market" in value_column else EFFECTIVE_PRICE_SCALE,
            hovertemplate="<b>%{x}</b><br>Hour %{y}:00<br>$%{z:.2f}/MWh<extra></extra>",
            colorbar={
                "title": {"text": colorbar_title, "font": {"size": 11}},
                "thickness": 12,
                "len": 0.62,
                "tickfont": {"size": 10},
                "outlinewidth": 0,
            },
        )
    )
    fig.update_layout(margin={"l": 40, "r": 22, "t": 18, "b": 24})
    fig.update_yaxes(title="Local hour", autorange="reversed")
    fig.update_xaxes(side="top")
    return _style_plot(fig, 420)


def _daily_window_log(selected_location: str, profile_key: str, duration_hours: int) -> pd.DataFrame:
    prefix = f"{duration_hours}h"
    frame = daily_windows.loc[
        daily_windows["location"].eq(selected_location)
        & daily_windows["profile"].eq(profile_key)
        & daily_windows["active_load_mwh"].gt(0),
        :,
    ].copy()
    view = (
        frame.loc[
        :,
        [
            "local_date",
            "local_month_label",
            f"{prefix}_best_spread_usd_per_mwh",
            f"{prefix}_charge_start_hour",
            f"{prefix}_discharge_start_hour",
            f"{prefix}_profitable",
        ],
    ]
        .sort_values("local_date", ascending=True, kind="mergesort")
        .rename(
        columns={
            "local_date": "Date",
            "local_month_label": "Month",
            f"{prefix}_best_spread_usd_per_mwh": "Best Spread ($/MWh)",
            f"{prefix}_charge_start_hour": "Charge Start Hour",
            f"{prefix}_discharge_start_hour": "Discharge Start Hour",
            f"{prefix}_profitable": "Profitable",
        }
    )
    )
    out = view.copy()
    out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    out["Best Spread ($/MWh)"] = out["Best Spread ($/MWh)"].map(lambda value: f"${value:,.2f}")
    out["Charge Start Hour"] = out["Charge Start Hour"].map(
        lambda value: f"{int(value):02d}:00" if pd.notna(value) else "—"
    )
    out["Discharge Start Hour"] = out["Discharge Start Hour"].map(
        lambda value: f"{int(value):02d}:00" if pd.notna(value) else "—"
    )
    out["Profitable"] = out["Profitable"].map(lambda value: "Yes" if bool(value) else "No")
    return out.reset_index(drop=True)


def main() -> None:
    _init_session_state()
    selected_profile, selected_duration = _render_controls()
    tab_screen, tab_evidence, tab_next = st.tabs(["Screen", "Evidence", "Next Step"])
    with tab_screen:
        _render_screen_tab(selected_profile, selected_duration)
    with tab_evidence:
        _render_evidence_tab(selected_profile, selected_duration)
    with tab_next:
        _render_next_step_tab(selected_profile, selected_duration)


if __name__ == "__main__":
    main()
