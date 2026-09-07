"""Tests for the layout package: captions and page builders."""

from pathlib import Path

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from src import layout, theme
from src.layout import captions
from src.layout.explainer import Explainer
from tests.support import component_ids, walk

DESIGN = Path(__file__).resolve().parent.parent / "docs" / "DESIGN.md"
EXPLAINER = Explainer(
    title="Example panel",
    what="What.",
    how="How.",
    why="Why.",
    not_shown="Not shown.",
    source_name="Example source",
    source_url="https://example.org/source",
    licence_label="CC BY 4.0",
)


def design_blockquotes(heading: str) -> list[str]:
    """The blockquotes of one section of docs/DESIGN.md, each joined into one line."""
    text = DESIGN.read_text(encoding="utf-8")
    section = text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]
    quotes: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        if line.startswith("> "):
            current.append(line[2:].strip())
        elif current:
            quotes.append(" ".join(current))
            current = []
    if current:
        quotes.append(" ".join(current))
    return quotes


def design_captions() -> list[str]:
    return design_blockquotes("## Caption guardrails")


def test_captions_are_verbatim_from_the_design_notes():
    assert list(captions.CAPTIONS) == design_captions()
    assert captions.CAPTIONS == (
        captions.GROWTH,
        captions.PRICE_TRANSMISSION,
        captions.TEMPERATURE_CONTRIBUTION,
    )


READING = (
    "Latest three-month season (June to August 2026): RONI +1.36 °C, ONI +1.80 °C, provisional."
)


def test_opening_line_is_verbatim():
    assert layout.OPENING == (
        "An El Niño is under way in the tropical Pacific and is forecast to become very strong "
        "by late 2026, on top of the warmest global background on record. This atlas follows "
        "what was forecast, what was done in anticipation, and what has happened."
    )
    assert design_blockquotes("## Opening line") == [layout.OPENING]
    header = layout.opening()
    (lead,) = [c for c in walk(header) if getattr(c, "id", None) == "opening"]
    assert lead.children == layout.OPENING
    assert component_ids(header) == ["header", "opening"]


def test_opening_carries_the_reading_line_directly_beneath_the_lead():
    header = layout.opening(READING)
    assert component_ids(header) == ["header", "opening", "latest-reading"]
    (line,) = [c for c in walk(header) if getattr(c, "id", None) == "latest-reading"]
    assert isinstance(line, html.P) and line.children == READING
    assert "latest-reading" not in component_ids(layout.opening(None))


def test_about_block_has_three_sentences():
    assert len(layout.ABOUT) == 3
    assert all(sentence.endswith(".") and sentence.count(". ") == 0 for sentence in layout.ABOUT)
    text = " ".join(layout.ABOUT)
    for phrase in (
        "one climate event",
        "forecast, anticipatory action and realised impact",
        "finding",
    ):
        assert phrase in text
    assert layout.about().id == "about"


def test_panel_holds_stage_graph_and_explainer():
    section = layout.panel("Forecast", EXPLAINER, go.Figure(), "2026-09-05T17:00:00Z", id="p")
    assert section.id == "p"
    assert next(c for c in walk(section) if isinstance(c, html.H2)).children == "Forecast"
    assert len([c for c in walk(section) if isinstance(c, dcc.Graph)]) == 1
    rendered = str(section)
    assert "Example panel" in rendered
    assert "retrieved 2026-09-05T17:00:00Z" in rendered
    assert layout.UNAVAILABLE_NOTICE not in rendered


def test_unavailable_panel_shows_notice_and_explainer():
    section = layout.unavailable_panel("Forecast", EXPLAINER, id="p")
    assert not [c for c in walk(section) if isinstance(c, dcc.Graph)]
    (notice,) = [c for c in walk(section) if getattr(c, "role", None) == "status"]
    assert notice.children == layout.UNAVAILABLE_NOTICE
    assert theme.STATE_COLOURS["not_assessed"] in notice.style["border"]
    rendered = str(section)
    assert "Example panel" in rendered
    assert "retrieved" not in rendered


def test_composite_panel_holds_the_callers_column_beside_the_explainer():
    column = [html.Div(id="first"), html.Div(id="second")]
    section = layout.composite_panel("Anticipatory action", EXPLAINER, column, id="p")
    assert section.id == "p"
    assert (
        next(c for c in walk(section) if isinstance(c, html.H2)).children == "Anticipatory action"
    )
    ids = component_ids(section)
    assert ids.index("first") < ids.index("second")
    rendered = str(section)
    assert "Example panel" in rendered
    assert "retrieved" not in rendered
    stamped = layout.composite_panel("Stage", EXPLAINER, column, id="q", retrieved_at="2026-09-07")
    assert "retrieved 2026-09-07" in str(stamped)


def test_composite_panel_places_beneath_components_after_the_row_at_full_width():
    table = html.Table(id="wide")
    section = layout.composite_panel(
        "Stage", EXPLAINER, [html.Div(id="first")], id="p", beneath=(table,)
    )
    (row,) = [c for c in section.children if isinstance(c, dbc.Row)]
    assert "first" in component_ids(row) and "wide" not in component_ids(row)
    assert section.children[-1] is table


def test_container_is_empty_with_its_id():
    empty = layout.container("panel-activations")
    assert empty.id == "panel-activations" and not empty.children


def test_footer_states_licences_and_citation():
    footer = layout.footer()
    assert footer.id == "footer"
    rendered = str(footer)
    assert "Code: MIT licence. Data: licence stated with each panel." in rendered
    assert "Cite: " in rendered
    (link,) = [c for c in walk(footer) if isinstance(c, html.A)]
    assert link.href == link.children == "https://doi.org/10.5281/zenodo.22644790"


def test_page_copy_follows_the_rules():
    for text in (layout.OPENING, *layout.ABOUT, layout.LICENCE_LINE):
        assert "—" not in text


def test_graph_config_suits_touch_screens():
    assert layout.GRAPH_CONFIG == {
        "responsive": True,
        "displayModeBar": False,
        "scrollZoom": False,
    }
    assert layout.graph(go.Figure()).config == layout.GRAPH_CONFIG
    assert getattr(layout.graph(go.Figure()), "id", None) is None
    assert getattr(layout.graph(go.Figure()), "style", None) is None
    named = layout.graph(go.Figure(), id="activations-map", height=420)
    assert named.id == "activations-map" and named.config == layout.GRAPH_CONFIG
    assert named.style == {"height": "420px"}


def test_every_column_fills_a_narrow_screen():
    sections = (
        layout.panel("Forecast", EXPLAINER, go.Figure(), "2026-09-05T17:00:00Z", id="p"),
        layout.unavailable_panel("Forecast", EXPLAINER, id="q"),
        layout.composite_panel("Stage", EXPLAINER, [layout.legend(), html.Div()], id="r"),
    )
    for section in sections:
        columns = [c for c in walk(section) if isinstance(c, dbc.Col)]
        assert columns and all(column.xs == 12 for column in columns)


def test_page_container_is_fluid():
    assert layout.page().fluid is True
