from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import plotly.graph_objects as go

from src.config import AppSettings, BODY_FONT, PALETTE, SCORE_SCALE, SETTINGS


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


def build_location_map_frame(
    metrics: pd.DataFrame,
    battery: pd.DataFrame,
    settings: AppSettings = SETTINGS,
) -> pd.DataFrame:
    anchor_frame = _anchor_frame(settings)
    battery_fields = battery.loc[
        :,
        ["location", "annual_battery_gross_margin_usd", "pct_positive_value_days"],
    ]
    map_frame = (
        metrics.merge(
            battery_fields,
            on="location",
            how="left",
            validate="one_to_one",
        )
        .merge(
            anchor_frame,
            on="location",
            how="left",
            validate="one_to_one",
        )
        .sort_values("rank")
        .reset_index(drop=True)
    )

    missing_locations = map_frame.loc[map_frame["lat"].isna(), "location"].tolist()
    if missing_locations:
        raise ValueError(f"Missing map anchor coordinates for: {missing_locations}")

    map_frame["marker_size"] = 14.0 + (map_frame["battery_opportunity_score"] / 5.0)
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
        selection_payload = selection_payload.get("selection", {})

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
) -> go.Figure:
    selected_points = map_frame.index[
        map_frame["location"].eq(selected_location)
    ].tolist()
    customdata = map_frame[
        [
            "location",
            "anchor_name",
            "anchor_note",
            "battery_opportunity_score",
            "avg_daily_spread",
            "annual_battery_gross_margin_usd",
        ]
    ]

    figure = go.Figure()
    figure.add_trace(
        go.Scattergeo(
            lat=map_frame["lat"],
            lon=map_frame["lon"],
            text=map_frame["map_label"],
            textposition=map_frame["text_position"],
            mode="markers+text",
            textfont={
                "family": BODY_FONT,
                "size": 11,
                "color": "#475457",
            },
            customdata=customdata,
            selectedpoints=selected_points,
            marker={
                "size": map_frame["marker_size"],
                "color": map_frame["battery_opportunity_score"],
                "colorscale": SCORE_SCALE,
                "cmin": 0,
                "cmax": 100,
                "line": {
                    "color": "rgba(255,255,255,0.72)",
                    "width": 1.2,
                },
                "colorbar": {"title": "Score"},
                "opacity": 0.94,
            },
            selected={
                "marker": {
                    "color": PALETTE["accent"],
                    "size": 31,
                    "opacity": 1.0,
                }
            },
            unselected={"marker": {"opacity": 0.66}},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Anchor: %{customdata[1]}<br>"
                "%{customdata[2]}<br>"
                "Battery opportunity score: %{customdata[3]:.1f}<br>"
                "Average daily spread: %{customdata[4]:.1f} $/MWh<br>"
                "Battery gross margin: $%{customdata[5]:,.0f}<extra></extra>"
            ),
        )
    )

    figure.update_geos(
        projection_type="mercator",
        showland=True,
        landcolor="#f0e6d8",
        showocean=True,
        oceancolor="#d8e4e8",
        showlakes=True,
        lakecolor="#d8e4e8",
        showcountries=False,
        showsubunits=True,
        subunitcolor="rgba(53, 90, 102, 0.28)",
        subunitwidth=0.8,
        coastlinecolor="rgba(53, 90, 102, 0.44)",
        bgcolor="rgba(0,0,0,0)",
        lataxis_range=[25.0, 36.8],
        lonaxis_range=[-107.0, -92.5],
    )
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=540,
        font={"family": BODY_FONT, "color": PALETTE["ink"]},
    )
    return figure


__all__ = [
    "build_location_map_frame",
    "build_texas_location_map",
    "extract_selected_location",
]
