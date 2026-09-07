"""Draft teleconnection schematic layer: El Niño tendencies, December to February.

Provenance
----------
publisher:      NOAA Climate Prediction Center (NCEP/NWS)
dataset:        "Warm Episode Relationships, December - February", the El
                Niño panel of the typical-impacts schematic (warm.gif) on
                the El Niño temperature and precipitation patterns page
url:            https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml
image:          https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/impacts/warm.gif
licence:        US Government work, public domain
redistribution: yes
attribution:    "Schematic after NOAA Climate Prediction Center, El Niño
                temperature and precipitation patterns"
cadence:        static; the page was last modified on 19 December 2005 and
                the image file on 7 November 2012
latency:        none, the schematic is fixed
registry id:    none yet; src/sources.yaml has no entry for the schematic
                (noaa_oni covers a different dataset)

Role in the atlas
-----------------
Context layer beneath the impact layers: where El Niño has tended to
shift rainfall and temperature in past December to February seasons.
The polygons are approximate outlines drawn by hand from the schematic,
carried in a GeoJSON FeatureCollection in which every feature has the
properties ``signal``, ``season`` ("DJF"), ``basis`` ("NOAA CPC
schematic, DJF") and ``note``. Nothing is computed from data.

The layer draws what the collection says and raises on anything it
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

import plotly.graph_objects as go

from src.layout.explainer import Explainer

SEASON = "DJF"
BASIS = "NOAA CPC schematic, DJF"

SOURCE_NAME = "NOAA Climate Prediction Center"
SOURCE_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml"
IMAGE_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/impacts/warm.gif"
LICENCE_LABEL = "US Government work, public domain"

ROOT = Path(__file__).resolve().parent.parent.parent
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
        title="El Niño teleconnections, December to February (draft)",
        what=(
            "Where El Niño has tended to shift rainfall and temperature in past December to "
            "February seasons. Each shaded area marks a tendency towards wetter, drier, warmer "
            "or cooler conditions than normal, or a combination of two, as drawn on the "
            "National Oceanic and Atmospheric Administration (NOAA) Climate Prediction Center "
            "schematic of typical El Niño impacts."
        ),
        how=(
            "Schematic after the NOAA Climate Prediction Center, whose page states that El Niño "
            "episodes are 'associated with increased rainfall across the east-central and "
            "eastern Pacific and with drier than normal conditions over northern Australia, "
            "Indonesia and the Philippines', and lists further regional tendencies for "
            "December to February. The outlines here were drawn by hand from the December to "
            "February panel of that schematic and are approximate. The source line below "
            "links to the page."
        ),
        why=(
            "The impacts the other layers track begin with shifts in seasonal rainfall and "
            "temperature. The schematic shows where those shifts have tended to occur in past "
            "El Niño events, so the forecast, anticipatory action and realised impact layers "
            "can be read against the places where an effect was expected, and against the "
            "places where none was."
        ),
        not_shown=(
            "The shading shows tendencies across past events. Single events differ from the "
            "tendency, and a region can see the opposite sign in a given season. This draft "
            "carries no statistical test, no magnitude and no measure of confidence, and it "
            "will be replaced by computed composites. Unshaded areas carry no drawn tendency, "
            "and the schematic makes no claim about them."
        ),
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        licence_label=LICENCE_LABEL,
        captions=(
            "Draft schematic drawn by hand after the NOAA Climate Prediction Center panel for "
            "December to February; the outlines are approximate and carry no statistical test.",
        ),
    )
