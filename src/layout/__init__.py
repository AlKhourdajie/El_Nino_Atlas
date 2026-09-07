"""Layout builders for the El Niño Atlas dashboard.

``build_layout`` composes the served page from small, reusable builders so
that future layers can add panels without touching ``app.py``.
"""

import dash_bootstrap_components as dbc
from dash import html

from src import theme

TITLE = "El Niño Atlas"
SCOPE = (
    "A live tracker of the 2026-27 El Niño, following each signal from forecast, "
    "through anticipatory action, to realised socioeconomic impact."
)


def section(title: str, *children, id: str | None = None) -> html.Section:
    """A titled page section."""
    kwargs = {"id": id} if id else {}
    return html.Section([html.H2(title, className="h5 mt-4 mb-2"), *children], **kwargs)


def panel(title: str, *children, id: str | None = None) -> dbc.Card:
    """A bordered card holding one layer or one block of content."""
    kwargs = {"id": id} if id else {}
    return dbc.Card(
        [dbc.CardHeader(title), dbc.CardBody(list(children))],
        className="mb-3",
        **kwargs,
    )


def legend_item(state: str) -> html.Div:
    swatch_style = {
        "display": "inline-block",
        "width": "1.1rem",
        "height": "1.1rem",
        "marginRight": "0.5rem",
        "verticalAlign": "middle",
        "borderRadius": "2px",
        **theme.STATE_SWATCH_STYLE[state],
    }
    return html.Div(
        [
            html.Span(style=swatch_style, **{"aria-hidden": "true"}),
            html.Span(theme.STATE_LABELS[state]),
        ],
        className="me-4 d-inline-block",
        id=f"legend-{state}",
    )


def legend() -> html.Div:
    """The three-state legend used by every layer."""
    return html.Div(
        [legend_item(s) for s in ("alert", "no_alert", "not_assessed")],
        id="legend",
        role="list",
    )


def build_layout() -> dbc.Container:
    return dbc.Container(
        [
            html.Header(
                [
                    html.H1(TITLE, className="mt-4"),
                    html.P(SCOPE, className="lead", id="scope"),
                ]
            ),
            section(
                "Layers",
                panel(
                    "No active layers",
                    html.P(
                        "No layers are active yet. Layers appear here once their source "
                        "has an approved or conditional entry in the licence registry and "
                        "a working fetcher.",
                        className="mb-0",
                    ),
                    id="placeholder-panel",
                ),
                id="layers",
            ),
            section(
                "Legend",
                html.P(
                    "Every layer uses the same three states. "
                    "“Not assessed” means no assessment is available and is never "
                    "shown in the “No alert” colour.",
                    className="text-muted small",
                ),
                legend(),
                id="legend-section",
            ),
        ],
        fluid=False,
        className="pb-5",
    )
