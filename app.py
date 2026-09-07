"""Dash application for the El Niño Atlas.

The app is built at import time so that ``gunicorn app:server`` works
unchanged; ``run.py`` imports the same object for local serving.

``build_page`` assembles the page: the skip link, the sticky navigation,
the hero (title, maintainer line, opening line, latest-reading line,
scope line), the About block, the shared time-range bar, the index
card, the commodity card, the activation card, the teleconnection
schematic card, the sources section and the footer. The index and
commodity panels read their snapshots through ``src.data_access``. A
missing snapshot, the ``FileNotFoundError`` that ``load_frame`` raises,
renders the panel's explainer with a visible notice and omits the
latest-reading line. Any other failure to load or draw a panel's data
renders a visible error banner naming the source and the error, so the
page never shows a placeholder series or a blank panel. The commodity
panel needs both snapshots, because its shading comes from the index
events. The activation panel reads the curated register through
``src.activations`` with example entries excluded. The schematic panel
shows a static asset.

The callbacks are clientside functions in ``assets/atlas.js`` apart
from the CSV download, which the server builds from the frames the page
was assembled from. The view state (shared time range, phase bands,
isolated series) lives in the URL through ``dcc.Location``.
"""

from __future__ import annotations

import gzip
import logging
import os
import subprocess
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import dash
import yaml
from dash import ClientsideFunction, Input, Output, State, ctx, dcc, html
from flask import request

from src import activations, data_access, layout, theme
from src.enso_events import Event, enso_event_records, season_label
from src.layers import activations_map, commodities, enso_index, teleconnections
from src.layout import viewstate
from src.plotly_template import TEMPLATES, TOKENS
from src.schema import registry

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
CITATION_PATH = ROOT / "CITATION.cff"

EVENT = "The event"
ANTICIPATORY_ACTION = "Anticipatory action"
REALISED_IMPACT = "Realised impact"

MAP_ID = layout.GRAPH_IDS["activations"]
INDEX_GRAPH_ID = layout.GRAPH_IDS["index"]
PRICES_GRAPH_ID = layout.GRAPH_IDS["commodities"]
REGISTER_SOURCE = "data/curated/activations.yaml"
ACTIVATIONS_REGISTRY_ID = "ocha_cerf_anticipatory_action"

CSV_STEMS: dict[str, str] = {
    "index": "el-nino-atlas-index",
    "commodities": "el-nino-atlas-commodity-prices",
    "activations": "el-nino-atlas-activations",
}

SKELETON = """<div id="react-entry-point">
    <div class="_dash-loading" role="status" aria-label="Loading">
        <span class="skeleton skeleton--title"></span>
        <span class="skeleton skeleton--line"></span>
        <span class="skeleton skeleton--line is-short"></span>
        <span class="skeleton skeleton--card"></span>
        <span class="skeleton skeleton--card"></span>
        <span class="skeleton skeleton--card"></span>
    </div>
</div>"""

# Sets the stored colour scheme before the first paint, so that a reader
# who chose the dark scheme never sees the light one flash.
THEME_SCRIPT = """<script>
(function () {
  try {
    var stored = JSON.parse(window.localStorage.getItem("theme-store"));
    if (stored === "dark" || stored === "light") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (err) {}
})();
</script>"""

INDEX_STRING = """<!DOCTYPE html>
<html lang="en-GB">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        THEME_SCRIPT
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>""".replace("THEME_SCRIPT", THEME_SCRIPT)


@dataclass(frozen=True)
class LoadFailure:
    """A data load or figure build that raised: the source and the error."""

    source: str
    error: str


@dataclass
class PageData:
    """What the page was assembled from, kept for the CSV downloads."""

    index: tuple | None = None
    prices: tuple | None = None
    events: list[Event] | None = None
    entries: list[dict] | None = None
    csv_keys: list[str] = field(default_factory=list)
    graph_keys: list[str] = field(default_factory=list)


