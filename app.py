"""Annual ERCOT large-load flexibility screener."""

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


st.set_page_config(
    page_title="ERCOT Large-Load Flexibility Screener",
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
    st.markdown('<div class="hero-kicker">Annual Screener</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="hero-title">ERCOT Large-Load Flexibility Screener</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-subtitle">Screen ERCOT hubs and load zones for annual large-load deployment. '
        'Switch between 24/7 training and weekday daytime inference, then compare how 4-hour and 8-hour '
        'battery flexibility changes delivered cost, profitable day frequency, and active-hour risk.</p>',
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
            '<div class="control-note">The primary lens controls ranking, map coloring, and headline KPIs. '
            'The drilldown still shows both 4h and 8h for the selected load profile.</div>',
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
        st.metric("Lens leader", str(leader["location"]), delta=f"Score {leader[score_column]:.1f}")
    with col2:
        st.metric("Best effective average price", f"${lowest_price[price_column]:.2f}/MWh", delta=str(lowest_price["location"]))
    with col3:
        st.metric("Largest annual cost reduction", f"{highest_reduction[reduction_column]:.1f}%", delta=str(highest_reduction["location"]))
    with col4:
        st.metric("Strongest active-hour tail-risk reduction", f"{strongest_tail[p95_column]:.1f}%", delta=str(strongest_tail["location"]))

    observations = int(metrics.iloc[0]["observations"])
    st.caption(
        f"ERCOT DAM {SETTINGS.target_year} · {len(metrics)} locations · {observations:,} hourly observations per location · "
        f"Primary lens: {lens_label(profile_key, duration_hours)}"
    )


def _selected_row(location: str) -> pd.Series:
    return metrics.loc[metrics["location"].eq(location)].iloc[0]


def _render_focus_selector(
    active_frame: pd.DataFrame,
    rank_column: str,
    label: str,
    widget_key: str,
) -> None:
    location_order = active_frame["location"].tolist()
    location_type_lookup = active_frame.set_index("location")["location_type"].to_dict()
    rank_lookup = active_frame.set_index("location")[rank_column].astype(int).to_dict()

    selected_location = st.selectbox(
        label,
        options=location_order,
        index=location_order.index(st.session_state["selected_location"]),
        format_func=lambda location: (
            f"#{rank_lookup[location]} · {location} · {location_type_lookup[location]}"
        ),
        key=widget_key,
    )
    if selected_location != st.session_state["selected_location"]:
        st.session_state["selected_location"] = selected_location
        st.rerun()


def _render_map_section(profile_key: str, duration_hours: int) -> None:
    st.markdown("### Geographic Screen")
    map_frame = build_location_map_frame(metrics, profile_key, duration_hours)
    rank_column = _lens_column(profile_key, duration_hours, "rank")
    valid_locations = map_frame["location"].tolist()
    if st.session_state["selected_location"] not in valid_locations:
        st.session_state["selected_location"] = str(map_frame.iloc[0]["location"])

    map_col, detail_col = st.columns([2.8, 1.7], gap="large")

    with map_col:
        st.caption("Marker color reflects annual lens score. Marker size reflects annual cost reduction %. Click a location to persist selection.")
        map_event = st.plotly_chart(
            build_texas_location_map(
                map_frame=map_frame,
                selected_location=st.session_state["selected_location"],
                profile_label=PROFILE_LABELS[profile_key],
                duration_label=f"{duration_hours}h",
            ),
            use_container_width=True,
            key="texas_map",
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

    selected = _selected_row(st.session_state["selected_location"])
    with detail_col:
        _render_focus_selector(
            _active_metrics_frame(profile_key, duration_hours),
            rank_column,
            "Focus location (active-lens rank)",
            f"focus_location_map_{rank_column}",
        )
        st.markdown(f"#### {selected['location']}")
        st.markdown(build_location_narrative(selected, profile_key, duration_hours))
        card_left, card_right = st.columns(2)
        with card_left:
            st.metric(
                "4h effective price",
                f"${selected[_lens_column(profile_key, 4, 'effective_avg_price_usd_per_mwh')]:.2f}/MWh",
                delta=f"{selected[_lens_column(profile_key, 4, 'annual_cost_reduction_pct')]:.1f}% reduction",
            )
        with card_right:
            st.metric(
                "8h effective price",
                f"${selected[_lens_column(profile_key, 8, 'effective_avg_price_usd_per_mwh')]:.2f}/MWh",
                delta=f"{selected[_lens_column(profile_key, 8, 'annual_cost_reduction_pct')]:.1f}% reduction",
            )
        st.metric("Best-fit lens", str(selected["best_fit_lens"]), delta=f"Rank {int(selected['best_fit_rank'])}")


def _style_ranking_table(table: pd.DataFrame) -> pd.io.formats.style.Styler:
    zebra_light = "#efe5d8"
    zebra_dark = "#e4d5c3"

    def _row_fill(row: pd.Series) -> list[str]:
        background = zebra_light if int(row.name) % 2 == 0 else zebra_dark
        return [f"background-color: {background}; color: {PALETTE['ink']};"] * len(row)

    return (
        table.style.apply(_row_fill, axis=1)
        .set_properties(**{"border-color": "rgba(31, 38, 40, 0.08)"})
        .format(na_rep="—")
    )


def _render_ranking_table(profile_key: str) -> None:
    st.markdown("### Ranking Table")
    reviewer_table = build_reviewer_table(metrics, profile_key)
    formatted = format_reviewer_table(reviewer_table)
    styled = _style_ranking_table(formatted)
    table_height = min(42 + 35 * len(formatted), 620)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=table_height)
    st.download_button(
        label="Download reviewer CSV",
        data=reviewer_table.to_csv(index=False),
        file_name=f"ercot_{profile_key}_annual_screener.csv",
        mime="text/csv",
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


def _render_annual_summary(selected: pd.Series, profile_key: str, duration_hours: int) -> None:
    baseline = selected[_lens_column(profile_key, 4, "baseline_annual_cost_usd_per_mw_year")]
    effective_4h = selected[_lens_column(profile_key, 4, "effective_annual_cost_usd_per_mw_year")]
    effective_8h = selected[_lens_column(profile_key, 8, "effective_annual_cost_usd_per_mw_year")]

    cards = st.columns(5, gap="medium")
    cards[0].metric("Baseline annual cost", f"${baseline:,.0f}/MW-yr")
    cards[1].metric(
        "4h cost reduction",
        f"{selected[_lens_column(profile_key, 4, 'annual_cost_reduction_pct')]:.1f}%",
        delta=f"${selected[_lens_column(profile_key, 4, 'annual_cost_reduction_usd_per_mw_year')]:,.0f}",
    )
    cards[2].metric(
        "8h cost reduction",
        f"{selected[_lens_column(profile_key, 8, 'annual_cost_reduction_pct')]:.1f}%",
        delta=f"${selected[_lens_column(profile_key, 8, 'annual_cost_reduction_usd_per_mw_year')]:,.0f}",
    )
    cards[3].metric(
        "4h profitable-day share",
        f"{selected[_lens_column(profile_key, 4, 'profitable_day_share')]:.1f}%",
    )
    cards[4].metric(
        "8h profitable-day share",
        f"{selected[_lens_column(profile_key, 8, 'profitable_day_share')]:.1f}%",
    )

    left, right = st.columns([1.3, 1.0], gap="large")
    with left:
        annual_cost_fig = go.Figure(
            data=[
                go.Bar(
                    x=["Baseline", "4h Battery", "8h Battery"],
                    y=[baseline, effective_4h, effective_8h],
                    marker_color=[PALETTE["sea_soft"], PALETTE["sand"], PALETTE["accent"]],
                    marker_line_width=0,
                    hovertemplate="%{x}<br>$%{y:,.0f}/MW-yr<extra></extra>",
                )
            ]
        )
        annual_cost_fig.update_yaxes(title="Annual cost ($/MW-yr)", gridcolor=PALETTE["line"], zeroline=False)
        _style_plot(annual_cost_fig, 360)
        st.plotly_chart(annual_cost_fig, use_container_width=True)

    with right:
        pre_post = go.Figure()
        for duration, color in ((4, PALETTE["sand"]), (8, PALETTE["accent"])):
            pre_column = _lens_column(profile_key, duration, "p95_active_hour_price_usd_per_mwh")
            post_column = _lens_column(profile_key, duration, "p95_active_hour_effective_price_usd_per_mwh")
            pre_post.add_trace(
                go.Bar(
                    name=f"{duration}h pre-shape",
                    x=[f"{duration}h"],
                    y=[selected[pre_column]],
                    marker_color=PALETTE["sea_soft"],
                    offsetgroup=f"{duration}_pre",
                    hovertemplate=f"{duration}h pre-shape<br>$%{{y:.2f}}/MWh<extra></extra>",
                )
            )
            pre_post.add_trace(
                go.Bar(
                    name=f"{duration}h post-shape",
                    x=[f"{duration}h"],
                    y=[selected[post_column]],
                    marker_color=color,
                    offsetgroup=f"{duration}_post",
                    hovertemplate=f"{duration}h post-shape<br>$%{{y:.2f}}/MWh<extra></extra>",
                )
            )
        pre_post.update_layout(barmode="group")
        pre_post.update_yaxes(title="P95 active-hour price ($/MWh)", gridcolor=PALETTE["line"], zeroline=False)
        _style_plot(pre_post, 360)
        st.plotly_chart(pre_post, use_container_width=True)


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


def _monthly_comparison_figure(
    selected_location: str,
    profile_key: str,
    duration_hours: int,
) -> go.Figure:
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
            .assign(series="Weekday overnight")
        )
        compare = pd.concat([active, overnight], ignore_index=True)
    else:
        frame = daily_windows.loc[
            daily_windows["location"].eq(selected_location)
            & daily_windows["profile"].eq(profile_key)
            & daily_windows["active_load_mwh"].gt(0),
            :,
        ].copy()
        active = (
            frame.groupby(["local_month", "local_month_label"], as_index=False)
            .agg(value=("baseline_daily_cost_usd_per_mw_day", lambda series: float(series.mean() / 24.0)))
            .assign(series="Average active-hour price")
        )
        charge_avg_column = f"{duration_hours}h_charge_avg_price_usd_per_mwh"
        charge = (
            frame.groupby(["local_month", "local_month_label"], as_index=False)
            .agg(value=(charge_avg_column, "mean"))
            .assign(series="Selected charge-window average")
        )
        compare = pd.concat([active, charge], ignore_index=True)

    fig = go.Figure()
    color_map = {
        "Weekday active hours": PALETTE["sea"],
        "Weekday overnight": PALETTE["sand"],
        "Average active-hour price": PALETTE["sea"],
        "Selected charge-window average": PALETTE["accent"],
    }
    for series_name, series_frame in compare.groupby("series", sort=False):
        series_frame = series_frame.sort_values("local_month")
        fig.add_trace(
            go.Scatter(
                x=series_frame["local_month_label"],
                y=series_frame["value"],
                mode="lines+markers",
                name=series_name,
                marker={"size": 8},
                line={"width": 2.4, "color": color_map[series_name]},
                hovertemplate=f"{series_name}<br>%{{x}}: $%{{y:.2f}}/MWh<extra></extra>",
            )
        )
    fig.update_yaxes(title="Average price ($/MWh)", gridcolor=PALETTE["line"], zeroline=False)
    fig.update_xaxes(categoryorder="array", categoryarray=list(MONTH_ORDER))
    return _style_plot(fig, 320)


def _monthly_profitable_share_figure(monthly: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Bar(
                x=monthly["local_month_label"],
                y=monthly["profitable_day_share"],
                marker={
                    "color": monthly["profitable_day_share"],
                    "colorscale": [
                        [0.0, "#d8ddd6"],
                        [0.5, PALETTE["sea_soft"]],
                        [1.0, PALETTE["sea"]],
                    ],
                    "cmin": 0.0,
                    "cmax": 100.0,
                    "line": {"width": 0},
                },
                hovertemplate="%{x}<br>%{y:.1f}% of active days profitable<extra></extra>",
                showlegend=False,
            )
        ]
    )
    fig.update_yaxes(
        title="Profitable day share (%)",
        range=[0, 100],
        gridcolor=PALETTE["line"],
        zeroline=False,
    )
    fig.update_xaxes(categoryorder="array", categoryarray=list(MONTH_ORDER))
    return _style_plot(fig, 250)


def _monthly_best_spread_figure(monthly: pd.DataFrame, duration_hours: int) -> go.Figure:
    accent = PALETTE["sand"] if duration_hours == 4 else PALETTE["accent"]
    fig = go.Figure(
        data=[
            go.Scatter(
                x=monthly["local_month_label"],
                y=monthly["average_best_spread"],
                mode="lines+markers",
                line={"width": 3, "color": accent},
                marker={
                    "size": 9,
                    "color": accent,
                    "line": {"width": 2, "color": "rgba(255,252,247,0.9)"},
                },
                fill="tozeroy",
                fillcolor="rgba(184, 157, 125, 0.12)" if duration_hours == 4 else "rgba(127, 79, 63, 0.10)",
                hovertemplate="%{x}<br>$%{y:.2f}/MWh average best spread<extra></extra>",
                showlegend=False,
            )
        ]
    )
    fig.update_yaxes(
        title="Average best spread ($/MWh)",
        gridcolor=PALETTE["line"],
        zeroline=False,
    )
    fig.update_xaxes(categoryorder="array", categoryarray=list(MONTH_ORDER))
    return _style_plot(fig, 250)


def _render_temporal_shape(selected_location: str, profile_key: str, duration_hours: int) -> None:
    frame = hourly_shape.loc[
        hourly_shape["location"].eq(selected_location)
        & hourly_shape["profile"].eq(profile_key)
        & hourly_shape["duration_hours"].eq(duration_hours),
        :,
    ]
    heat_left, heat_right = st.columns(2, gap="large")
    with heat_left:
        st.markdown('<div class="chart-kicker">Market price shape</div>', unsafe_allow_html=True)
        st.plotly_chart(
            _heatmap_figure(
                frame,
                "market_price_avg_usd_per_mwh",
                "Market price<br>($/MWh)",
            ),
            use_container_width=True,
        )
    with heat_right:
        st.markdown(
            f'<div class="chart-kicker">Effective shaped price ({duration_hours}h)</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            _heatmap_figure(
                frame,
                "effective_active_price_avg_usd_per_mwh",
                "Effective price<br>($/MWh)",
            ),
            use_container_width=True,
        )
    st.plotly_chart(
        _monthly_comparison_figure(selected_location, profile_key, duration_hours),
        use_container_width=True,
    )


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


