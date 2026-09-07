"""Tests for the page assembly in app.py.

``load_frame``, ``snapshot_metadata`` and ``load_activations`` are
monkeypatched so that no test reads the snapshot directory, the curated
register or the network, apart from the tests that check the served
layout against the committed files.
"""

import dash_bootstrap_components as dbc
import plotly.io as pio
import pytest
from dash import dcc, html

from src import activations, data_access, layout
from src.layers import activations_map, teleconnections
from tests.support import RETRIEVED_AT, component_ids, index_frame, price_frame, walk
from tests.test_activations import example_entry, no_activation_entry

ORDER = [
    "opening",
    "about",
    "panel-index",
    "panel-activations",
    "panel-commodities",
    "panel-teleconnections",
    "footer",
]
UNITS = {
    "COFFEE_ARABIC": "USD/kg",
    "COFFEE_ROBUS": "USD/kg",
    "COCOA": "USD/kg",
    "SUGAR_WLD": "USD/kg",
    "RICE_05": "USD/mt",
}


def prices():
    return price_frame(
        {sid: (unit, [1.0 + 0.01 * k for k in range(200)]) for sid, unit in UNITS.items()}
    )


def install_snapshots(monkeypatch, frames: dict) -> None:
    """Serve ``frames`` by source id; every other id has no snapshot."""

    def load_frame(source_id):
        if source_id not in frames:
            raise FileNotFoundError(f"No snapshot for {source_id}. Run: python run.py update")
        return frames[source_id]

    def snapshot_metadata(source_id):
        assert source_id in frames, "metadata must only be read after load_frame succeeds"
        return {"source_id": source_id, "retrieved_at": RETRIEVED_AT}

    monkeypatch.setattr(data_access, "load_frame", load_frame)
    monkeypatch.setattr(data_access, "snapshot_metadata", snapshot_metadata)


def install_register(monkeypatch, entries: list[dict]) -> None:
    """Serve ``entries`` as the validated register, examples already excluded."""
    monkeypatch.setattr(activations, "load_activations", lambda: entries)


def assert_in_spine_order(page) -> None:
    ids = component_ids(page)
    positions = [ids.index(id) for id in ORDER]
    assert positions == sorted(positions)


def graphs(page) -> list:
    return [c for c in walk(page) if isinstance(c, dcc.Graph)]


def headings(page) -> list[str]:
    """The section headings in page order."""
    return [c.children for c in walk(page) if isinstance(c, html.H2)]


def reading_line(page) -> html.P | None:
    lines = [c for c in walk(page) if getattr(c, "id", None) == "latest-reading"]
    assert len(lines) <= 1
    return lines[0] if lines else None


# The reading the synthetic index frame yields: the last run FMA to JJA 2026 has
# five seasons, so it is not provisional.
READING = "Latest three-month season (June to August 2026): RONI +1.20 °C, ONI +1.40 °C."
SCHEMATIC = "Where El Niño usually matters: draft schematic"
HEADINGS = ["About", "The event", "Anticipatory action", "Realised impact", SCHEMATIC]


def activation_rows(page) -> list[html.Tr]:
    return [
        c
        for c in walk(page)
        if isinstance(c, html.Tr) and str(getattr(c, "id", "")).startswith("activation-")
    ]


def assert_activation_panel(page, entries: list[dict]) -> None:
    """Legend, map and table in that order beside the explainer, showing ``entries``."""
    (section,) = [c for c in walk(page) if getattr(c, "id", None) == "panel-activations"]
    assert isinstance(section, html.Section)
    assert (
        next(c for c in walk(section) if isinstance(c, html.H2)).children == "Anticipatory action"
    )
    ids = component_ids(section)
    assert ids.index("legend") < ids.index("activations-map") < ids.index("activations-table")
    for state in ("alert", "no_alert", "not_assessed"):
        assert f"legend-{state}" in ids
    (graph,) = [c for c in walk(section) if isinstance(c, dcc.Graph)]
    assert graph.id == "activations-map" and graph.config == layout.GRAPH_CONFIG
    choropleth = next(t for t in graph.figure.data if t.type == "choropleth")
    states = dict(zip(choropleth.locations, choropleth.z, strict=True))
    for entry in entries:
        expected = activations_map.STATE_BY_STATUS[entry["status"]]
        assert activations_map.STATE_ORDER[int(states[entry["iso3"]])] == expected
    assert [row.id for row in activation_rows(section)] == [
        f"activation-{e['id']}" for e in entries
    ]
    rendered = str(section)
    assert activations_map.explainer().title in rendered
    assert (activations_map.NO_ENTRIES_TEXT in rendered) == (not entries)


def test_app_imports_and_layout_builds():
    import app as app_module

    assert app_module.server is not None
    assert_in_spine_order(app_module.app.layout)


def test_page_with_both_snapshots(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame(), "worldbank_pink_sheet": prices()})
    entries = [example_entry(), no_activation_entry()]
    install_register(monkeypatch, entries)
    page = app_module.build_page()
    assert_in_spine_order(page)
    rendered = str(page)
    assert layout.OPENING in rendered
    assert " ".join(layout.ABOUT) in rendered
    assert layout.LICENCE_LINE in rendered
    assert layout.CITATION_URL in rendered
    assert layout.UNAVAILABLE_NOTICE not in rendered
    assert rendered.count(f"retrieved {RETRIEVED_AT}") == 2
    assert len(graphs(page)) == 3
    assert headings(page) == HEADINGS
    assert reading_line(page).children == READING
    ids = component_ids(page)
    assert ids.index("latest-reading") == ids.index("opening") + 1
    assert_activation_panel(page, entries)
    assert_schematic_panel(page, teleconnections.IMAGE_URL_PATH)


