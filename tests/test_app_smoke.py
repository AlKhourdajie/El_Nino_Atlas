"""Tests for the page assembly in app.py.

``load_frame`` and ``snapshot_metadata`` are monkeypatched so that no
test reads the snapshot directory or the network.
"""

import dash_bootstrap_components as dbc
import plotly.io as pio
import pytest
from dash import dcc, html

from src import data_access, layout
from src.layers import teleconnections
from tests.support import RETRIEVED_AT, component_ids, index_frame, price_frame, walk

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


def test_app_imports_and_layout_builds():
    import app as app_module

    assert app_module.server is not None
    assert_in_spine_order(app_module.app.layout)


def test_page_with_both_snapshots(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame(), "worldbank_pink_sheet": prices()})
    page = app_module.build_page()
    assert_in_spine_order(page)
    rendered = str(page)
    assert layout.OPENING in rendered
    assert " ".join(layout.ABOUT) in rendered
    assert layout.LICENCE_LINE in rendered
    assert layout.CITATION_URL in rendered
    assert layout.UNAVAILABLE_NOTICE not in rendered
    assert rendered.count(f"retrieved {RETRIEVED_AT}") == 2
    assert len(graphs(page)) == 2
    assert headings(page) == ["About", "The event", "Realised impact", SCHEMATIC]
    assert reading_line(page).children == READING
    ids = component_ids(page)
    assert ids.index("latest-reading") == ids.index("opening") + 1
    (empty,) = [c for c in walk(page) if getattr(c, "id", None) == "panel-activations"]
    assert isinstance(empty, html.Div) and not empty.children
    assert_schematic_panel(page, teleconnections.IMAGE_URL_PATH)


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
    page = app_module.build_page()
    assert_in_spine_order(page)
    rendered = str(page)
    assert rendered.count(layout.UNAVAILABLE_NOTICE) == 2
    assert f"retrieved {RETRIEVED_AT}" not in rendered
    assert not graphs(page)
    for title in (
        "Relative Oceanic Niño Index (RONI)",
        "Commodity prices: the World Bank Pink Sheet",
    ):
        assert title in rendered
    assert layout.OPENING in rendered
    assert headings(page) == ["About", "The event", "Realised impact", SCHEMATIC]
    assert reading_line(page) is None
    assert "Latest three-month season" not in rendered
    # The schematic is a static asset, so it shows whether or not snapshots exist.
    assert_schematic_panel(page, teleconnections.IMAGE_URL_PATH)


def test_commodity_panel_waits_for_the_index_snapshot(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"worldbank_pink_sheet": prices()})
    page = app_module.build_page()
    assert str(page).count(layout.UNAVAILABLE_NOTICE) == 2
    assert not graphs(page)
    assert reading_line(page) is None


def test_index_panel_renders_without_the_price_snapshot(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame()})
    page = app_module.build_page()
    assert str(page).count(layout.UNAVAILABLE_NOTICE) == 1
    assert len(graphs(page)) == 1
    assert reading_line(page).children == READING


def test_page_renders_on_narrow_screens(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame(), "worldbank_pink_sheet": prices()})
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
