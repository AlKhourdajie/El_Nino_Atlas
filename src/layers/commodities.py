"""Realised-impact panel: monthly commodity prices from the World Bank Pink Sheet.

Source: World Bank, Prospects Group, Commodity Price Data (the Pink
Sheet), registry id ``worldbank_pink_sheet`` in ``src/sources.yaml``
(CC BY 4.0; redistribution yes). Nothing here fetches. The frame arrives
through ``src.data_access.load_frame`` and the events through the index
panel's RONI series.

``build_figure`` rebases the five default series to an index with
January 2010 equal to 100 so that five units share one axis, keeps the
nominal price and its unit in the hover text, and shades El Niño seasons
with ``src.layers.enso_index.add_event_shading``. Price transmission is
disputed, so the panel carries the second caption guardrail of
docs/DESIGN.md verbatim and states that the prices are nominal US dollars.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import plotly.graph_objects as go

from src import theme
from src.enso_events import Event
from src.layers.enso_index import add_event_shading
from src.layout.captions import PRICE_TRANSMISSION
from src.layout.explainer import Explainer
from src.schema import validate_frame

SOURCE_ID = "worldbank_pink_sheet"
BASE_MONTH = "2010-01-01"
BASE_VALUE = 100.0
SHADED_PHASES: tuple[str, ...] = ("el_nino",)

# Pink Sheet series ids, in legend order, with the label shown for each.
DEFAULT_SERIES: tuple[tuple[str, str], ...] = (
    ("COFFEE_ARABIC", "Coffee, arabica"),
    ("COFFEE_ROBUS", "Coffee, robusta"),
    ("COCOA", "Cocoa"),
    ("SUGAR_WLD", "Sugar, world"),
    ("RICE_05", "Rice, Thai 5%"),
)

SOURCE_NAME = "World Bank Commodity Price Data (the Pink Sheet)"
SOURCE_URL = "https://www.worldbank.org/en/research/commodity-markets"
LICENCE_LABEL = "CC BY 4.0"

REBASE_CAPTION = (
    "Prices are monthly averages in nominal US dollars, rebased so that January 2010 equals 100."
)

WHAT = (
    "Monthly world prices for five agricultural commodities: arabica coffee, robusta "
    "coffee, cocoa, sugar and rice. Each series is rebased so that January 2010 equals "
    "100, which puts five different units on one axis; hovering over a point shows the "
    "nominal price in its own unit. Shading marks El Niño seasons as in the index panel, "
    "so that price movements can be read against the state of the event."
)

HOW = (
    "The World Bank's Commodity Price Data, known as the Pink Sheet, is a monthly "
    "release of nominal US dollar prices for energy, agricultural, fertiliser and metal "
    "commodities, with most series from 1960, alongside price indices for each group. "
    "Each price is the average for the month of a stated grade in a stated market. The "
    "release and its documentation are on the "
    f"[World Bank commodity markets page]({SOURCE_URL})."
)

WHY = (
    "Coffee, cocoa, sugar and rice are grown in regions where El Niño shifts rainfall "
    "and temperature, so their world prices are among the first public series in which "
    "a realised effect on food and export earnings could appear. The panel puts the "
    "price series beside the El Niño seasons of the El Niño Southern Oscillation "
    "(ENSO) index so that the reader can see whether the two align during this event "
    "or diverge."
)

NOT_SHOWN = (
    "Co-movement here is descriptive, since prices respond to many drivers, among them "
    "stocks, exchange rates, energy and fertiliser costs, trade policy and demand, and a "
    "price move during an El Niño season therefore stands as an observation without "
    "attribution or size estimate. The series are nominal, so long-run movements "
    "include inflation, and they are world prices, distinct from what producers "
    "received or consumers paid in any one country."
)


def explainer() -> Explainer:
    return Explainer(
        title="Commodity prices: the World Bank Pink Sheet",
        what=WHAT,
        how=HOW,
        why=WHY,
        not_shown=NOT_SHOWN,
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        licence_label=LICENCE_LABEL,
        captions=(REBASE_CAPTION, PRICE_TRANSMISSION),
    )


def _series(frame: pd.DataFrame, series_id: str) -> pd.DataFrame:
    """The rows of one series in date order, or a ``ValueError`` naming the fault."""
    rows = frame[frame["series_id"] == series_id]
    if rows.empty:
        raise ValueError(f"frame has no rows with series_id {series_id!r}")
    if rows["region"].nunique() != 1:
        raise ValueError(f"series {series_id!r} spans regions {sorted(rows['region'].unique())}")
    if rows["unit"].nunique() != 1:
        raise ValueError(f"series {series_id!r} mixes units {sorted(rows['unit'].unique())}")
    return rows.sort_values("date").reset_index(drop=True)


def _rebased(rows: pd.DataFrame, series_id: str) -> pd.Series:
    base = rows.loc[rows["date"] == BASE_MONTH, "value"]
    if base.empty:
        raise ValueError(f"series {series_id!r} has no value for {BASE_MONTH}, the base month")
    return rows["value"] / base.iloc[0] * BASE_VALUE


def build_figure(
    frame: pd.DataFrame,
    events: Iterable[Event],
    series: tuple[tuple[str, str], ...] = DEFAULT_SERIES,
) -> go.Figure:
    """The commodity panel: each series as an index with January 2010 equal to 100.

    ``frame`` is the ``worldbank_pink_sheet`` contract frame; every id in
    ``series`` must be present with a value for the base month, or a
    ``ValueError`` names the fault. ``events`` are the RONI event records;
    El Niño seasons are shaded, and an event with no end is shaded to the
    end of the last month in the frame. The x axis spans the price record,
    so an event before the first price month cannot widen it.
    """
    validate_frame(frame)
    fig = go.Figure()
    first_month = "9999-12-31"
    last_month = ""
    for rank, (series_id, label) in enumerate(series, start=1):
        rows = _series(frame, series_id)
        unit = rows["unit"].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=rows["date"].tolist(),
                y=_rebased(rows, series_id).tolist(),
                name=label,
                mode="lines",
                legendrank=rank,
                customdata=[[value, unit] for value in rows["value"]],
                hovertemplate="%{y:.1f} (%{customdata[0]:.2f} %{customdata[1]})<extra></extra>",
            )
        )
        first_month = min(first_month, rows["date"].iloc[0])
        last_month = max(last_month, rows["date"].iloc[-1])

    until = pd.Timestamp(last_month) + pd.DateOffset(months=1)
    add_event_shading(fig, events, until=until.date(), phases=SHADED_PHASES)
    fig.add_hline(y=BASE_VALUE, line=theme.THRESHOLD_LINE)
    fig.update_xaxes(
        type="date",
        range=[first_month, until.strftime("%Y-%m-%d")],
        hoverformat="%b %Y",
    )
    fig.update_yaxes(title_text="Index (January 2010 = 100)")
    fig.update_layout(hovermode="x unified", **theme.RESPONSIVE_LAYOUT)
    return fig