def test_served_layout_shows_the_committed_register_without_its_examples():
    import app as app_module

    real = activations.load_activations()
    assert not any(e.get("example") for e in real)
    assert_activation_panel(app_module.app.layout, real)
    examples = [e for e in activations.load_activations(include_examples=True) if e.get("example")]
    assert examples
    rendered = str(app_module.app.layout)
    assert all(f"activation-{e['id']}" not in rendered for e in examples)


def assert_schematic_panel(page, image_src: str) -> None:
    (schematic,) = [c for c in walk(page) if getattr(c, "id", None) == "panel-teleconnections"]
    assert isinstance(schematic, html.Section)
    assert next(c for c in walk(schematic) if isinstance(c, html.H2)).children == SCHEMATIC
    (image,) = [c for c in walk(page) if isinstance(c, html.Img)]
    assert image.src == image_src
    assert image.alt == teleconnections.IMAGE_ALT
    rendered = str(schematic)
    assert teleconnections.SOURCE_URL in rendered
    assert f"retrieved {teleconnections.IMAGE_RETRIEVED_AT}" in rendered


def test_schematic_is_served_from_the_app_asset_url():
    import app as app_module

    served = app_module.app.get_asset_url(teleconnections.IMAGE_ASSET)
    assert served == "/assets/teleconnections/noaa_cpc_elnino_impacts.jpg"
    assert_schematic_panel(app_module.app.layout, served)
    assert_schematic_panel(
        app_module.build_page(image_src="/prefix/assets/x.jpg"), "/prefix/assets/x.jpg"
    )


def test_page_without_snapshots(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {})
    install_register(monkeypatch, [])
    page = app_module.build_page()
    assert_in_spine_order(page)
    rendered = str(page)
    assert rendered.count(layout.UNAVAILABLE_NOTICE) == 2
    assert f"retrieved {RETRIEVED_AT}" not in rendered
    # The map draws from the register, so it is the one graph without snapshots.
    assert [g.id for g in graphs(page)] == ["activations-map"]
    for title in (
        "Relative Oceanic Niño Index (RONI)",
        "Commodity prices: the World Bank Pink Sheet",
    ):
        assert title in rendered
    assert layout.OPENING in rendered
    assert headings(page) == HEADINGS
    assert reading_line(page) is None
    assert "Latest three-month season" not in rendered
    # With no curated entries every country is not tracked, which is correct.
    assert_activation_panel(page, [])
    # The schematic is a static asset, so it shows whether or not snapshots exist.
    assert_schematic_panel(page, teleconnections.IMAGE_URL_PATH)


def test_commodity_panel_waits_for_the_index_snapshot(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"worldbank_pink_sheet": prices()})
    install_register(monkeypatch, [])
    page = app_module.build_page()
    assert str(page).count(layout.UNAVAILABLE_NOTICE) == 2
    assert [g.id for g in graphs(page)] == ["activations-map"]
    assert reading_line(page) is None


def test_index_panel_renders_without_the_price_snapshot(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame()})
    install_register(monkeypatch, [])
    page = app_module.build_page()
    assert str(page).count(layout.UNAVAILABLE_NOTICE) == 1
    assert len(graphs(page)) == 2
    assert reading_line(page).children == READING


def test_register_errors_propagate(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {})

    def malformed():
        raise ValueError("activations[0]: missing fields")

    monkeypatch.setattr(activations, "load_activations", malformed)
    with pytest.raises(ValueError, match="missing fields"):
        app_module.build_page()


def test_page_renders_on_narrow_screens(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame(), "worldbank_pink_sheet": prices()})
    install_register(monkeypatch, [example_entry()])
    page = app_module.build_page()
    assert page.fluid is True
    for graph in graphs(page):
        assert graph.figure.layout.width is None
        assert graph.config == layout.GRAPH_CONFIG
    columns = [c for c in walk(page) if isinstance(c, dbc.Col)]
    assert columns and all(column.xs == 12 for column in columns)


def test_errors_other_than_a_missing_snapshot_propagate(monkeypatch):
    import app as app_module

    def broken(source_id):
        raise ValueError("malformed snapshot")

    monkeypatch.setattr(data_access, "load_frame", broken)
    install_register(monkeypatch, [])
    with pytest.raises(ValueError, match="malformed snapshot"):
        app_module.build_page()

    install_snapshots(monkeypatch, {"noaa_oni": index_frame()})

    def missing_metadata(source_id):
        raise FileNotFoundError("metadata missing although the frame exists")

    monkeypatch.setattr(data_access, "snapshot_metadata", missing_metadata)
    with pytest.raises(FileNotFoundError, match="metadata missing"):
        app_module.build_page()


def test_plotly_templates_registered():
    from src import theme

    theme.register_templates()
    assert theme.TEMPLATE_DARK in pio.templates
    assert theme.TEMPLATE_LIGHT in pio.templates


def test_not_assessed_never_shares_no_alert_colour():
    from src import theme
    from src.layout import legend

    assert theme.STATE_COLOURS["not_assessed"] != theme.STATE_COLOURS["no_alert"]
    assert theme.STATE_COLOURS["not_assessed"] != theme.STATE_COLOURS["alert"]
    rendered = str(legend())
    for state in ("alert", "no_alert", "not_assessed"):
        assert f"legend-{state}" in rendered
