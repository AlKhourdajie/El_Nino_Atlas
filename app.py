"""Dash application for the El Niño Atlas.

The app is built at import time so that ``gunicorn app:server`` works
unchanged; ``run.py`` imports the same object for local serving.

``build_page`` assembles the page along the forecast, action, impact
spine: the opening line with the latest-reading line beneath it, the
About block, the index panel, the activations container, the commodity
panel, the teleconnection schematic panel and the footer. Each data
panel reads its snapshot through ``src.data_access``. A missing
snapshot, the ``FileNotFoundError`` that ``load_frame`` raises, renders
the panel's explainer with a visible notice and omits the latest-reading
line; every other error propagates. The commodity panel needs both
snapshots, because its shading comes from the index events. The
schematic panel shows a static asset and needs no snapshot.
"""

import dash
import dash_bootstrap_components as dbc

from src import data_access, layout, theme
from src.enso_events import Event, enso_event_records
from src.layers import commodities, enso_index, teleconnections

EVENT = "The event"
REALISED_IMPACT = "Realised impact"


def _snapshot(source_id: str) -> tuple | None:
    """The snapshot frame and its metadata, or ``None`` when no snapshot exists."""
    try:
        frame = data_access.load_frame(source_id)
    except FileNotFoundError:
        return None
    return frame, data_access.snapshot_metadata(source_id)


def _index_panel(snapshot: tuple | None, events: list[Event] | None) -> object:
    explainer = enso_index.explainer()
    if snapshot is None:
        return layout.unavailable_panel(EVENT, explainer, id="panel-index")
    frame, metadata = snapshot
    figure = enso_index.build_figure(frame, events)
    return layout.panel(EVENT, explainer, figure, metadata["retrieved_at"], id="panel-index")


def _commodity_panel(snapshot: tuple | None, events: list[Event] | None) -> object:
    explainer = commodities.explainer()
    if snapshot is None or events is None:
        return layout.unavailable_panel(REALISED_IMPACT, explainer, id="panel-commodities")
    frame, metadata = snapshot
    figure = commodities.build_figure(frame, events)
    return layout.panel(
        REALISED_IMPACT, explainer, figure, metadata["retrieved_at"], id="panel-commodities"
    )


def build_page(image_src: str = teleconnections.IMAGE_URL_PATH) -> dbc.Container:
    """The page, from whichever snapshots exist at the time of the call.

    ``image_src`` is the URL the app serves the teleconnection schematic
    from. The module passes ``app.get_asset_url`` so that the image
    follows whatever path prefix the deployment sets.
    """
    index = _snapshot(enso_index.SOURCE_ID)
    events = None
    reading = None
    if index is not None:
        frame = index[0]
        events = enso_event_records(frame[frame["series_id"] == enso_index.PRIMARY_SERIES])
        reading = enso_index.latest_reading(frame, events)
    prices = _snapshot(commodities.SOURCE_ID)
    return layout.page(
        layout.opening(reading),
        layout.about(),
        _index_panel(index, events),
        layout.container("panel-activations"),
        _commodity_panel(prices, events),
        teleconnections.build_image_panel(image_src),
        layout.footer(),
    )


theme.register_templates()

app = dash.Dash(
    __name__,
    title=layout.TITLE,
    external_stylesheets=[dbc.themes.FLATLY],
)
app.layout = build_page(image_src=app.get_asset_url(teleconnections.IMAGE_ASSET))

server = app.server
