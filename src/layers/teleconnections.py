"""Draft teleconnection schematic layer: El Niño tendencies, December to February.

Provenance
----------
publisher:      NOAA Climate Prediction Center (NCEP/NWS)
dataset:        "Warm Episode Relationships", the typical-impacts schematic
                (warm.gif) on the El Niño temperature and precipitation
                patterns page: December to February in the upper panel,
                June to August in the lower panel
url:            https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml
image:          https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/impacts/warm.gif
asset:          assets/teleconnections/noaa_cpc_elnino_impacts.jpg,
                byte-identical to the retrieved image (a JPEG despite the
                .gif name), retrieved 2026-09-07T14:36:16Z; sha256 and the
                full record in assets/teleconnections/PROVENANCE.md
licence:        US Government work, public domain (LicenseRef-US-PD)
redistribution: yes
attribution:    "Source: NOAA Climate Prediction Center, typical El Niño
                temperature and precipitation patterns"
cadence:        static; the page was last modified on 19 December 2005 and
                the image file on 7 November 2012
latency:        none, the schematic is fixed
registry id:    noaa_cpc_enso_impacts_schematic (src/sources.yaml; status
                approved, redistribution yes)

Role in the atlas
-----------------
Context layer beneath the impact layers: where El Niño has tended to
shift rainfall and temperature in past December to February seasons.

The page shows the schematic image itself, through ``build_image_panel``,
because it is a US government work and the most faithful form of the
draft. A set of approximate polygons drawn by hand from the schematic
exists as a draft mask in the main clone's private ``local/candidates/``
folder (a GeoJSON FeatureCollection in which every feature has the
properties ``signal``, ``season`` ("DJF"), ``basis`` ("NOAA CPC
schematic, DJF") and ``note``). That mask is not yet rendered.
``build_figure`` and ``GRAPH_CONFIG`` stay in place to draw it once it is
approved. Nothing is computed from data.

``build_figure`` draws what the collection says and raises on anything it
cannot draw faithfully: an unknown signal, a missing note, a geometry
with holes or a coordinate off the globe. It classifies areas by
tendency rather than by the three alert states of ``src.theme``, and its
colours are kept distinct from all three state tokens so a tendency can
never be read as an alert.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html

from src.layout import section
from src.layout.explainer import Explainer, render_explainer

SOURCE_ID = "noaa_cpc_enso_impacts_schematic"
SEASON = "DJF"
BASIS = "NOAA CPC schematic, DJF"

SOURCE_NAME = "NOAA Climate Prediction Center"
SOURCE_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml"
IMAGE_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/impacts/warm.gif"
LICENCE_LABEL = "US Government work, public domain"
# The one link the how-block carries, rendered by ``render_explainer``.
SOURCE_LINK_LABEL = (
    "Climate Prediction Center page on El Niño temperature and precipitation patterns"
)

# The schematic as served on the page: Dash serves ``assets/`` at ``/assets/``.
IMAGE_ASSET = "teleconnections/noaa_cpc_elnino_impacts.jpg"
IMAGE_URL_PATH = f"/assets/{IMAGE_ASSET}"
IMAGE_SHA256 = "849985b5dfc4c951ea7206da135c16d7a4c313addf7f77b071d54c12104d26c5"
IMAGE_RETRIEVED_AT = "2026-09-07T14:36:16Z"
IMAGE_ALT = (
    "National Oceanic and Atmospheric Administration Climate Prediction Center schematic of "
    "typical El Niño impacts, December to February above and June to August below: shaded "
    "areas where past El Niño events tended to bring wetter, drier, warmer or cooler "
    "conditions."
)
IMAGE_STYLE: dict[str, str] = {
    "width": "100%",
    "maxWidth": "100%",
    "height": "auto",
    "display": "block",
}
PANEL_TITLE = "Where El Niño usually matters: draft schematic"
# The id of the empty container ``app.build_page`` reserves for this layer.
PANEL_ID = "panel-teleconnections"

ROOT = Path(__file__).resolve().parent.parent.parent
IMAGE_FILE = ROOT / "assets" / "teleconnections" / "noaa_cpc_elnino_impacts.jpg"
CURATED_PATH = (
    ROOT / "data" / "curated" / "teleconnections" / "teleconnections_djf_schematic.geojson"
)

TITLE = "Draft: where El Niño has tended to shift rainfall and temperature, December to February"
LEGEND_TITLE = (
    "Tendency in past El Niño December to February seasons, "
    "after the Climate Prediction Center schematic"
)

# Signal classes in drawing order: single tendencies first, combined ones
# on top, as on the schematic.
SIGNALS: tuple[str, ...] = (
    "wetter",
    "drier",
    "warmer",
    "cooler",
    "warmer_and_drier",
    "cooler_and_wetter",
    "warmer_and_wetter",
)
SIGNAL_LABELS: dict[str, str] = {
    "wetter": "Wetter",
    "drier": "Drier",
    "warmer": "Warmer",
    "cooler": "Cooler",
    "warmer_and_drier": "Warmer and drier",
    "cooler_and_wetter": "Cooler and wetter",
    "warmer_and_wetter": "Warmer and wetter",
}
# None of these equals a token in src.theme.STATE_COLOURS; a test asserts it.
SIGNAL_COLOURS: dict[str, str] = {
    "wetter": "#1B9E77",
    "drier": "#8C6D46",
    "warmer": "#D95F02",
    "cooler": "#6A51A3",
    "warmer_and_drier": "#E6AB02",
    "cooler_and_wetter": "#5B5BD6",
    "warmer_and_wetter": "#E7298A",
}
FILL_OPACITY = 0.55

# Scroll zoom is a Plotly config option rather than a layout property, so
# the app passes this to ``dcc.Graph(config=...)`` beside the figure.
GRAPH_CONFIG: dict[str, bool] = {"scrollZoom": False, "displayModeBar": False}

GEOMETRY_TYPES: tuple[str, ...] = ("Polygon", "MultiPolygon")

Position = tuple[float, float]
Ring = tuple[Position, ...]


@dataclass(frozen=True)
class SchematicFeature:
    """One validated feature: its signal class, its note and its exterior rings."""

    signal: str
    note: str
    rings: tuple[Ring, ...]


def _fail(label: str, message: str) -> ValueError:
    return ValueError(f"{label}: {message}")


def _ring(raw: Any, label: str) -> Ring:
    if not isinstance(raw, list) or len(raw) < 4:
        raise _fail(label, "a ring needs at least four positions")
    points: list[Position] = []
    for position in raw:
        if not isinstance(position, list | tuple) or len(position) < 2:
            raise _fail(label, f"bad position {position!r}")
        lon, lat = position[0], position[1]
        for value in (lon, lat):
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise _fail(label, f"bad position {position!r}")
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise _fail(label, f"position {position!r} is off the globe")
        points.append((float(lon), float(lat)))
    if points[0] != points[-1]:
        raise _fail(label, "ring is not closed")
    return tuple(points)


def _rings(geometry: Any, label: str) -> tuple[Ring, ...]:
    """Exterior rings of a Polygon or MultiPolygon; holes are refused."""
    if not isinstance(geometry, dict) or geometry.get("type") not in GEOMETRY_TYPES:
        raise _fail(label, f"geometry must be one of {GEOMETRY_TYPES}")
    polygons = geometry.get("coordinates")
    if geometry["type"] == "Polygon":
        polygons = [polygons]
    if not isinstance(polygons, list) or not polygons:
        raise _fail(label, "geometry has no coordinates")
    rings: list[Ring] = []
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise _fail(label, "polygon has no rings")
        if len(polygon) > 1:
            raise _fail(label, "polygons with holes are not supported")
        rings.append(_ring(polygon[0], label))
    return tuple(rings)


def parse_features(geojson: Any) -> list[SchematicFeature]:
    """Validate a FeatureCollection and return its features in file order.

    Raises ``ValueError`` naming the first fault. Nothing is repaired,
    coerced or dropped; the input is left unchanged.
    """
    if not isinstance(geojson, dict) or geojson.get("type") != "FeatureCollection":
        raise ValueError("expected a GeoJSON FeatureCollection")
    features = geojson.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("the collection has no features")
    parsed: list[SchematicFeature] = []
    for index, feature in enumerate(features):
        label = f"features[{index}]"
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise _fail(label, "expected a Feature")
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise _fail(label, "properties must be a mapping")
        signal = properties.get("signal")
        if signal not in SIGNALS:
            raise _fail(label, f"unknown signal {signal!r}; expected one of {SIGNALS}")
        if properties.get("season") != SEASON:
            raise _fail(label, f"season must be {SEASON!r}, got {properties.get('season')!r}")
        if properties.get("basis") != BASIS:
            raise _fail(label, f"basis must be {BASIS!r}, got {properties.get('basis')!r}")
        note = properties.get("note")
        if not isinstance(note, str) or not note.strip():
            raise _fail(label, "note must be a non-empty string")
        parsed.append(SchematicFeature(signal, note, _rings(feature.get("geometry"), label)))
    return parsed


def load_geojson(path: Path = CURATED_PATH) -> dict:
    """Read and validate a schematic FeatureCollection from ``path``."""
    with Path(path).open(encoding="utf-8") as fh:
        geojson = json.load(fh)
    parse_features(geojson)
    return geojson


def _rgba(hex_colour: str, alpha: float) -> str:
    value = hex_colour.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def _trace(signal: str, features: list[SchematicFeature]) -> go.Scattergeo:
    """One filled trace per signal class; rings are separated by gaps."""
    lon: list[float | None] = []
    lat: list[float | None] = []
    text: list[str] = []
    for feature in features:
        for ring in feature.rings:
            lon.extend(point[0] for point in ring)
            lat.extend(point[1] for point in ring)
            text.extend([feature.note] * len(ring))
            lon.append(None)
            lat.append(None)
            text.append("")
    lon.pop()
    lat.pop()
    text.pop()
    colour = SIGNAL_COLOURS[signal]
    return go.Scattergeo(
        lon=lon,
        lat=lat,
        text=text,
        mode="lines",
        fill="toself",
        fillcolor=_rgba(colour, FILL_OPACITY),
        line={"color": colour, "width": 1},
        name=SIGNAL_LABELS[signal],
        legendgroup=signal,
        hoverinfo="text",
        connectgaps=False,
    )


def build_figure(geojson: dict) -> go.Figure:
    """The draft schematic on Plotly's built-in geography, one fill per signal class."""
    features = parse_features(geojson)
    fig = go.Figure()
    for signal in SIGNALS:
        chosen = [feature for feature in features if feature.signal == signal]
        if chosen:
            fig.add_trace(_trace(signal, chosen))
    fig.update_layout(
        title={"text": TITLE},
        dragmode=False,
        showlegend=True,
        legend={"title": {"text": LEGEND_TITLE}, "orientation": "h", "y": -0.02},
        margin={"l": 8, "r": 8, "t": 56, "b": 8},
        geo={
            "projection": {"type": "natural earth", "rotation": {"lon": 160}},
            "showland": True,
            "landcolor": "#E9E4DB",
            "showocean": True,
            "oceancolor": "#D7E3EC",
            "showcoastlines": True,
            "coastlinecolor": "#8A867E",
            "coastlinewidth": 0.6,
            "showcountries": False,
            "showlakes": False,
            "showframe": False,
            "lataxis": {"range": [-60, 78]},
            "bgcolor": "rgba(0,0,0,0)",
        },
    )
    return fig


