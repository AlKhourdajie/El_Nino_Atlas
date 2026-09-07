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
is shared with the commodity panel. The bands are low-opacity tints
behind the lines: a La Niña band carries a dotted outline so that the
phases differ in more than hue, and the hover text names the phase of
every shaded season, so colour never carries the phase alone.

The range presets that used to sit in the figure live in the shared
time-range bar that ``src.layout.time_controls`` builds from
``RANGE_BUTTONS``; the two time-series panels share one x-axis window.

``latest_reading`` builds the one-line summary of the latest season that
the page shows beneath its opening line: the season's months, the RONI
and ONI values with their signs, and the word provisional while the RONI
run that reaches that season is shorter than five seasons.
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
PROVISIONAL_LABEL = "provisional"

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
    "The Climate Prediction Center (CPC) defines RONI as the Niño 3.4 sea surface "
    "temperature anomaly minus the average anomaly of the global tropics, 20°N to 20°S, "
    "rescaled to the traditional index. Both indices are three-month running means in "
    "degrees C, and the same rule applies to both: El Niño or La Niña conditions "
    "are identified when the index is at or beyond plus or minus 0.5 °C for five "
    "consecutive overlapping three-month seasons. The atlas applies the rule to the "
    "one-decimal values that CPC publishes, which is how CPC's own episode tables are "
    "built. The definition is set out in the "
    f"[CPC RONI announcement]({RONI_URL})."
)

READING_PREFIX = "Latest three-month season"
NOT_ASSESSED_TEXT = "not assessed"
MONTHS: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
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
    "A seasonal index measures the state of the ocean. Weekly values, local rainfall "
    "and temperature, losses in any place, and the forecasts issued ahead of the event "
    "lie outside this panel. The latest seasons are shaded only once the five-season "
    "rule is met."
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


def _shift(centre: date, months: int) -> tuple[int, int]:
    """The (year, month) that lies ``months`` after ``centre``; ``months`` may be negative."""
    year, month_index = divmod(centre.year * 12 + centre.month - 1 + months, 12)
    return year, month_index + 1


def season_span(centre: date | str) -> str:
    """The months of the season centred on ``centre``, e.g. 'June to August 2026'.

    ``centre`` is a ``date`` or the ISO string of the centre month. A
    season that crosses a year boundary names both years, as in
    'December 2026 to February 2027'.
    """
    if isinstance(centre, str):
        centre = date.fromisoformat(centre)
    start_year, start_month = _shift(centre, -1)
    end_year, end_month = _shift(centre, 1)
    if start_year == end_year:
        return f"{MONTHS[start_month - 1]} to {MONTHS[end_month - 1]} {end_year}"
    return f"{MONTHS[start_month - 1]} {start_year} to {MONTHS[end_month - 1]} {end_year}"


def latest_reading(frame: pd.DataFrame, events: Iterable[Event]) -> str:
    """One line on the latest season, shown beneath the page's opening line.

    'Latest three-month season (June to August 2026): RONI +1.36 °C,
    ONI +1.80 °C, provisional.' The season is the last one in the RONI
    series. The ONI value is the one for the same season, or "not
    assessed" when the ONI series has none. ``events`` are the RONI
    event records; the word provisional appears when the run that
    reaches the latest season is still shorter than five seasons, so
    its classification can change.
    """
    validate_frame(frame)
    primary = _series(frame, PRIMARY_SERIES)
    secondary = _series(frame, SECONDARY_SERIES)
    last = primary.iloc[-1]
    readings = [f"{PRIMARY_SERIES} {last['value']:+.2f} °C"]
    match = secondary.loc[secondary["date"] == last["date"], "value"]
    if match.empty:
        readings.append(f"{SECONDARY_SERIES} {NOT_ASSESSED_TEXT}")
    else:
        readings.append(f"{SECONDARY_SERIES} {match.iloc[0]:+.2f} °C")
    if any(event.end is None and event.provisional for event in events):
        readings.append("provisional")
    return f"{READING_PREFIX} ({season_span(last['date'])}): {', '.join(readings)}."


