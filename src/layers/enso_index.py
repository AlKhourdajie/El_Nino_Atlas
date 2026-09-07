"""Forecast-stage panel: the state of ENSO as the RONI and ONI series.

Source: NOAA Climate Prediction Center, registry id ``noaa_oni`` in
``src/sources.yaml`` (US Government work, public domain; redistribution
yes). Nothing here fetches. The frame arrives through
``src.data_access.load_frame`` and the events through
``src.enso_events.enso_event_records`` applied to the RONI rows.

``build_figure`` draws the Relative Oceanic Niño Index (RONI) as the
primary line and the Oceanic Niño Index (ONI) as a muted secondary line,
both in degrees C, and shades the seasons of every event it is given.
Each value is a three-month season dated by its centre month, so an
event is shaded from the first month of its first season to the end of
the last month of its last season. An event whose ``end`` is ``None`` is
shaded to the end of the last season in the frame. A provisional event
has a dashed outline and the label "provisional". ``add_event_shading``
is shared with the commodity panel.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

import pandas as pd
import plotly.graph_objects as go

from src import theme
from src.enso_events import THRESHOLD_C, Event, season_label
from src.layout.captions import TEMPERATURE_CONTRIBUTION
from src.layout.explainer import Explainer
from src.schema import validate_frame

SOURCE_ID = "noaa_oni"
PRIMARY_SERIES = "RONI"
SECONDARY_SERIES = "ONI"
UNIT = "degC"
RECORD_START_YEAR = 1950
DEFAULT_WINDOW_YEARS = 30
PHASES: tuple[str, ...] = ("el_nino", "la_nina")

SOURCE_NAME = "NOAA Climate Prediction Center"
SOURCE_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php"
RONI_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/announcement.php"
LICENCE_LABEL = "US public domain"

RANGE_BUTTONS: tuple[dict, ...] = (
    {"label": f"From {RECORD_START_YEAR}", "step": "all"},
    {
        "label": f"{DEFAULT_WINDOW_YEARS} years",
        "count": DEFAULT_WINDOW_YEARS,
        "step": "year",
        "stepmode": "backward",
    },
    {"label": "5 years", "count": 5, "step": "year", "stepmode": "backward"},
)

_LEGEND_RANK = {"el_nino": 1010, "la_nina": 1020}

WHAT = (
    "The coloured line is the Relative Oceanic Niño Index (RONI) and the grey line "
    "is the Oceanic Niño Index (ONI), two indices that the NOAA Climate Prediction "
    "Center publishes for the El Niño Southern Oscillation (ENSO). Each point is a "
    "three-month season in degrees C, plotted at its centre month. Shading marks "
    "the seasons of each event that the five-season rule yields when applied to "
    "RONI: warm shading for El Niño and light cool shading for La Niña. A dashed "
    "outline and the word provisional mark an event whose classification can "
    "still change."
)

HOW = (
    "The Climate Prediction Center defines RONI as the Niño 3.4 sea surface "
    "temperature anomaly minus the average anomaly of the global tropics, rescaled "
    "to the traditional index. Both indices are three-month running means in "
    "degrees C, and the same rule applies to both: El Niño or La Niña conditions "
    "are identified when the index is at or beyond plus or minus 0.5 °C for five "
    "consecutive overlapping three-month seasons. The definition is set out in the "
    f"[CPC RONI announcement]({RONI_URL})."
)

WHY = (
    "ENSO is the largest source of year-to-year variation in the global climate, "
    "and every forecast, activation and impact on this page is tied to the state "
    "of the event that this index measures. Because the tropical oceans have "
    "warmed, the Niño 3.4 anomaly on its own partly reflects the background trend; "
    "RONI subtracts the tropical mean so that the index follows the contrast that "
    "drives the atmospheric response. The two lines diverge most when the whole "
    "tropics are warm."
)

NOT_SHOWN = (
    "A seasonal index is neither a weekly value nor an impact. It does not show "
    "rainfall, temperature or losses in any place, and it does not show the "
    "forecasts issued ahead of the event. A single season at or beyond the "
    "threshold is shaded only once the five-season rule is met, so the "
    "classification of the latest seasons can change as new months arrive."
)


def explainer() -> Explainer:
    return Explainer(
        title="Relative Oceanic Niño Index (RONI) and Oceanic Niño Index (ONI)",
        what=WHAT,
        how=HOW,
        why=WHY,
        not_shown=NOT_SHOWN,
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        licence_label=LICENCE_LABEL,
        captions=(TEMPERATURE_CONTRIBUTION,),
    )


def _iso(stamp: pd.Timestamp) -> str:
    return stamp.strftime("%Y-%m-%d")


def _series(frame: pd.DataFrame, series_id: str) -> pd.DataFrame:
    """The rows of one series in date order, or a ``ValueError`` naming the fault."""
    rows = frame[frame["series_id"] == series_id]
    if rows.empty:
        raise ValueError(f"frame has no rows with series_id {series_id!r}")
    if rows["region"].nunique() != 1:
        raise ValueError(f"series {series_id!r} spans regions {sorted(rows['region'].unique())}")
    units = sorted(set(rows["unit"]))
    if units != [UNIT]:
        raise ValueError(f"series {series_id!r} must be in {UNIT!r}, got {units}")
    return rows.sort_values("date").reset_index(drop=True)


def _line(rows: pd.DataFrame, name: str, colour: str, width: float, rank: int) -> go.Scatter:
    return go.Scatter(
        x=rows["date"].tolist(),
        y=rows["value"].tolist(),
        name=name,
        mode="lines",
        line={"color": colour, "width": width},
        legendrank=rank,
        customdata=[season_label(text) for text in rows["date"]],
        hovertemplate=f"{name} %{{y:.2f}} °C (%{{customdata}})<extra></extra>",
    )


def shading_span(event: Event, until: date) -> tuple[str, str]:
    """ISO bounds of the shaded span for ``event``.

    A season starts one month before its centre month and ends two months
    after it, so the span runs from the onset month less one to the end
    month plus two, the latter exclusive. ``until`` is the exclusive end
    for an event whose ``end`` is ``None``.
    """
    start = pd.Timestamp(event.onset) - pd.DateOffset(months=1)
    if event.end is None:
        stop = pd.Timestamp(until)
    else:
        stop = pd.Timestamp(event.end) + pd.DateOffset(months=2)
    return _iso(start), _iso(stop)


def add_event_shading(
    fig: go.Figure,
    events: Iterable[Event],
    until: date,
    phases: tuple[str, ...] = PHASES,
) -> None:
    """Shade the seasons of every event in ``events`` whose phase is in ``phases``.

    Each phase gets one legend entry. ``until`` is the exclusive end of
    the shading for an event whose ``end`` is ``None``. A provisional
    event has a dashed outline and the label "provisional". An event with
    a phase outside ``theme.PHASE_COLOURS`` raises ``ValueError``.
    """
    shown: set[str] = set()
    for event in events:
        if event.phase not in theme.PHASE_COLOURS:
            raise ValueError(f"unknown event phase {event.phase!r}")
        if event.phase not in phases:
            continue
        x0, x1 = shading_span(event, until)
        colour = theme.PHASE_COLOURS[event.phase]
        shape: dict = {
            "x0": x0,
            "x1": x1,
            "fillcolor": theme.rgba(colour, theme.PHASE_OPACITY[event.phase]),
            "line": {"width": 0},
            "layer": "below",
            "name": theme.PHASE_LABELS[event.phase],
            "legendgroup": event.phase,
            "legendrank": _LEGEND_RANK[event.phase],
            "showlegend": event.phase not in shown,
        }
        if event.provisional:
            shape["line"] = {"color": colour, "width": 1.5, "dash": "dash"}
            shape["label"] = {
                "text": "provisional",
                "textposition": "top center",
                "font": {"size": 11, "color": colour},
            }
        fig.add_vrect(**shape)
        shown.add(event.phase)


def build_figure(frame: pd.DataFrame, events: Iterable[Event]) -> go.Figure:
    """The index panel: RONI over ONI in degrees C with event seasons shaded.

    ``frame`` is the ``noaa_oni`` contract frame holding the series
    ``RONI`` and ``ONI``; ``events`` are the records for the RONI series.
    The default view is the last ``DEFAULT_WINDOW_YEARS`` years, ending
    with the last season in the frame; range buttons give the record
    from 1950, the last 30 years and the last 5 years.
    """
    validate_frame(frame)
    primary = _series(frame, PRIMARY_SERIES)
    secondary = _series(frame, SECONDARY_SERIES)
    last_centre = pd.Timestamp(max(primary["date"].iloc[-1], secondary["date"].iloc[-1]))
    x_end = last_centre + pd.DateOffset(months=2)
    x_start = x_end - pd.DateOffset(years=DEFAULT_WINDOW_YEARS)

    fig = go.Figure()
    fig.add_trace(_line(secondary, SECONDARY_SERIES, theme.INDEX_LINE_COLOURS["secondary"], 1.2, 2))
    fig.add_trace(_line(primary, PRIMARY_SERIES, theme.INDEX_LINE_COLOURS["primary"], 2.2, 1))
    add_event_shading(fig, events, until=x_end.date())
    fig.add_hline(
        y=THRESHOLD_C,
        line=theme.THRESHOLD_LINE,
        annotation_text=f"±{THRESHOLD_C} °C",
        annotation_position="top left",
        annotation_font_size=11,
        annotation_font_color=theme.MUTED_LINE,
    )
    fig.add_hline(y=-THRESHOLD_C, line=theme.THRESHOLD_LINE)

    fig.update_xaxes(
        type="date",
        range=[_iso(x_start), _iso(x_end)],
        rangeselector={"buttons": list(RANGE_BUTTONS)},
        hoverformat="%b %Y",
    )
    fig.update_yaxes(title_text="Anomaly (°C)", zeroline=True)
    fig.update_layout(hovermode="x unified")
    return fig