def _render_flexibility_tab(selected: pd.Series, profile_key: str, duration_hours: int) -> None:
    prefix = f"{duration_hours}h"
    frame = daily_windows.loc[
        daily_windows["location"].eq(selected["location"])
        & daily_windows["profile"].eq(profile_key)
        & daily_windows["active_load_mwh"].gt(0),
        :,
    ].copy()

    comparison_col, raw_col = st.columns([1.4, 1.0], gap="large")
    with comparison_col:
        monthly = (
            frame.groupby(["local_month", "local_month_label"], as_index=False)
            .agg(
                profitable_day_share=(f"{prefix}_profitable", lambda series: float(series.mean() * 100.0)),
                average_best_spread=(f"{prefix}_best_spread_usd_per_mwh", "mean"),
            )
            .sort_values("local_month")
        )

        monthly_cards = st.columns(3, gap="medium")
        best_share_row = monthly.loc[monthly["profitable_day_share"].idxmax()]
        best_spread_row = monthly.loc[monthly["average_best_spread"].idxmax()]
        weakest_spread_row = monthly.loc[monthly["average_best_spread"].idxmin()]
        monthly_cards[0].metric("Best profitable month", str(best_share_row["local_month_label"]), f"{best_share_row['profitable_day_share']:.1f}%")
        monthly_cards[1].metric("Best spread month", str(best_spread_row["local_month_label"]), f"${best_spread_row['average_best_spread']:.2f}/MWh")
        monthly_cards[2].metric("Weakest spread month", str(weakest_spread_row["local_month_label"]), f"${weakest_spread_row['average_best_spread']:.2f}/MWh")

        monthly_left, monthly_right = st.columns(2, gap="large")
        with monthly_left:
            st.markdown('<div class="chart-kicker">Monthly profitable-day share</div>', unsafe_allow_html=True)
            st.plotly_chart(
                _monthly_profitable_share_figure(monthly),
                use_container_width=True,
            )
        with monthly_right:
            st.markdown('<div class="chart-kicker">Monthly average best spread</div>', unsafe_allow_html=True)
            st.plotly_chart(
                _monthly_best_spread_figure(monthly, duration_hours),
                use_container_width=True,
            )

        spread_distribution = go.Figure(
            data=[
                go.Histogram(
                    x=frame[f"{prefix}_best_spread_usd_per_mwh"],
                    nbinsx=42,
                    marker_color=PALETTE["sand"] if duration_hours == 4 else PALETTE["accent"],
                    opacity=0.86,
                    hovertemplate="$%{x:.2f}/MWh<br>%{y} days<extra></extra>",
                )
            ]
        )
        spread_distribution.update_xaxes(title="Best daily causal spread ($/MWh)", gridcolor=PALETTE["line"], zerolinecolor=PALETTE["line_strong"])
        spread_distribution.update_yaxes(title="Days", gridcolor=PALETTE["line"], zeroline=False)
        _style_plot(spread_distribution, 280)
        st.plotly_chart(spread_distribution, use_container_width=True)

        st.markdown('<div class="chart-kicker">Daily window log</div>', unsafe_allow_html=True)
        st.dataframe(
            _daily_window_log(str(selected["location"]), profile_key, duration_hours),
            use_container_width=True,
            hide_index=True,
            height=360,
        )

    with raw_col:
        if duration_hours == 8:
            delta = (
                selected[_lens_column(profile_key, 8, "annual_cost_reduction_pct")]
                - selected[_lens_column(profile_key, 4, "annual_cost_reduction_pct")]
            )
            st.metric("8h minus 4h annual cost reduction", f"{delta:.1f} percentage points")
        st.dataframe(
            build_selected_metric_table(selected, profile_key, focus_duration=duration_hours),
            use_container_width=True,
            hide_index=True,
            height=620,
        )


