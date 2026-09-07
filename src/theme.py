"""Colour tokens and Plotly templates for the El Niño Atlas.

Every value here is read from ``src/plotly_template.py``, which
``scripts/build_tokens.py`` generates from ``design/tokens.json``, the
single source of truth for the design system. Edit the tokens, rebuild,
and this module follows.

Three-state convention
----------------------
Every layer classifies each unit as exactly one of ``alert``, ``no_alert``
or ``not_assessed``. The last is the absence of an assessment, not a
finding of "nothing happening", so it must never share a colour with
``no_alert``. ``STATE_COLOURS`` is the single place where those colours
live; ``tests/test_app_smoke.py`` asserts the two remain distinct. Each
state also has a mark style in ``STATE_MARKS`` (filled, outlined,
hatched), so the legend never relies on colour alone.

ENSO phase shading
------------------
Time-series panels shade El Niño and La Niña seasons behind their lines
as low-opacity bands in the Okabe-Ito orange and sky blue. A shaded
season is a classification of the index, not an alert, so
``PHASE_COLOURS`` stays distinct from every state token
(``tests/test_enso_index.py`` asserts this). The hues appear only as
tints; outlines and labels on the bands use the muted ink.
"""

import plotly.graph_objects as go
import plotly.io as pio

from src.plotly_template import TEMPLATES, TOKENS

_DATA = TOKENS["data"]
_SCHEME = TOKENS["scheme"]

# Semantic state tokens (shared by the dark and light templates).
STATE_COLOURS: dict[str, str] = dict(_DATA["state"])

STATE_LABELS: dict[str, str] = {
    "alert": "Alert",
    "no_alert": "No alert",
    "not_assessed": "Not assessed",
}

# The mark style paired with each state: a filled swatch, an outlined
# swatch and a hatched swatch with a dashed outline.
STATE_MARKS: dict[str, str] = dict(_DATA["state_mark"])

# Plotly marker symbols carrying the same distinction on maps.
STATE_MARKER_SYMBOLS: dict[str, str] = {
    "alert": "circle",
    "no_alert": "circle-open",
    "not_assessed": "square",
}

# Base palettes: the chrome of each scheme.
LIGHT: dict[str, str] = {
    "bg": _SCHEME["light"]["paper"],
    "panel": _SCHEME["light"]["surface"],
    "text": _SCHEME["light"]["ink"],
    "muted": _SCHEME["light"]["ink_muted"],
    "grid": _SCHEME["light"]["rule"],
}
DARK: dict[str, str] = {
    "bg": _SCHEME["dark"]["paper"],
    "panel": _SCHEME["dark"]["surface"],
    "text": _SCHEME["dark"]["ink"],
    "muted": _SCHEME["dark"]["ink_muted"],
    "grid": _SCHEME["dark"]["rule"],
}

# Ordered categorical sequence for non-state series.
SERIES: list[str] = list(_DATA["series"])

# ENSO phase shading: warm for El Niño, cool and lighter for La Niña.
PHASE_COLOURS: dict[str, str] = {
    "el_nino": _DATA["phase"]["el_nino"],
    "la_nina": _DATA["phase"]["la_nina"],
}
PHASE_NEUTRAL: str = _DATA["phase"]["neutral"]
PHASE_OPACITY: dict[str, float] = dict(_DATA["phase_opacity"])
PHASE_LABELS: dict[str, str] = {"el_nino": "El Niño season", "la_nina": "La Niña season"}
# A La Niña band carries a dotted outline so that the two phases differ
# in more than hue; an El Niño band has none.
PHASE_OUTLINE: dict[str, str | None] = dict(_DATA["phase_outline"])

# Reference lines, outlines and secondary series sit back from the primary line.
MUTED_LINE: str = _DATA["index"]["secondary"]
BAND_OUTLINE: str = LIGHT["muted"]
INDEX_LINE_COLOURS: dict[str, str] = {
    "primary": _DATA["index"]["primary"],
    "secondary": _DATA["index"]["secondary"],
}
THRESHOLD_LINE: dict[str, str | float] = {"color": _DATA["threshold"], "width": 1, "dash": "dot"}
MAP_BORDER: str = _DATA["map"]["border_light"]

# Shared figure layout for narrow screens: the figure fills its column
# with no fixed width, the legend runs horizontally below the plot, and
# the margins stay small. The height is fixed so the plot keeps its shape
# as the column narrows; Plotly expands the margins for tick labels and
# the legend as needed.
RESPONSIVE_LAYOUT: dict = {
    "autosize": True,
    "height": TOKENS["layout"]["figure_height_px"],
    "margin": {"l": 44, "r": 12, "t": 36, "b": 8},
    "legend": {"orientation": "h", "yanchor": "top", "y": -0.12, "xanchor": "left", "x": 0},
    # Dash redraws a figure from its stored copy after every interaction it
    # reports; a fixed uirevision makes plotly.js keep the reader's zoom and
    # legend choices across those redraws.
    "uirevision": "atlas",
}
UI_REVISION: str = RESPONSIVE_LAYOUT["uirevision"]
MAP_HEIGHT: int = TOKENS["layout"]["map_height_px"]

FONT_FAMILY: str = TEMPLATES["light"]["layout"]["font"]["family"]

TEMPLATE_DARK = "atlas_dark"
TEMPLATE_LIGHT = "atlas_light"


def rgba(hex_colour: str, alpha: float) -> str:
    """``#RRGGBB`` as a CSS ``rgba(...)`` string with ``alpha`` between 0 and 1."""
    value = hex_colour.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def template(scheme: str) -> go.layout.Template:
    """The Plotly template for ``scheme`` (``light`` or ``dark``)."""
    return go.layout.Template(layout=TEMPLATES[scheme]["layout"])


def register_templates() -> None:
    """Register ``atlas_dark`` and ``atlas_light`` with Plotly (idempotent)."""
    pio.templates[TEMPLATE_DARK] = template("dark")
    pio.templates[TEMPLATE_LIGHT] = template("light")
    pio.templates.default = TEMPLATE_LIGHT
