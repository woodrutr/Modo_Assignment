"""Annual ERCOT large-load flexibility screener."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    BODY_FONT,
    DISPLAY_FONT,
    DURATION_OPTIONS,
    EFFECTIVE_PRICE_SCALE,
    HEATMAP_SCALE,
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
        padding-top: 1.6rem;
        padding-bottom: 2.5rem;
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
        margin-top: -0.25rem;
        margin-bottom: 1.1rem;
    }}

    .section-card {{
        background: rgba(255, 252, 247, 0.72);
        border: 1px solid {PALETTE["line"]};
        border-radius: 20px;
        padding: 1rem 1.1rem 1.05rem 1.1rem;
        box-shadow: 0 12px 28px rgba(31, 38, 40, 0.05);
    }}

    .section-caption {{
        color: {PALETTE["muted"]};
        font-size: 0.8rem;
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
def load_metrics() -> pd.DataFrame:
    return pd.read_parquet(SETTINGS.metrics_path(SETTINGS.target_year))


@st.cache_data
def load_daily_profile_windows() -> pd.DataFrame:
    return pd.read_parquet(SETTINGS.daily_profile_windows_path(SETTINGS.target_year))


@st.cache_data
def load_hourly_profile_shape() -> pd.DataFrame:
    return pd.read_parquet(SETTINGS.hourly_profile_shape_path(SETTINGS.target_year))


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
    controls_left, controls_right = st.columns([2.2, 1.2], gap="large")
    with controls_left:
        st.markdown("### Annual Screener")
        st.markdown(
            '<p class="hero-subtitle">Screen ERCOT hubs and load zones for annual large-load deployment. '
            'Switch between 24/7 training and weekday daytime inference, then compare how 4-hour and 8-hour '
            'battery flexibility changes delivered cost, profitable day frequency, and active-hour risk.</p>',
            unsafe_allow_html=True,
        )
    with controls_right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        selected_profile = st.radio(
            "Load profile",
            options=list(PROFILE_ORDER),
            format_func=lambda key: PROFILE_LABELS[key],
            horizontal=True,
            key="selected_profile",
        )
        selected_duration = st.radio(
            "Primary battery duration",
            options=list(DURATION_OPTIONS),
            format_func=lambda duration: f"{duration}h",
            horizontal=True,
            key="selected_duration",
        )
        st.markdown(
            '<p class="section-caption">The primary lens controls ranking, map coloring, and headline KPIs. '
            'The drilldown still shows both 4h and 8h for the selected load profile.</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
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


def _render_map_section(profile_key: str, duration_hours: int) -> None:
    st.markdown("### Geographic Screen")
    map_frame = build_location_map_frame(metrics, profile_key, duration_hours)
    valid_locations = map_frame["location"].tolist()
    if st.session_state["selected_location"] not in valid_locations:
        st.session_state["selected_location"] = str(map_frame.iloc[0]["location"])

    map_col, detail_col = st.columns([2.8, 1.7], gap="large")

    with map_col:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
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
        st.markdown("</div>", unsafe_allow_html=True)

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
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
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
        st.markdown("</div>", unsafe_allow_html=True)


def _render_ranking_table(profile_key: str) -> None:
    st.markdown("### Ranking Table")
    reviewer_table = build_reviewer_table(metrics, profile_key)
    formatted = format_reviewer_table(reviewer_table)
    st.dataframe(formatted, use_container_width=True, hide_index=True, height=min(44 * len(formatted) + 40, 760))
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


def _heatmap_figure(frame: pd.DataFrame, value_column: str, title: str, colorbar_title: str) -> go.Figure:
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
    fig.update_layout(title={"text": title, "font": {"size": 14}}, margin={"l": 40, "r": 22, "t": 50, "b": 24})
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


def _render_temporal_shape(selected_location: str, profile_key: str, duration_hours: int) -> None:
    frame = hourly_shape.loc[
        hourly_shape["location"].eq(selected_location)
        & hourly_shape["profile"].eq(profile_key)
        & hourly_shape["duration_hours"].eq(duration_hours),
        :,
    ]
    heat_left, heat_right = st.columns(2, gap="large")
    with heat_left:
        st.plotly_chart(
            _heatmap_figure(
                frame,
                "market_price_avg_usd_per_mwh",
                "Market price shape",
                "Market price<br>($/MWh)",
            ),
            use_container_width=True,
        )
    with heat_right:
        st.plotly_chart(
            _heatmap_figure(
                frame,
                "effective_active_price_avg_usd_per_mwh",
                f"Effective shaped price ({duration_hours}h)",
                "Effective price<br>($/MWh)",
            ),
            use_container_width=True,
        )
    st.plotly_chart(
        _monthly_comparison_figure(selected_location, profile_key, duration_hours),
        use_container_width=True,
    )


def _representative_days(selected_location: str, profile_key: str, duration_hours: int) -> pd.DataFrame:
    prefix = f"{duration_hours}h"
    frame = daily_windows.loc[
        daily_windows["location"].eq(selected_location)
        & daily_windows["profile"].eq(profile_key)
        & daily_windows["active_load_mwh"].gt(0),
        :,
    ].copy()
    sort_column = f"{prefix}_best_spread_usd_per_mwh"
    view = frame.loc[
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
    worst = view.nsmallest(3, sort_column).assign(bucket="Worst")
    best = view.nlargest(3, sort_column).assign(bucket="Best")
    out = pd.concat([best, worst], ignore_index=True)
    out = out.rename(
        columns={
            "local_date": "Date",
            "local_month_label": "Month",
            f"{prefix}_best_spread_usd_per_mwh": "Best Spread ($/MWh)",
            f"{prefix}_charge_start_hour": "Charge Start Hour",
            f"{prefix}_discharge_start_hour": "Discharge Start Hour",
            f"{prefix}_profitable": "Profitable",
            "bucket": "Bucket",
        }
    )
    return out


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

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=monthly["local_month_label"],
                y=monthly["profitable_day_share"],
                marker_color=PALETTE["sea_soft"],
                name="Profitable day share",
                hovertemplate="%{x}<br>%{y:.1f}% of active days<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=monthly["local_month_label"],
                y=monthly["average_best_spread"],
                mode="lines+markers",
                marker={"size": 8},
                line={"width": 2.4, "color": PALETTE["accent"]},
                name="Average best spread",
                yaxis="y2",
                hovertemplate="%{x}<br>$%{y:.2f}/MWh<extra></extra>",
            )
        )
        fig.update_layout(
            yaxis={"title": "Profitable day share (%)", "gridcolor": PALETTE["line"], "zeroline": False},
            yaxis2={"title": "Average best spread ($/MWh)", "overlaying": "y", "side": "right", "showgrid": False},
            barmode="group",
        )
        _style_plot(fig, 330)
        st.plotly_chart(fig, use_container_width=True)

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

        st.dataframe(_representative_days(str(selected["location"]), profile_key, duration_hours), use_container_width=True, hide_index=True)

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
    selected = _selected_row(st.session_state["selected_location"])
    st.markdown("### Analyst Console")
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
    _render_map_section(selected_profile, selected_duration)
    st.markdown("---")
    _render_ranking_table(selected_profile)
    st.markdown("---")
    _render_analyst_console(selected_profile, selected_duration)
    st.markdown("---")
    _render_methodology(selected_profile)


if __name__ == "__main__":
    main()