def _render_analyst_console(profile_key: str, duration_hours: int) -> None:
    active_frame = _active_metrics_frame(profile_key, duration_hours)
    rank_column = _lens_column(profile_key, duration_hours, "rank")
    selected = _selected_row(st.session_state["selected_location"])
    st.markdown("### Analyst Console")
    _render_focus_selector(
        active_frame,
        rank_column,
        "Analyst focus (active-lens rank)",
        f"focus_location_console_{rank_column}",
    )
    tab_summary, tab_shape, tab_4h, tab_8h = st.tabs(
        ["Annual Summary", "Temporal Shape", "4h Flexibility", "8h Flexibility"]
    )
    with tab_summary:
        _render_annual_summary(selected, profile_key, duration_hours)
    with tab_shape:
        _render_temporal_shape(str(selected["location"]), profile_key, duration_hours)
    with tab_4h:
        _render_flexibility_tab(selected, profile_key, 4)
    with tab_8h:
        _render_flexibility_tab(selected, profile_key, 8)


def _render_methodology(profile_key: str) -> None:
    with st.expander("Methodology and scope"):
        st.markdown(
            f"""
**Question:** Which ERCOT hubs and load zones look strongest for annual large-load deployment when the load can be paired with 4-hour or 8-hour battery flexibility?

**Active profile in view:** {PROFILE_LABELS[profile_key]}. Rankings and map colors use the selected profile and primary duration lens. The table always shows 4h and 8h side by side for that profile.

**Battery convention:** 1 MW battery power per 1 MW load, same-day causal charge then discharge only, 85% round-trip efficiency, no ancillary services, no degradation, and no cross-day state of charge.

**Annual score inputs:** inverse effective average price, annual cost reduction %, profitable-day share, and active-hour p95 price reduction. Daily best-spread diagnostics support the drilldown but do not drive the primary score.

**Scope boundary:** annual hub/load-zone screening only. This is not nodal siting, forecasting, transmission analysis, or production dispatch optimization.
"""
        )


def main() -> None:
    _init_session_state()
    selected_profile, selected_duration = _render_controls()
    active_frame = _active_metrics_frame(selected_profile, selected_duration)
    _render_hero_cards(active_frame, selected_profile, selected_duration)
    st.markdown("---")
    _render_analyst_console(selected_profile, selected_duration)
    st.markdown("---")
    _render_map_section(selected_profile, selected_duration)
    st.markdown("---")
    _render_ranking_table(selected_profile)
    st.markdown("---")
    _render_methodology(selected_profile)


if __name__ == "__main__":
    main()
