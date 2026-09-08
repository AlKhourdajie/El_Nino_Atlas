"""Tests for the layout package: captions, page builders, cards and the footer."""

from datetime import date
from pathlib import Path

import plotly.graph_objects as go
import yaml
from dash import dcc, html

from src import layout, theme
from src.enso_events import Event
from src.layers import enso_index
from src.layout import captions
from src.layout.explainer import Explainer
from tests.support import component_ids, walk

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "DESIGN.md"
README = ROOT / "README.md"
CITATION = ROOT / "CITATION.cff"
EXPLAINER = Explainer(
    title="Example panel",
    what="What. More.",
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


def line_text(paragraph) -> str:
    """The text of a page line, each child component flattened to its text."""
    children = paragraph.children
    if isinstance(children, str):
        return children
    return "".join(line_text(c) if hasattr(c, "children") else c for c in children)


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
    assert component_ids(header) == ["header", "opening", "scope"]


def test_hero_has_no_maintainer_line_and_names_no_affiliation():
    title, lead, scope = layout.opening().children
    assert isinstance(title, html.H1) and title.children == layout.TITLE
    assert lead.id == "opening"
    assert scope.id == "scope" and scope.children == layout.SCOPE
    assert "Maintained by" not in str(layout.opening(READING))
    assert "Imperial" not in str(layout.opening(READING)) + str(layout.footer())
    assert not hasattr(layout, "AFFILIATION")


def test_opening_carries_the_reading_line_directly_beneath_the_lead():
    header = layout.opening(READING)
    assert component_ids(header) == ["header", "opening", "latest-reading", "scope"]
    (line,) = [c for c in walk(header) if getattr(c, "id", None) == "latest-reading"]
    assert isinstance(line, html.P) and line.children == READING
    assert "latest-reading" not in component_ids(layout.opening(None))


def readme_paragraph(heading: str) -> str:
    """The first paragraph under ``heading`` in README.md."""
    text = README.read_text(encoding="utf-8")
    section = text.split(f"\n{heading}\n", 1)[1]
    return next(p.strip() for p in section.split("\n\n") if p.strip())


def test_scope_line_is_a_readme_sentence():
    text = README.read_text(encoding="utf-8")
    assert layout.SCOPE in text
    assert layout.SCOPE.endswith(".") and layout.SCOPE.count(". ") == 0


def test_about_block_opens_the_readme_case_for_the_atlas():
    assert layout.ABOUT == (
        "Hazard catalogues, forecast dashboards and response dashboards each cover one stage "
        "of an event and keep their records apart.",
        "The atlas takes the 2026-27 El Niño as its unit and organises the three records "
        "around it, so that every entry is tied to this event with a stated basis and the "
        "stages sit on one page.",
    )
    assert all(sentence.endswith(".") and sentence.count(". ") == 0 for sentence in layout.ABOUT)
    text = " ".join(layout.ABOUT)
    assert readme_paragraph("## Why an event-resolved atlas").startswith(text + " ")
    assert layout.about().id == "about"


def test_readme_order_paragraph_states_the_page_order():
    assert readme_paragraph("## How to read the atlas") == (
        "**Order.** The page opens with the state of El Niño in the Pacific, followed by the "
        "realised impacts that public data can measure, the anticipatory action taken on "
        "forecasts, and a draft map of where an effect is expected. Each panel carries its "
        "stage label."
    )


def test_readme_names_the_maintainer_under_the_live_site_line():
    text = README.read_text(encoding="utf-8")
    assert (
        "\nLive site: https://el-nino-atlas.onrender.com\n\n"
        "Maintained by [Alaa Al Khourdajie](https://sites.google.com/site/akhourdajie/).\n\n"
    ) in text
    assert "Imperial" not in text


def test_nav_anchors_follow_the_page_order_and_carry_the_theme_toggle():
    nav = layout.nav()
    assert nav.id == "site-nav"
    links = [(a.children, a.href) for a in walk(nav) if isinstance(a, html.A)]
    assert links[0] == (layout.TITLE, "#header")
    assert links[1:] == list(layout.NAV_ITEMS)
    assert [href for _, href in layout.NAV_ITEMS] == [
        "#panel-index",
        "#panel-commodities",
        "#panel-activations",
        "#sources",
        "#cite",
    ]
    (toggle,) = [c for c in walk(nav) if isinstance(c, html.Button)]
    assert toggle.id == "theme-toggle"
    assert layout.skip_link().href == "#main"


def test_card_has_the_fixed_header_grammar():
    section = layout.panel(
        "Forecast", EXPLAINER, go.Figure(), "2026-09-05T17:00:00Z", id="p", graph_id="g"
    )
    assert section.id == "p"
    header = section.children[0]
    assert isinstance(header, html.Header)
    stage, title, lede, source, method = header.children
    assert stage.children == "Forecast" and stage.className == "card__stage"
    assert isinstance(title, html.H2) and title.children == "Example panel"
    assert title.id == "p-title"
    assert lede.children == "What."
    assert "retrieved 2026-09-05T17:00:00Z" in str(source)
    assert isinstance(method, html.Details)
    assert method.children[0].children == "Source and method"
    (graph,) = [c for c in walk(section) if isinstance(c, dcc.Graph)]
    assert graph.id == "g"
    (figure,) = [c for c in walk(section) if isinstance(c, html.Figure)]
    (caption,) = [c for c in walk(figure) if isinstance(c, html.Figcaption)]
    assert caption.children == "What." and "visually-hidden" in caption.className
    rendered = str(section)
    assert "Example panel" in rendered
    assert layout.UNAVAILABLE_NOTICE not in rendered
    body = [c for c in walk(section) if getattr(c, "className", None) == "card__body"]
    assert len(body) == 1 and "More." in str(body[0])


def test_unavailable_panel_shows_notice_and_explainer():
    section = layout.unavailable_panel("Forecast", EXPLAINER, id="p")
    assert not [c for c in walk(section) if isinstance(c, dcc.Graph)]
    (notice,) = [c for c in walk(section) if getattr(c, "role", None) == "status"]
    assert notice.children == layout.UNAVAILABLE_NOTICE
    rendered = str(section)
    assert "Example panel" in rendered
    assert "retrieved" not in rendered


def test_error_panel_names_the_source_and_the_error():
    section = layout.error_panel(
        "Forecast", EXPLAINER, id="p", source="Example source (x)", error="ValueError: bad"
    )
    (banner,) = [c for c in walk(section) if getattr(c, "role", None) == "alert"]
    rendered = str(banner)
    assert layout.ERROR_PREFIX in rendered
    assert "Example source (x)" in rendered and "ValueError: bad" in rendered
    assert not [c for c in walk(section) if isinstance(c, dcc.Graph)]
    assert layout.UNAVAILABLE_NOTICE not in str(section)


def test_composite_panel_holds_the_callers_column_and_beneath_components():
    column = html.Div([html.Div(id="first"), html.Div(id="second")])
    table = html.Table(id="wide")
    section = layout.composite_panel(
        "Anticipatory action", EXPLAINER, column, id="p", beneath=(table,)
    )
    assert section.id == "p"
    assert section.children[0].children[0].children == "Anticipatory action"
    ids = component_ids(section)
    assert ids.index("first") < ids.index("second") < ids.index("wide")
    assert section.children[-1] is table
    rendered = str(section)
    assert "Example panel" in rendered
    assert "retrieved" not in rendered
    stamped = layout.composite_panel("Stage", EXPLAINER, column, id="q", retrieved_at="2026-09-07")
    assert "retrieved 2026-09-07" in str(stamped)


def test_container_is_empty_with_its_id():
    empty = layout.container("panel-activations")
    assert empty.id == "panel-activations" and not empty.children


def footer_lines(footer) -> list[str]:
    return [line_text(p) for p in footer.children if isinstance(p, html.P)]


def test_footer_states_maintainer_licences_and_citation():
    footer = layout.footer()
    assert footer.id == "footer"
    assert footer_lines(footer)[:3] == [
        "El Niño Atlas is maintained by Alaa Al Khourdajie. "
        "ORCID: https://orcid.org/0000-0003-1376-7529",
        "Code: MIT licence, on GitHub. Data: licence stated with each panel.",
        "Cite: https://doi.org/10.5281/zenodo.22644790",
    ]
    anchors = [(a.children, a.href) for a in walk(footer) if isinstance(a, html.A)]
    assert anchors[1:] == [
        ("Alaa Al Khourdajie", "https://sites.google.com/site/akhourdajie/"),
        ("https://orcid.org/0000-0003-1376-7529", "https://orcid.org/0000-0003-1376-7529"),
        ("GitHub", "https://github.com/AlKhourdajie/El_Nino_Atlas"),
        ("https://doi.org/10.5281/zenodo.22644790", "https://doi.org/10.5281/zenodo.22644790"),
        ("Report a discrepancy", "https://github.com/AlKhourdajie/El_Nino_Atlas/issues"),
    ]
    badge = anchors[0]
    assert badge[1] == layout.CITATION_URL
    citation = yaml.safe_load(CITATION.read_text(encoding="utf-8"))
    (author,) = citation["authors"]
    assert layout.ORCID_URL == author["orcid"]
    assert layout.REPOSITORY_URL == citation["repository-code"]
    assert layout.CONCEPT_DOI == citation["doi"]


def test_footer_cite_block_and_build_line():
    footer = layout.footer(layout.BuildInfo("0123456789abcdef", "2026-09-07 21:00 UTC"))
    cite = footer.children[0]
    assert cite.id == "cite"
    ids = component_ids(cite)
    assert "copy-citation" in ids and "copy-status" in ids
    (build,) = [c for c in walk(footer) if getattr(c, "id", None) == "build-info"]
    assert line_text(build) == "Build 0123456, 2026-09-07 21:00 UTC"
    assert "build-info" not in component_ids(layout.footer())


def test_citation_text_reads_the_citation_file():
    cff = yaml.safe_load(CITATION.read_text(encoding="utf-8"))
    text = layout.citation_text(cff)
    assert text == (
        "Al Khourdajie, A. (2026). El Niño Atlas (version 0.2.0). "
        "https://doi.org/10.5281/zenodo.22644790"
    )


def test_page_copy_follows_the_rules():
    footer_lines_ = footer_lines(layout.footer())
    lines = (
        layout.OPENING,
        layout.SCOPE,
        *layout.ABOUT,
        *footer_lines_,
        *(label for label, _ in layout.NAV_ITEMS),
        layout.TIME_RANGE_LABEL,
        layout.BANDS_LABEL,
        layout.EVENT_SELECT_LABEL,
    )
    for text in lines:
        assert "—" not in text


def test_graph_config_trims_the_mode_bar_and_keeps_scroll_zoom_off():
    assert layout.GRAPH_CONFIG["responsive"] is True
    assert layout.GRAPH_CONFIG["scrollZoom"] is False
    assert layout.GRAPH_CONFIG["displaylogo"] is False
    assert "toImage" in layout.GRAPH_CONFIG["modeBarButtonsToRemove"]
    assert "lasso2d" in layout.GRAPH_CONFIG["modeBarButtonsToRemove"]
    # Nothing leaves the page: the cloud share button plotly.js 3.8 adds stays off.
    assert layout.GRAPH_CONFIG["showSendToCloud"] is False
    assert "sendChartToCloud" in layout.GRAPH_CONFIG["modeBarButtonsToRemove"]
    assert layout.MAP_CONFIG["showSendToCloud"] is False
    plain = layout.graph(go.Figure())
    assert plain.config == layout.GRAPH_CONFIG
    assert getattr(plain, "id", None) is None
    named = layout.graph(go.Figure(), id="activations-map", height=300)
    assert named.id == "activations-map" and named.style == {"height": "300px"}
    assert layout.map_config("/assets/topojson/")["topojsonURL"] == "/assets/topojson/"
    assert layout.map_config("/x/")["displayModeBar"] is False


def test_graph_container_takes_the_figure_height():
    assert layout.FIGURE_HEIGHT == theme.RESPONSIVE_LAYOUT["height"] == 420
    assert layout.graph(go.Figure()).style == {"height": "420px"}
    assert getattr(layout.graph(go.Figure(), height=None), "style", None) is None
    section = layout.panel("Forecast", EXPLAINER, go.Figure(), "2026-09-05T17:00:00Z", id="p")
    (graph,) = [c for c in walk(section) if isinstance(c, dcc.Graph)]
    assert graph.style == {"height": "420px"}


def test_legend_pairs_each_state_with_a_mark_style():
    legend = layout.legend()
    assert legend.id == "legend" and legend.role == "list"
    items = {item.id: item for item in legend.children}
    assert list(items) == ["legend-alert", "legend-no_alert", "legend-not_assessed"]
    for state, item in zip(("alert", "no_alert", "not_assessed"), legend.children, strict=True):
        swatch, label = item.children
        assert f"legend__swatch--{theme.STATE_MARKS[state]}" in swatch.className
        assert label.children == theme.STATE_LABELS[state]
    assert theme.STATE_MARKS["not_assessed"] == "hatched"
    assert theme.STATE_MARKS["no_alert"] == "outlined"


def test_download_toolbar_and_sources_section():
    toolbar = layout.download_toolbar("index")
    ids = component_ids(toolbar)
    assert ids == ["csv-index", "png-index", "svg-index", "export-sink-index"]
    assert list(layout.GRAPH_IDS) == ["index", "prices", "activations"]
    assert layout.download_toolbar("map", csv=False).children[1].id == "png-map"
    sources = layout.sources_section(
        [layout.SourceEntry("panel-index", EXPLAINER, "2026-09-05T17:00:00Z")]
    )
    assert sources.id == "sources"
    assert sources.children[0].children == layout.SOURCES_TITLE
    rendered = str(sources)
    assert "#panel-index" in rendered and "retrieved 2026-09-05T17:00:00Z" in rendered


EVENTS = [
    Event(
        "el_nino",
        date(1997, 5, 1),
        date(1998, 4, 1),
        ("MAM 1997", "MAM 1998"),
        2.28,
        date(1997, 11, 1),
    ),
    Event(
        "la_nina",
        date(2026, 4, 1),
        None,
        ("AMJ 2026", "JJA 2026"),
        -1.0,
        date(2026, 6, 1),
        True,
    ),
]


def test_event_options_and_windows():
    options = layout.event_options(EVENTS, date(2026, 9, 1))
    assert [o["label"] for o in options] == [
        "El Niño, MAM 1997 to MAM 1998",
        "La Niña, AMJ 2026 to JJA 2026, provisional",
    ]
    assert options[0]["value"] == "1996-04-01,1999-06-01"
    assert options[1]["value"] == "2025-03-01,2027-09-01"
    # A panel whose record starts later drops events that ended before it.
    later = layout.event_options(EVENTS, date(2026, 9, 1), not_before=date(2000, 1, 1))
    assert [o["label"] for o in later] == ["La Niña, AMJ 2026 to JJA 2026, provisional"]


def test_range_toolbar_is_per_panel():
    options = layout.event_options(EVENTS, date(2026, 9, 1))
    for key, buttons in (
        ("index", enso_index.RANGE_BUTTONS),
        ("prices", layout.range_buttons(1960)),
    ):
        toolbar = layout.range_toolbar(key, buttons, options)
        assert toolbar.id == f"time-controls-{key}"
        ids = component_ids(toolbar)
        assert ids[1:] == [
            f"range-all-{key}",
            f"range-30-{key}",
            f"range-5-{key}",
            f"event-select-{key}",
            f"bands-toggle-{key}",
        ]
        found = [c for c in walk(toolbar) if isinstance(c, html.Button)]
        assert [b.children for b in found[:3]] == [buttons[0]["label"], "30 years", "5 years"]
        (select,) = [c for c in walk(toolbar) if isinstance(c, html.Select)]
        assert [o.value for o in select.children] == ["", options[0]["value"], options[1]["value"]]
        toggle = found[3]
        assert toggle.children[1] == layout.BANDS_LABEL
        assert getattr(toggle, "aria-pressed") == "true"
    assert layout.range_buttons(1960)[0]["label"] == "From 1960"
    assert layout.range_buttons(1950)[0]["label"] == enso_index.RANGE_BUTTONS[0]["label"]
    assert layout.range_buttons(1950)[1:] == enso_index.RANGE_BUTTONS[1:]
    rows = layout.toolbars(html.Div(id="a"), html.Div(id="b"))
    assert rows.className == "card__toolbars" and component_ids(rows) == ["a", "b"]
    assert not hasattr(layout, "time_controls")


def test_page_wraps_main_in_a_landmark():
    page = layout.page(html.Div(id="before"), main=(html.Div(id="inside"),))
    assert page.id == "atlas-page"
    (main,) = [c for c in walk(page) if isinstance(c, html.Main)]
    assert main.id == "main" and "inside" in component_ids(main)
    assert "before" not in component_ids(main)
