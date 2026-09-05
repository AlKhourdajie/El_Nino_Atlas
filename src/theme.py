"""Colour tokens and Plotly templates for the El Niño Atlas.

Three-state convention
----------------------
Every layer classifies each unit as exactly one of ``alert``, ``no_alert``
or ``not_assessed``. The last is the absence of an assessment, not a
finding of "nothing happening", so it must never share a colour with
``no_alert``. ``STATE_COLOURS`` is the single place where those colours
live; ``tests/test_app_smoke.py`` asserts the two remain distinct.
"""

import plotly.graph_objects as go
import plotly.io as pio

# Semantic state tokens (shared by the dark and light templates).
STATE_COLOURS: dict[str, str] = {
    "alert": "#D1495B",  # warm red: an active alert or realised impact
    "no_alert": "#3A7CA5",  # cool blue: assessed, no alert
    "not_assessed": "#B8B2A7",  # warm neutral grey: no assessment available
}

STATE_LABELS: dict[str, str] = {
    "alert": "Alert",
    "no_alert": "No alert",
    "not_assessed": "Not assessed",
}

# ``not_assessed`` additionally gets a hatched, dashed-outline swatch so the
# distinction survives greyscale printing and colour-vision deficiency.
STATE_SWATCH_STYLE: dict[str, dict[str, str]] = {
    "alert": {"backgroundColor": STATE_COLOURS["alert"]},
    "no_alert": {"backgroundColor": STATE_COLOURS["no_alert"]},
    "not_assessed": {
        "backgroundColor": "transparent",
        "backgroundImage": (
            "repeating-linear-gradient(45deg, "
            f"{STATE_COLOURS['not_assessed']} 0 3px, transparent 3px 6px)"
        ),
        "border": f"1px dashed {STATE_COLOURS['not_assessed']}",
    },
}

# Base palettes.
DARK = {
    "bg": "#14171C",
    "panel": "#1E232B",
    "text": "#E6E1D8",
    "muted": "#9A948A",
    "grid": "#2C333D",
}
LIGHT = {
    "bg": "#FBFAF7",
    "panel": "#FFFFFF",
    "text": "#1F2328",
    "muted": "#6B665E",
    "grid": "#E4E0D8",
}

# Ordered categorical sequence for non-state series.
SERIES = ["#3A7CA5", "#D1495B", "#EDAE49", "#5E8C61", "#7B6D8D", "#8C4A2F"]

FONT_FAMILY = "Inter, 'Helvetica Neue', Arial, sans-serif"

TEMPLATE_DARK = "atlas_dark"
TEMPLATE_LIGHT = "atlas_light"


def _make_template(palette: dict[str, str]) -> go.layout.Template:
    axis = {
        "gridcolor": palette["grid"],
        "zerolinecolor": palette["grid"],
        "linecolor": palette["grid"],
        "tickcolor": palette["muted"],
        "title": {"font": {"color": palette["muted"]}},
    }
    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=palette["bg"],
            plot_bgcolor=palette["panel"],
            font={"family": FONT_FAMILY, "color": palette["text"], "size": 13},
            colorway=SERIES,
            xaxis=axis,
            yaxis=axis,
            legend={"bgcolor": "rgba(0,0,0,0)"},
            margin={"l": 48, "r": 24, "t": 48, "b": 40},
            hoverlabel={"font": {"family": FONT_FAMILY}},
        )
    )


def register_templates() -> None:
    """Register ``atlas_dark`` and ``atlas_light`` with Plotly (idempotent)."""
    pio.templates[TEMPLATE_DARK] = _make_template(DARK)
    pio.templates[TEMPLATE_LIGHT] = _make_template(LIGHT)
    pio.templates.default = TEMPLATE_LIGHT
