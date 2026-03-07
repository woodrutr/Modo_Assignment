"""Presentation-only Texas map helpers for the annual screener."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import plotly.graph_objects as go

from src.config import AppSettings, BODY_FONT, DURATION_OPTIONS, PALETTE, SCORE_SCALE, SETTINGS, lens_metric_column


_TX_OUTLINE_LON = [
    -103.002, -100.000, -100.000, -99.192, -98.576, -98.088, -97.483,
    -97.147, -96.937, -96.567, -96.328, -96.030, -95.542, -95.130,
    -94.915, -94.668, -94.485, -94.406, -94.024, -94.043, -94.043,
    -93.822, -93.814, -93.704, -93.669, -93.606, -93.521, -93.529,
    -93.731, -93.670, -93.397, -93.839, -94.691, -95.073, -94.761,
    -95.160, -95.228, -95.857, -96.216, -96.485, -96.620, -96.695,
    -97.013, -97.259, -97.378, -97.411, -97.339, -97.236, -97.167,
    -97.142, -97.395, -97.684, -98.083, -98.344, -98.712, -99.107,
    -99.459, -99.514, -100.055, -100.324, -100.470, -100.529, -100.658,
    -100.962, -101.398, -101.987, -102.305, -102.688, -103.093, -103.322,
    -103.718, -104.044, -104.367, -104.534, -104.683, -104.678, -104.859,
    -105.000, -105.256, -105.539, -105.742, -106.003, -106.377, -106.528,
    -106.618, -106.635, -106.633, -106.617, -103.064, -103.002, -103.002,
]
_TX_OUTLINE_LAT = [
    36.500, 36.500, 34.560, 34.214, 34.135, 33.752, 33.896,
    33.728, 33.939, 33.837, 33.691, 33.844, 33.864, 33.935,
    33.832, 33.672, 33.637, 33.549, 33.551, 33.012, 31.992,
    31.775, 31.537, 31.504, 31.268, 31.080, 30.936, 30.517,
    30.286, 30.058, 29.767, 29.688, 29.480, 29.307, 29.339,
    29.006, 28.857, 28.668, 28.502, 28.591, 28.339, 28.161,
    27.879, 27.694, 27.223, 26.916, 26.600, 26.398, 26.058,
    25.969, 25.843, 26.024, 26.060, 26.152, 26.341, 26.445,
    27.035, 27.577, 28.196, 28.629, 28.678, 28.814, 29.080,
    29.365, 29.771, 29.803, 29.879, 29.741, 29.052, 29.004,
    29.189, 29.316, 29.545, 29.669, 29.942, 30.124, 30.389,
    30.633, 30.794, 30.996, 31.166, 31.391, 31.731, 31.783,
    31.814, 31.866, 31.973, 32.001, 32.001, 32.001, 36.500,
]


def _anchor_frame(settings: AppSettings = SETTINGS) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "location": anchor.location,
                "map_label": anchor.map_label,
                "anchor_name": anchor.anchor_name,
                "anchor_note": anchor.anchor_note,
                "lat": anchor.lat,
                "lon": anchor.lon,
                "text_position": anchor.text_position,
            }
            for anchor in settings.location_anchors
        ]
    )


def _scale_marker_sizes(cost_reduction_pct: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(cost_reduction_pct, errors="coerce").fillna(0.0)
    clipped = numeric.clip(lower=0.0, upper=max(20.0, float(numeric.max())))
    if clipped.max() <= 0:
        return pd.Series(16.0, index=cost_reduction_pct.index, dtype=float)
    return 14.0 + (clipped / clipped.max() * 14.0)


def build_location_map_frame(
    metrics: pd.DataFrame,
    profile_key: str,
    duration_hours: int,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    score_column = lens_metric_column(profile_key, duration_hours, "score")
    rank_column = lens_metric_column(profile_key, duration_hours, "rank")
    reduction_column = lens_metric_column(profile_key, duration_hours, "annual_cost_reduction_pct")
    effective_price_column = lens_metric_column(profile_key, duration_hours, "effective_avg_price_usd_per_mwh")

    anchor_frame = _anchor_frame(settings)
    map_frame = (
        metrics.merge(anchor_frame, on="location", how="left", validate="one_to_one")
        .sort_values([rank_column, "location"], kind="mergesort")
        .reset_index(drop=True)
    )
    missing = map_frame.loc[map_frame["lat"].isna(), "location"].tolist()
    if missing:
        raise ValueError(f"Missing map anchor coordinates for: {missing}")

    map_frame["marker_size"] = _scale_marker_sizes(map_frame[reduction_column])
    map_frame["map_score"] = map_frame[score_column]
    map_frame["map_rank"] = map_frame[rank_column]
    map_frame["map_cost_reduction_pct"] = map_frame[reduction_column]
    map_frame["map_effective_avg_price"] = map_frame[effective_price_column]

    for other_duration in DURATION_OPTIONS:
        map_frame[f"{other_duration}h_score"] = map_frame[
            lens_metric_column(profile_key, other_duration, "score")
        ]
        map_frame[f"{other_duration}h_cost_reduction_pct"] = map_frame[
            lens_metric_column(profile_key, other_duration, "annual_cost_reduction_pct")
        ]
    return map_frame


def extract_selected_location(
    selection_event: object | None,
    map_frame: pd.DataFrame,
    fallback_location: str,
) -> str:
    if selection_event is None:
        return fallback_location

    selection_payload = getattr(selection_event, "selection", selection_event)
    if isinstance(selection_payload, Mapping) and "selection" in selection_payload:
        selection_payload = selection_payload["selection"]

    if isinstance(selection_payload, Mapping):
        points = selection_payload.get("points")
    else:
        points = getattr(selection_payload, "points", None)

    if not points:
        return fallback_location

    point = points[0]
    if isinstance(point, Mapping):
        point_index = point.get("point_index", point.get("pointNumber"))
    else:
        point_index = getattr(point, "point_index", getattr(point, "pointNumber", None))

    if point_index is None:
        return fallback_location
    if point_index < 0 or point_index >= len(map_frame):
        return fallback_location
    return str(map_frame.iloc[int(point_index)]["location"])


def build_texas_location_map(
    map_frame: pd.DataFrame,
    selected_location: str,
    profile_label: str,
    duration_label: str,
) -> go.Figure:
    selected_points = map_frame.index[map_frame["location"].eq(selected_location)].tolist()
    customdata = map_frame[
        [
            "location",
            "anchor_name",
            "anchor_note",
            "map_rank",
            "map_score",
            "map_cost_reduction_pct",
            "map_effective_avg_price",
            "4h_score",
            "8h_score",
            "best_fit_lens",
        ]
    ]

    figure = go.Figure()
    figure.add_trace(
        go.Scattergeo(
            lat=_TX_OUTLINE_LAT,
            lon=_TX_OUTLINE_LON,
            mode="lines",
            line={"color": "rgba(53, 90, 102, 0.35)", "width": 1.8},
            fill="toself",
            fillcolor="rgba(240, 236, 228, 0.45)",
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scattergeo(
            lat=map_frame["lat"],
            lon=map_frame["lon"],
            text=map_frame["map_label"],
            textposition=map_frame["text_position"],
            mode="markers+text",
            textfont={"family": BODY_FONT, "size": 10.5, "color": PALETTE["ink"]},
            customdata=customdata,
            selectedpoints=selected_points,
            marker={
                "size": map_frame["marker_size"],
                "color": map_frame["map_score"],
                "colorscale": SCORE_SCALE,
                "cmin": 0,
                "cmax": 100,
                "line": {"color": "rgba(255,255,255,0.85)", "width": 1.5},
                "opacity": 0.92,
                "colorbar": {
                    "title": {
                        "text": f"{profile_label}<br>{duration_label} score",
                        "font": {"size": 11, "family": BODY_FONT},
                    },
                    "thickness": 12,
                    "len": 0.42,
                    "y": 0.5,
                    "tickfont": {"size": 10, "family": BODY_FONT},
                    "outlinewidth": 0,
                },
            },
            selected={"marker": {"color": PALETTE["accent"], "size": 28, "opacity": 1.0}},
            unselected={"marker": {"opacity": 0.55}},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "%{customdata[1]}<br>"
                "<span style='color:#697274;font-size:11px'>%{customdata[2]}</span><br><br>"
                "Active lens rank: <b>#%{customdata[3]}</b><br>"
                "Active lens score: <b>%{customdata[4]:.1f}</b><br>"
                "Annual cost reduction: <b>%{customdata[5]:.1f}%</b><br>"
                "Effective average price: <b>$%{customdata[6]:.2f}/MWh</b><br>"
                "4h score: <b>%{customdata[7]:.1f}</b> · 8h score: <b>%{customdata[8]:.1f}</b><br>"
                "Best-fit lens: <b>%{customdata[9]}</b>"
                "<extra></extra>"
            ),
        )
    )
    figure.update_geos(
        projection_type="mercator",
        showland=True,
        landcolor="#eae4da",
        showocean=True,
        oceancolor="#dce6ea",
        showlakes=True,
        lakecolor="#dce6ea",
        showcountries=False,
        showsubunits=False,
        showcoastlines=True,
        coastlinecolor="rgba(53, 90, 102, 0.25)",
        coastlinewidth=0.8,
        bgcolor="rgba(0,0,0,0)",
        lataxis_range=[25.2, 37.0],
        lonaxis_range=[-107.5, -92.0],
    )
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=540,
        font={"family": BODY_FONT, "color": PALETTE["ink"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode="select",
    )
    return figure


__all__ = [
    "build_location_map_frame",
    "build_texas_location_map",
    "extract_selected_location",
]