def season_phases(events: Iterable[Event]) -> dict[str, str]:
    """The phase label of every season an event covers, keyed by the season label.

    A provisional run's seasons carry the word provisional after the
    phase label, as the reading line does.
    """
    phases: dict[str, str] = {}
    for event in events:
        if event.phase not in theme.PHASE_COLOURS:
            raise ValueError(f"unknown event phase {event.phase!r}")
        label = theme.PHASE_LABELS[event.phase]
        if event.provisional:
            label = f"{label}, {PROVISIONAL_LABEL}"
        for season in event.seasons:
            phases[season] = label
    return phases


def _line(
    rows: pd.DataFrame,
    name: str,
    colour: str,
    width: float,
    rank: int,
    phases: dict[str, str],
) -> go.Scatter:
    seasons = [season_label(text) for text in rows["date"]]
    customdata = [[season, phases.get(season, "")] for season in seasons]
    return go.Scatter(
        x=rows["date"].tolist(),
        y=rows["value"].tolist(),
        name=name,
        mode="lines",
        line={"color": colour, "width": width},
        legendrank=rank,
        customdata=customdata,
        hovertemplate=(
            f"{name} %{{y:.2f}} °C (%{{customdata[0]}}) %{{customdata[1]}}<extra></extra>"
        ),
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
    the shading for an event whose ``end`` is ``None``. A band is a
    low-opacity tint in the phase hue; a La Niña band adds a dotted
    outline in the muted ink. A provisional event has a dashed outline
    and the label "provisional", both in the muted ink, anchored to the
    top right corner of its shading with the text running left, so that
    a run ending at the axis edge keeps its label inside the plot area
    on a narrow screen. An event with a phase outside
    ``theme.PHASE_COLOURS`` raises ``ValueError``.
    """
    shown: set[str] = set()
    for event in events:
        if event.phase not in theme.PHASE_COLOURS:
            raise ValueError(f"unknown event phase {event.phase!r}")
        if event.phase not in phases:
            continue
        x0, x1 = shading_span(event, until)
        colour = theme.PHASE_COLOURS[event.phase]
        outline = theme.PHASE_OUTLINE.get(event.phase)
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
        if outline:
            shape["line"] = {"color": theme.BAND_OUTLINE, "width": 1, "dash": outline}
        if event.provisional:
            shape["line"] = {"color": theme.BAND_OUTLINE, "width": 1.5, "dash": "dash"}
            shape["label"] = {
                "text": PROVISIONAL_LABEL,
                "textposition": "top right",
                "xanchor": "right",
                "yanchor": "top",
                "padding": 6,
                "font": {"size": 11, "color": theme.BAND_OUTLINE},
            }
        fig.add_vrect(**shape)
        shown.add(event.phase)


def build_figure(frame: pd.DataFrame, events: Iterable[Event]) -> go.Figure:
    """The index panel: RONI over ONI in degrees C with event seasons shaded.

    ``frame`` is the ``noaa_oni`` contract frame holding the series
    ``RONI`` and ``ONI``; ``events`` are the records for the RONI series.
    The default view is the last ``DEFAULT_WINDOW_YEARS`` years, ending
    with the last season in the frame; the shared time-range bar gives
    the record from 1950, the last 30 years, the last 5 years and every
    event in the data.
    """
    validate_frame(frame)
    events = list(events)
    primary = _series(frame, PRIMARY_SERIES)
    secondary = _series(frame, SECONDARY_SERIES)
    last_centre = pd.Timestamp(max(primary["date"].iloc[-1], secondary["date"].iloc[-1]))
    x_end = last_centre + pd.DateOffset(months=2)
    x_start = x_end - pd.DateOffset(years=DEFAULT_WINDOW_YEARS)
    phases = season_phases(events)

    fig = go.Figure()
    fig.add_trace(
        _line(secondary, SECONDARY_SERIES, theme.INDEX_LINE_COLOURS["secondary"], 1.2, 2, phases)
    )
    fig.add_trace(
        _line(primary, PRIMARY_SERIES, theme.INDEX_LINE_COLOURS["primary"], 2.2, 1, phases)
    )
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

    fig.update_xaxes(type="date", range=[_iso(x_start), _iso(x_end)], hoverformat="%b %Y")
    fig.update_yaxes(title_text="Anomaly (°C)", zeroline=True)
    fig.update_layout(hovermode="x unified", **theme.RESPONSIVE_LAYOUT)
    return fig