def explainer() -> Explainer:
    return Explainer(
        title=PANEL_TITLE,
        what=(
            "Where El Niño has tended to shift rainfall and temperature in past seasons, on the "
            "schematic published by the National Oceanic and Atmospheric Administration (NOAA) "
            "Climate Prediction Center and shown here as retrieved, with two panels: December "
            "to February above and June to August below. Each shaded area marks a tendency "
            "towards wetter, drier, warmer or cooler conditions than normal, or a combination "
            "of two."
        ),
        how=(
            "Schematic by the NOAA Climate Prediction Center, whose page states that El Niño "
            "episodes are 'associated with increased rainfall across the east-central and "
            "eastern Pacific and with drier than normal conditions over northern Australia, "
            "Indonesia and the Philippines', and lists further regional tendencies for "
            "December to February. The image is shown as retrieved, without cropping or "
            f"redrawing, from the [{SOURCE_LINK_LABEL}]({SOURCE_URL})."
        ),
        why=(
            "The impacts the other layers track begin with shifts in seasonal rainfall and "
            "temperature, so a map of where those shifts have tended to occur shows where an "
            "El Niño signal is expected. It sets the basis on which later realised-impact "
            "layers are admitted to the atlas, and it lets a reader set realised impacts "
            "against the places where an effect was expected and the places outside them."
        ),
        not_shown=(
            "The schematic summarises tendencies across past events, and single events differ "
            "from it. CPC's page text lists Central America as drier in December to February "
            "while the image draws no such area, and the image shows a wet area over the "
            "south-western United States that the text omits. The panel is a draft and will "
            "be replaced by composites computed from public-domain gridded data with "
            "significance tests."
        ),
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        licence_label=LICENCE_LABEL,
        captions=(
            "Draft layer: the schematic is shown as published by the NOAA Climate Prediction "
            "Center, with the December to February panel above the June to August panel. The "
            "shaded areas are the publisher's own and carry no statistical test.",
        ),
    )


def build_image_panel(
    image_src: str = IMAGE_URL_PATH, retrieved_at: str | None = IMAGE_RETRIEVED_AT
) -> html.Section:
    """The draft layer as shown on the page: the schematic image beside its explainer.

    One section in the page's panel shape: the heading carries the word
    draft, the image fills its column and keeps its aspect ratio, and the
    explainer sits beside it on wide screens and below it on narrow ones.
    ``image_src`` is the URL the app serves the asset from; the default is
    Dash's standard assets path, and ``app.get_asset_url(IMAGE_ASSET)``
    gives the same file under any other prefix.
    """
    image = html.Img(
        src=image_src,
        alt=IMAGE_ALT,
        style=IMAGE_STYLE,
        className="mb-3",
        id="teleconnections-image",
    )
    row = dbc.Row(
        [
            dbc.Col(image, xs=12, lg=7),
            dbc.Col(render_explainer(explainer(), retrieved_at), xs=12, lg=5),
        ]
    )
    return section(PANEL_TITLE, row, id=PANEL_ID)