def _describe(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _source_label(source_id: str) -> str:
    return f"{registry()[source_id]['name']} ({source_id})"


def _snapshot(source_id: str) -> tuple | None | LoadFailure:
    """The snapshot frame and its metadata.

    ``None`` when no snapshot exists; a ``LoadFailure`` when the snapshot
    exists and fails to load or validate, with the error logged.
    """
    try:
        frame = data_access.load_frame(source_id)
    except FileNotFoundError:
        return None
    except Exception as exc:
        logger.exception("snapshot %s failed to load", source_id)
        return LoadFailure(_source_label(source_id), _describe(exc))
    try:
        metadata = data_access.snapshot_metadata(source_id)
    except Exception as exc:
        logger.exception("snapshot metadata %s failed to load", source_id)
        return LoadFailure(_source_label(source_id), _describe(exc))
    return frame, metadata


def _register() -> list[dict] | LoadFailure:
    try:
        return activations.load_activations()
    except Exception as exc:
        logger.exception("the activation register failed to load")
        return LoadFailure(REGISTER_SOURCE, _describe(exc))


def _export_source(attribution: str, retrieved_at: str | None) -> str:
    """The one source line an exported figure carries."""
    parts = [attribution.rstrip(".")]
    if retrieved_at:
        parts.append(f"Retrieved {retrieved_at}")
    parts.append(f"{layout.TITLE}, {layout.CITATION_URL}")
    return ". ".join(parts) + "."


def _export_meta(key: str, graph_id: str, attribution: str, retrieved_at: str | None) -> dcc.Store:
    return dcc.Store(
        id=f"export-meta-{key}",
        data={
            "graph": graph_id,
            "source": _export_source(attribution, retrieved_at),
            "stem": CSV_STEMS[key],
        },
    )


def _index_panel(snapshot, events: list[Event] | None, data: PageData) -> html.Section:
    explainer = enso_index.explainer()
    if isinstance(snapshot, LoadFailure):
        return layout.error_panel(
            EVENT, explainer, id="panel-index", source=snapshot.source, error=snapshot.error
        )
    if snapshot is None:
        return layout.unavailable_panel(EVENT, explainer, id="panel-index")
    frame, metadata = snapshot
    try:
        figure = enso_index.build_figure(frame, events or [])
    except Exception as exc:
        logger.exception("the index figure failed to build")
        return layout.error_panel(
            EVENT,
            explainer,
            id="panel-index",
            source=_source_label(enso_index.SOURCE_ID),
            error=_describe(exc),
        )
    data.csv_keys.append("index")
    data.graph_keys.append("index")
    panel = layout.panel(
        EVENT,
        explainer,
        figure,
        metadata["retrieved_at"],
        id="panel-index",
        graph_id=INDEX_GRAPH_ID,
        toolbar=layout.download_toolbar("index"),
    )
    attribution = registry()[enso_index.SOURCE_ID]["attribution"]
    panel.children.append(
        _export_meta("index", INDEX_GRAPH_ID, attribution, metadata["retrieved_at"])
    )
    return panel


def _activation_panel(entries, data: PageData, topojson_url: str) -> html.Section:
    """The activation map beneath the shared three-state legend, with its entry table."""
    explainer = activations_map.explainer()
    if isinstance(entries, LoadFailure):
        return layout.error_panel(
            ANTICIPATORY_ACTION,
            explainer,
            id="panel-activations",
            source=entries.source,
            error=entries.error,
        )
    try:
        figure = activations_map.build_figure(entries)
        table = activations_map.build_table(entries)
    except Exception as exc:
        logger.exception("the activation map failed to build")
        return layout.error_panel(
            ANTICIPATORY_ACTION,
            explainer,
            id="panel-activations",
            source=REGISTER_SOURCE,
            error=_describe(exc),
        )
    data.csv_keys.append("activations")
    data.graph_keys.append("activations")
    column = html.Div(
        [
            layout.legend(),
            layout.graph(
                figure, id=MAP_ID, height=theme.MAP_HEIGHT, config=layout.map_config(topojson_url)
            ),
        ]
    )
    note = None
    if activations_map.has_discrepancies(entries):
        note = html.P(
            html.A(activations_map.DISCREPANCY_PREFIX.strip(), href="#activations-table-wrap"),
            className="card__note",
        )
    attribution = registry()[ACTIVATIONS_REGISTRY_ID]["attribution"]
    return layout.composite_panel(
        ANTICIPATORY_ACTION,
        explainer,
        column,
        id="panel-activations",
        toolbar=layout.download_toolbar("activations"),
        note=note,
        beneath=(table, _export_meta("activations", MAP_ID, attribution, None)),
    )


def _commodity_panel(snapshot, events: list[Event] | None, data: PageData) -> html.Section:
    explainer = commodities.explainer()
    if isinstance(snapshot, LoadFailure):
        return layout.error_panel(
            REALISED_IMPACT,
            explainer,
            id="panel-commodities",
            source=snapshot.source,
            error=snapshot.error,
        )
    if snapshot is None or events is None:
        return layout.unavailable_panel(REALISED_IMPACT, explainer, id="panel-commodities")
    frame, metadata = snapshot
    try:
        figure = commodities.build_figure(frame, events)
    except Exception as exc:
        logger.exception("the commodity figure failed to build")
        return layout.error_panel(
            REALISED_IMPACT,
            explainer,
            id="panel-commodities",
            source=_source_label(commodities.SOURCE_ID),
            error=_describe(exc),
        )
    data.csv_keys.append("commodities")
    data.graph_keys.append("commodities")
    panel = layout.panel(
        REALISED_IMPACT,
        explainer,
        figure,
        metadata["retrieved_at"],
        id="panel-commodities",
        graph_id=PRICES_GRAPH_ID,
        toolbar=layout.download_toolbar("commodities"),
    )
    attribution = registry()[commodities.SOURCE_ID]["attribution"]
    panel.children.append(
        _export_meta("commodities", PRICES_GRAPH_ID, attribution, metadata["retrieved_at"])
    )
    return panel


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = result.stdout.strip()
    return sha if result.returncode == 0 and sha else None


def build_info() -> layout.BuildInfo:
    """The commit the page is built from (Render's, else git's) and the build time."""
    sha = os.environ.get("RENDER_GIT_COMMIT") or _git_sha() or "unknown"
    return layout.BuildInfo(sha=sha, built_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"))


def citation_text() -> str:
    return layout.citation_text(yaml.safe_load(CITATION_PATH.read_text(encoding="utf-8")))


def _stores(data: PageData) -> list:
    templates = {
        "light": TEMPLATES["light"],
        "dark": TEMPLATES["dark"],
        "map_border": {
            "light": TOKENS["data"]["map"]["border_light"],
            "dark": TOKENS["data"]["map"]["border_dark"],
        },
    }
    return [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="view-state", data=viewstate.default_state()),
        dcc.Store(id="theme-store", storage_type="local"),
        dcc.Store(id="event-select-store"),
        dcc.Store(id="plotly-templates", data=templates),
        dcc.Store(id="citation-text", data=citation_text()),
        dcc.Download(id="download"),
        html.Span(id="state-sink", hidden=True),
        html.Span(id="theme-sink", hidden=True),
    ]


def assemble(
    image_src: str = teleconnections.IMAGE_URL_PATH,
    topojson_url: str = "/assets/topojson/",
    build: layout.BuildInfo | None = None,
) -> tuple[html.Div, PageData]:
    """The page and the data it was built from, from whichever snapshots exist.

    ``image_src`` is the URL the app serves the teleconnection schematic
    from and ``topojson_url`` the folder it serves the map geometry from;
    the module passes ``app.get_asset_url`` for both so that they follow
    whatever path prefix the deployment sets.
    """
    data = PageData()
    index = _snapshot(enso_index.SOURCE_ID)
    events: list[Event] | None = None
    reading: str | None = None
    until = datetime.now(UTC).date()
    if isinstance(index, tuple):
        frame = index[0]
        try:
            events = enso_event_records(frame[frame["series_id"] == enso_index.PRIMARY_SERIES])
            reading = enso_index.latest_reading(frame, events)
            until = datetime.fromisoformat(max(frame["date"])).date()
        except Exception as exc:
            logger.exception("the index events failed to build")
            index = LoadFailure(_source_label(enso_index.SOURCE_ID), _describe(exc))
            events = None
            reading = None
        else:
            data.index = index
            data.events = events
    prices = _snapshot(commodities.SOURCE_ID)
    if isinstance(prices, tuple) and events is not None:
        data.prices = prices
    entries = _register()
    if not isinstance(entries, LoadFailure):
        data.entries = entries

    sources = [
        layout.SourceEntry(
            "panel-index",
            enso_index.explainer(),
            index[1]["retrieved_at"] if isinstance(index, tuple) else None,
        ),
        layout.SourceEntry(
            "panel-commodities",
            commodities.explainer(),
            prices[1]["retrieved_at"] if isinstance(prices, tuple) else None,
        ),
        layout.SourceEntry("panel-activations", activations_map.explainer()),
        layout.SourceEntry(
            "panel-teleconnections", teleconnections.explainer(), teleconnections.IMAGE_RETRIEVED_AT
        ),
    ]
    page = layout.page(
        *_stores(data),
        layout.skip_link(),
        layout.nav(),
        layout.opening(reading),
        main=(
            layout.about(),
            layout.time_controls(
                enso_index.RANGE_BUTTONS,
                layout.event_options(events or [], until) if events else [],
            ),
            _index_panel(index, events, data),
            _commodity_panel(prices, events, data),
            _activation_panel(entries, data, topojson_url),
            teleconnections.build_image_panel(image_src),
            layout.sources_section(sources),
            layout.footer(build),
        ),
    )
    return page, data


def build_page(image_src: str = teleconnections.IMAGE_URL_PATH) -> html.Div:
    """The page, from whichever snapshots exist at the time of the call."""
    return assemble(image_src=image_src)[0]


# ----------------------------------------------------------------- CSV


def _provenance_header(title: str, source_id: str, retrieved_at: str | None, href: str) -> list:
    entry = registry()[source_id]
    return [
        f"# {layout.TITLE}: {title}",
        f"# source: {entry['name']}, {entry['publisher']}, {entry['url']}",
        f"# licence: {entry['licence']} ({entry['licence_id']})",
        f"# attribution: {entry['attribution']}",
        f"# retrieved: {retrieved_at or 'not assessed'}",
        f"# concept DOI: {layout.CITATION_URL}",
        f"# permalink: {href}",
        f"# downloaded: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}",
    ]


def _csv_line(values: list) -> str:
    cells = []
    for value in values:
        text = "" if value is None else str(value)
        if any(ch in text for ch in ',"\n'):
            text = '"' + text.replace('"', '""') + '"'
        cells.append(text)
    return ",".join(cells)


def index_csv(data: PageData, href: str) -> str:
    frame, metadata = data.index
    header = _provenance_header(
        enso_index.explainer().title, enso_index.SOURCE_ID, metadata["retrieved_at"], href
    )
    rows = [_csv_line(["date", "season", "series", "value", "unit"])]
    for record in frame.sort_values(["series_id", "date"]).itertuples(index=False):
        rows.append(
            _csv_line(
                [
                    record.date,
                    season_label(record.date),
                    record.series_id,
                    record.value,
                    record.unit,
                ]
            )
        )
    return "\n".join(header + rows) + "\n"


def commodities_csv(data: PageData, href: str) -> str:
    frame, metadata = data.prices
    header = _provenance_header(
        commodities.explainer().title, commodities.SOURCE_ID, metadata["retrieved_at"], href
    )
    rows = [_csv_line(["date", "series", "label", "value", "unit", "index_2010_01"])]
    for series_id, label in commodities.DEFAULT_SERIES:
        series = frame[frame["series_id"] == series_id].sort_values("date")
        base = series.loc[series["date"] == commodities.BASE_MONTH, "value"]
        for record in series.itertuples(index=False):
            rebased = record.value / base.iloc[0] * commodities.BASE_VALUE if not base.empty else ""
            rows.append(
                _csv_line(
                    [
                        record.date,
                        series_id,
                        label,
                        record.value,
                        record.unit,
                        f"{rebased:.4f}" if rebased != "" else "",
                    ]
                )
            )
    return "\n".join(header + rows) + "\n"


def activations_csv(data: PageData, href: str) -> str:
    header = _provenance_header(
        activations_map.explainer().title, ACTIVATIONS_REGISTRY_ID, None, href
    )
    header[1] = f"# source: {REGISTER_SOURCE}, entries typed from the framework documents linked"
    columns = [
        "id",
        "iso3",
        "country",
        "framework",
        "status",
        "activation_date",
        "amount_usd",
        "people_targeted",
        "trigger",
        "forecast_source",
        "sector",
        "source_url",
        "wayback_url",
        "retrieved",
        "discrepancies",
    ]
    rows = [_csv_line(columns)]
    for entry in activations_map.rendered_entries(data.entries or []):
        discrepancies = "; ".join(
            f"{item['statement']}: {item['value']} ({item['source_url']})"
            for item in entry["discrepancies"]
        )
        rows.append(
            _csv_line(
                [
                    *(entry[column] for column in columns[:-1]),
                    discrepancies,
                ]
            )
        )
    return "\n".join(header + rows) + "\n"


CSV_BUILDERS = {"index": index_csv, "commodities": commodities_csv, "activations": activations_csv}


# ------------------------------------------------------------ callbacks


def register_callbacks(app: dash.Dash, data: PageData) -> None:
    """Wire the clientside callbacks and the CSV download for the panels present."""
    graphs = {
        "index": INDEX_GRAPH_ID,
        "commodities": PRICES_GRAPH_ID,
        "activations": MAP_ID,
    }
    time_series = [graphs[k] for k in ("index", "commodities") if k in data.graph_keys]

    inputs = [
        Input("url", "search"),
        Input("view-state", "data"),
        Input("event-select-store", "data"),
        Input("bands-toggle", "n_clicks"),
        Input("range-all", "n_clicks"),
        Input("range-30", "n_clicks"),
        Input("range-5", "n_clicks"),
    ]
    for graph_id in time_series:
        inputs.append(Input(graph_id, "relayoutData"))
        inputs.append(Input(graph_id, "restyleData"))
    app.clientside_callback(
        ClientsideFunction(namespace="atlas", function_name="syncState"),
        Output("view-state", "data"),
        Output("url", "search"),
        Output("bands-toggle", "aria-pressed"),
        *inputs,
        State("bands-toggle", "aria-pressed"),
    )
    app.clientside_callback(
        ClientsideFunction(namespace="atlas", function_name="applyState"),
        Output("state-sink", "children"),
        Input("view-state", "data"),
    )
    app.clientside_callback(
        ClientsideFunction(namespace="atlas", function_name="toggleTheme"),
        Output("theme-store", "data"),
        Input("theme-toggle", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    app.clientside_callback(
        ClientsideFunction(namespace="atlas", function_name="applyTheme"),
        Output("theme-sink", "children"),
        Input("theme-store", "data"),
        State("plotly-templates", "data"),
    )
    app.clientside_callback(
        ClientsideFunction(namespace="atlas", function_name="copyCitation"),
        Output("copy-status", "children"),
        Input("copy-citation", "n_clicks"),
        State("citation-text", "data"),
        prevent_initial_call=True,
    )
    for key in data.graph_keys:
        app.clientside_callback(
            ClientsideFunction(namespace="atlas", function_name="exportFigure"),
            Output(f"export-sink-{key}", "children"),
            Input(f"png-{key}", "n_clicks"),
            Input(f"svg-{key}", "n_clicks"),
            State(f"export-meta-{key}", "data"),
            prevent_initial_call=True,
        )
    if data.csv_keys:

        @app.callback(
            Output("download", "data"),
            [Input(f"csv-{key}", "n_clicks") for key in data.csv_keys],
            State("url", "href"),
            prevent_initial_call=True,
        )
        def download_csv(*args):
            triggered = ctx.triggered_id
            if not triggered:
                raise dash.exceptions.PreventUpdate
            key = str(triggered).removeprefix("csv-")
            href = args[-1] or ""
            text = CSV_BUILDERS[key](data, viewstate.permalink(href, href.partition("?")[2]))
            return dcc.send_string(text, f"{CSV_STEMS[key]}.csv")


class Atlas(dash.Dash):
    """The Dash app with a skeleton in place of the loading text."""

    def interpolate_index(self, **kwargs):
        kwargs["app_entry"] = SKELETON
        return super().interpolate_index(**kwargs)


# ------------------------------------------------------------- transport

# Fingerprinted static paths (Dash appends a modification stamp to assets
# and a version to component bundles) may be cached for a year; the page
# and its callbacks are not cached.
IMMUTABLE_PREFIXES: tuple[str, ...] = ("/assets/", "/_dash-component-suites/")
COMPRESSIBLE_TYPES: tuple[str, ...] = (
    "text/",
    "application/javascript",
    "application/json",
    "application/x-javascript",
    "image/svg+xml",
)
COMPRESS_MIN_BYTES = 1024
_COMPRESSED_CACHE: OrderedDict[str, tuple[str, bytes]] = OrderedDict()
_COMPRESSED_CACHE_SIZE = 32


def _compressed(key: str, etag: str, body: bytes) -> bytes:
    """``body`` gzipped, cached for fingerprinted responses by path and etag."""
    cached = _COMPRESSED_CACHE.get(key)
    if cached is not None and cached[0] == etag:
        _COMPRESSED_CACHE.move_to_end(key)
        return cached[1]
    packed = gzip.compress(body, compresslevel=6)
    _COMPRESSED_CACHE[key] = (etag, packed)
    while len(_COMPRESSED_CACHE) > _COMPRESSED_CACHE_SIZE:
        _COMPRESSED_CACHE.popitem(last=False)
    return packed


def compress_and_cache(response):
    """gzip text responses the client accepts, and mark fingerprinted files immutable.

    The production edge compresses as well; doing it here keeps the local
    server representative and the page weight the same wherever it runs.
    """
    path = request.path
    if path.startswith(IMMUTABLE_PREFIXES) and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    if (
        response.status_code != 200
        or "gzip" not in request.headers.get("Accept-Encoding", "")
        or response.headers.get("Content-Encoding")
        or not response.mimetype.startswith(COMPRESSIBLE_TYPES)
    ):
        return response
    # Static files stream from disk; reading them here is what allows the
    # compression, and the largest is the 1.1 MB topojson.
    response.direct_passthrough = False
    body = response.get_data()
    if len(body) < COMPRESS_MIN_BYTES:
        return response
    if path.startswith(IMMUTABLE_PREFIXES):
        key = f"{path}?{request.query_string.decode('ascii', 'ignore')}"
        etag = response.headers.get("ETag") or str(len(body))
        packed = _compressed(key, etag, body)
    else:
        packed = gzip.compress(body, compresslevel=6)
    response.set_data(packed)
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = str(len(packed))
    response.headers.add("Vary", "Accept-Encoding")
    return response


theme.register_templates()

app = Atlas(
    __name__,
    title=layout.TITLE,
    update_title=None,
    index_string=INDEX_STRING,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "color-scheme", "content": "light dark"},
    ],
)
_page, PAGE_DATA = assemble(
    image_src=app.get_asset_url(teleconnections.IMAGE_ASSET),
    topojson_url=app.get_asset_url("topojson/"),
    build=build_info(),
)
app.layout = _page
register_callbacks(app, PAGE_DATA)

server = app.server
server.after_request(compress_and_cache)
