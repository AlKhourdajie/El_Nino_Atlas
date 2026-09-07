"""Layout builders for the El Niño Atlas page.

``app.py`` assembles the page from these builders along the forecast,
action, impact spine. A panel is one section: the stage as its heading,
the figure in one column and the rendered explainer beside it. A panel
whose snapshot is missing keeps its explainer and shows a visible notice
in place of the figure. The page copy lives here; the copy rules are in
CLAUDE.md.
"""

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from src import theme
from src.layout.explainer import Explainer, render_explainer

TITLE = "El Niño Atlas"

OPENING = (
    "A very strong El Niño is under way in the tropical Pacific, on top of the warmest "
    "global background on record. This atlas follows what was forecast, what was done "
    "in anticipation, and what has happened."
)

ABOUT: tuple[str, ...] = (
    "The atlas follows one climate event, the 2026-27 El Niño, forward through three "
    "stages: forecast, anticipatory action and realised impact.",
    "Each panel belongs to one stage, draws on a source whose licence is recorded in the "
    "registry that ships with the code, and states what it does not show.",
    "Where the stages diverge, for example an activation whose trigger fired for a "
    "hazard that did not verify, the divergence is reported as a finding.",
)

UNAVAILABLE_NOTICE = "Data snapshot not yet available"
LICENCE_LINE = "Code: MIT licence. Data: licence stated with each panel."
CITATION_URL = "https://doi.org/10.5281/zenodo.22644790"


def section(title: str, *children, id: str | None = None) -> html.Section:
    """A titled page section."""
    kwargs = {"id": id} if id else {}
    return html.Section([html.H2(title, className="h5 mt-4 mb-2"), *children], **kwargs)


def opening() -> html.Header:
    """The page title and the opening line."""
    return html.Header(
        [html.H1(TITLE, className="mt-4"), html.P(OPENING, className="lead", id="opening")],
        id="header",
    )


def about() -> html.Section:
    """Three sentences on the event-resolved logic of the atlas."""
    return section("About", html.P(" ".join(ABOUT), className="mb-0"), id="about")


def graph(figure: go.Figure) -> dcc.Graph:
    """A panel figure."""
    return dcc.Graph(figure=figure)


def _panel_row(figure_column, explainer_column) -> dbc.Row:
    return dbc.Row([dbc.Col(figure_column, lg=7), dbc.Col(explainer_column, lg=5)])


def panel(
    stage: str,
    explainer: Explainer,
    figure: go.Figure,
    retrieved_at: str,
    *,
    id: str,
) -> html.Section:
    """One panel: the stage heading, the figure, and the explainer beside it."""
    row = _panel_row(graph(figure), render_explainer(explainer, retrieved_at))
    return section(stage, row, id=id)


def unavailable_panel(stage: str, explainer: Explainer, *, id: str) -> html.Section:
    """A panel whose snapshot is missing: the notice in place of the figure."""
    notice = html.P(
        UNAVAILABLE_NOTICE,
        className="p-3 mb-3",
        role="status",
        style={
            "border": f"1px dashed {theme.STATE_COLOURS['not_assessed']}",
            "borderRadius": "4px",
        },
    )
    return section(stage, _panel_row(notice, render_explainer(explainer)), id=id)


def container(id: str) -> html.Div:
    """An empty container another layer fills."""
    return html.Div(id=id)


def footer() -> html.Footer:
    return html.Footer(
        [
            html.P(LICENCE_LINE, className="mb-1"),
            html.P(["Cite: ", html.A(CITATION_URL, href=CITATION_URL)], className="mb-0"),
        ],
        id="footer",
        className="text-muted small mt-5 pt-3 border-top",
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


def page(*children) -> dbc.Container:
    """The served page, in the order given."""
    return dbc.Container(list(children), fluid=False, className="pb-5")
