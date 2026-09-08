"""Tests for the page assembly in app.py.

``load_frame``, ``snapshot_metadata`` and ``load_activations`` are
monkeypatched so that no test reads the snapshot directory, the curated
register or the network, apart from the tests that check the served
layout against the committed files.
"""

import re

import plotly.io as pio
import pytest
from dash import dcc, html

from src import activations, data_access, layout
from src.layers import activations_map, teleconnections
from tests.support import RETRIEVED_AT, component_ids, index_frame, price_frame, walk
from tests.test_activations import discrepancy, example_entry, no_activation_entry

ORDER = [
    "skip-link",
    "site-nav",
    "opening",
    "about",
    "panel-index",
    "panel-commodities",
    "panel-activations",
    "panel-teleconnections",
    "sources",
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


def assert_in_page_order(page) -> None:
    ids = component_ids(page)
    positions = [ids.index(id) for id in ORDER]
    assert positions == sorted(positions)


def graphs(page) -> list:
    return [c for c in walk(page) if isinstance(c, dcc.Graph)]


def headings(page) -> list[str]:
    """The section and card headings in page order."""
    return [c.children for c in walk(page) if isinstance(c, html.H2)]


def stages(page) -> list[str]:
    return [c.children for c in walk(page) if getattr(c, "className", None) == "card__stage"]


def banners(page) -> list:
    return [c for c in walk(page) if getattr(c, "role", None) == "alert"]


def reading_line(page) -> html.P | None:
    lines = [c for c in walk(page) if getattr(c, "id", None) == "latest-reading"]
    assert len(lines) <= 1
    return lines[0] if lines else None


# The reading the synthetic index frame yields: the last run FMA to JJA 2026 has
# five seasons, so it is not provisional.
READING = "Latest three-month season (June to August 2026): RONI +1.20 °C, ONI +1.40 °C."
SCHEMATIC = "Where El Niño usually matters: draft schematic"
HEADINGS = [
    "About",
    "Relative Oceanic Niño Index (RONI) and Oceanic Niño Index (ONI)",
    "Commodity prices: the World Bank Pink Sheet",
    "Anticipatory-action activations",
    SCHEMATIC,
    layout.SOURCES_TITLE,
]
STAGES = ["The event", "Realised impact", "Anticipatory action"]


def activation_rows(page) -> list[html.Tr]:
    return [
        c
        for c in walk(page)
        if isinstance(c, html.Tr) and str(getattr(c, "id", "")).startswith("activation-")
    ]


def assert_activation_panel(page, entries: list[dict]) -> None:
    """Legend, map and table in that order, showing ``entries``."""
    (section,) = [c for c in walk(page) if getattr(c, "id", None) == "panel-activations"]
    assert isinstance(section, html.Section)
    assert section.children[0].children[0].children == "Anticipatory action"
    ids = component_ids(section)
    assert ids.index("legend") < ids.index("activations-map") < ids.index("activations-table")
    for state in ("alert", "no_alert", "not_assessed"):
        assert f"legend-{state}" in ids
    (graph,) = [c for c in walk(section) if isinstance(c, dcc.Graph)]
    assert graph.id == "activations-map"
    assert graph.config["displayModeBar"] is False
    assert graph.config["topojsonURL"].endswith("/assets/topojson/")
    assert graph.style == {"height": "460px"}
    (figure,) = [c for c in walk(section) if isinstance(c, html.Figure)]
    assert "activations-table" not in component_ids(figure)
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
    assert "csv-activations" in ids and "png-activations" in ids


def test_app_imports_and_layout_builds():
    import app as app_module

    assert app_module.server is not None
    assert_in_page_order(app_module.app.layout)
    assert app_module.PAGE_DATA.graph_keys == ["index", "prices", "activations"]
    assert app_module.PAGE_DATA.csv_keys == ["index", "prices", "activations"]


def test_page_with_both_snapshots(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame(), "worldbank_pink_sheet": prices()})
    entries = [example_entry(), no_activation_entry()]
    install_register(monkeypatch, entries)
    page = app_module.build_page()
    assert_in_page_order(page)
    rendered = str(page)
    assert layout.OPENING in rendered
    assert layout.SCOPE in rendered
    assert " ".join(layout.ABOUT) in rendered
    footer_urls = (layout.MAINTAINER_URL, layout.ORCID_URL, layout.REPOSITORY_URL)
    for url in (*footer_urls, layout.CITATION_URL, layout.ISSUES_URL):
        assert url in rendered
    assert layout.UNAVAILABLE_NOTICE not in rendered
    assert not banners(page)
    # Each snapshot stamp appears on its card and in the sources section.
    assert rendered.count(f"retrieved {RETRIEVED_AT}") == 4
    assert [g.id for g in graphs(page)] == ["graph-index", "graph-commodities", "activations-map"]
    assert headings(page) == HEADINGS
    assert stages(page) == STAGES
    assert reading_line(page).children == READING
    ids = component_ids(page)
    assert ids.index("latest-reading") == ids.index("opening") + 1
    assert ids.index("scope") == ids.index("latest-reading") + 1
    assert_activation_panel(page, entries)
    assert_schematic_panel(page, teleconnections.IMAGE_URL_PATH)
    assert "Imperial" not in rendered and "Maintained by" not in rendered
    # Each time-series panel has its own range controls and event select;
    # the index lists the three synthetic events, the price panel, whose
    # synthetic record starts in 2009, only the events that reach it.
    selects = {c.id: c for c in walk(page) if isinstance(c, html.Select)}
    assert set(selects) == {"event-select-index", "event-select-prices"}
    assert len(selects["event-select-index"].children) == 4
    assert len(selects["event-select-prices"].children) == 3
    ids = component_ids(page)
    for key in ("index", "prices"):
        for prefix in ("range-all-", "range-30-", "range-5-", "bands-toggle-", "csv-", "png-"):
            assert f"{prefix}{key}" in ids
    (from_button,) = [c for c in walk(page) if getattr(c, "id", None) == "range-all-prices"]
    assert from_button.children == "From 2009"
    (index_from,) = [c for c in walk(page) if getattr(c, "id", None) == "range-all-index"]
    assert index_from.children == "From 1950"


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
    assert schematic.children[0].children[0].children == SCHEMATIC
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
    assert_in_page_order(page)
    rendered = str(page)
    assert rendered.count(layout.UNAVAILABLE_NOTICE) == 2
    assert f"retrieved {RETRIEVED_AT}" not in rendered
    assert not banners(page)
    # The map draws from the register, so it is the one graph without snapshots.
    assert [g.id for g in graphs(page)] == ["activations-map"]
    for title in (
        "Relative Oceanic Niño Index (RONI)",
        "Commodity prices: the World Bank Pink Sheet",
    ):
        assert title in rendered
    assert layout.OPENING in rendered
    assert headings(page) == HEADINGS
    assert stages(page) == STAGES
    assert reading_line(page) is None
    assert "Latest three-month season" not in rendered
    # With no curated entries every country is not tracked, which is correct.
    assert_activation_panel(page, [])
    # The schematic is a static asset, so it shows whether or not snapshots exist.
    assert_schematic_panel(page, teleconnections.IMAGE_URL_PATH)
    assert not [c for c in walk(page) if isinstance(c, html.Select)]


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


def test_register_failure_renders_a_banner_naming_the_register(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {})

    def malformed():
        raise ValueError("activations[0]: missing fields")

    monkeypatch.setattr(activations, "load_activations", malformed)
    page = app_module.build_page()
    (banner,) = banners(page)
    rendered = str(banner)
    assert layout.ERROR_PREFIX in rendered
    assert app_module.REGISTER_SOURCE in rendered
    assert "ValueError: activations[0]: missing fields" in rendered
    (section,) = [c for c in walk(page) if getattr(c, "id", None) == "panel-activations"]
    assert banner in list(walk(section))
    assert not [c for c in walk(section) if isinstance(c, dcc.Graph)]
    assert activations_map.explainer().title in str(section)
    assert headings(page) == HEADINGS


def test_snapshot_failure_renders_a_banner_naming_the_source(monkeypatch):
    import app as app_module

    def broken(source_id):
        raise ValueError("malformed snapshot")

    monkeypatch.setattr(data_access, "load_frame", broken)
    install_register(monkeypatch, [])
    page = app_module.build_page()
    found = banners(page)
    assert len(found) == 2
    for banner, source_id in zip(found, ("noaa_oni", "worldbank_pink_sheet"), strict=True):
        rendered = str(banner)
        assert f"({source_id})" in rendered
        assert "ValueError: malformed snapshot" in rendered
    assert [g.id for g in graphs(page)] == ["activations-map"]
    assert reading_line(page) is None
    assert layout.UNAVAILABLE_NOTICE not in str(page)


def test_missing_metadata_beside_a_frame_is_a_banner_too(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame()})
    install_register(monkeypatch, [])

    def missing_metadata(source_id):
        raise FileNotFoundError("metadata missing although the frame exists")

    monkeypatch.setattr(data_access, "snapshot_metadata", missing_metadata)
    page = app_module.build_page()
    (banner,) = banners(page)
    assert "FileNotFoundError: metadata missing although the frame exists" in str(banner)
    assert "(noaa_oni)" in str(banner)
    assert reading_line(page) is None


def test_figure_build_failure_renders_a_banner(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame(), "worldbank_pink_sheet": prices()})
    install_register(monkeypatch, [])
    monkeypatch.setattr(
        app_module.commodities,
        "build_figure",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("series 'RICE_05' mixes units")),
    )
    page = app_module.build_page()
    (banner,) = banners(page)
    assert "ValueError: series 'RICE_05' mixes units" in str(banner)
    assert "(worldbank_pink_sheet)" in str(banner)
    assert [g.id for g in graphs(page)] == ["graph-index", "activations-map"]
    ids = component_ids(page)
    assert "range-all-index" in ids and "range-all-prices" not in ids


def test_activation_card_notes_discrepancies(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {})
    with_note = {**example_entry(), "discrepancies": [discrepancy()]}
    install_register(monkeypatch, [with_note])
    page = app_module.build_page()
    (section,) = [c for c in walk(page) if getattr(c, "id", None) == "panel-activations"]
    notes = [c for c in walk(section) if getattr(c, "className", None) == "card__note"]
    assert len(notes) == 1
    assert "Companion documents differ." in str(notes[0])
    install_register(monkeypatch, [example_entry()])
    page = app_module.build_page()
    (section,) = [c for c in walk(page) if getattr(c, "id", None) == "panel-activations"]
    assert not [c for c in walk(section) if getattr(c, "className", None) == "card__note"]


def test_page_renders_on_narrow_screens(monkeypatch):
    import app as app_module

    install_snapshots(monkeypatch, {"noaa_oni": index_frame(), "worldbank_pink_sheet": prices()})
    install_register(monkeypatch, [example_entry()])
    page = app_module.build_page()
    for graph in graphs(page):
        assert graph.figure.layout.width is None
        assert graph.config["responsive"] is True
        assert graph.config["scrollZoom"] is False
        # A fixed container height, or Dash sizes the figure to its column.
        assert graph.style["height"].endswith("px")


def test_index_html_is_self_contained():
    import app as app_module

    html_text = app_module.app.index()
    assert '<html lang="en-GB">' in html_text
    assert 'name="color-scheme"' in html_text
    assert "skeleton--card" in html_text and "Loading..." not in html_text
    assert 'localStorage.getItem("theme-store")' in html_text
    assert not re.search(r"https?://(cdn|fonts|unpkg|cdnjs)", html_text)
    assert not app_module.app.config.external_stylesheets
    assert not app_module.app.config.external_scripts


def test_served_files_are_compressed_and_fingerprinted_files_cached():
    import app as app_module

    client = app_module.server.test_client()
    page = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert page.status_code == 200
    assert page.headers.get("Content-Encoding") == "gzip"
    assert "Cache-Control" not in page.headers or "immutable" not in page.headers["Cache-Control"]
    script = client.get("/assets/atlas.js?m=1", headers={"Accept-Encoding": "gzip"})
    assert script.status_code == 200
    assert script.headers.get("Content-Encoding") == "gzip"
    assert script.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert "Accept-Encoding" in script.headers.get("Vary", "")
    plain = client.get("/assets/atlas.js?m=1")
    assert plain.headers.get("Content-Encoding") is None
    assert plain.data.startswith(b"/* El Ni")
    font = client.get(
        "/assets/fonts/SourceSans3-latin.woff2?m=1", headers={"Accept-Encoding": "gzip"}
    )
    assert font.status_code == 200 and font.headers.get("Content-Encoding") is None
    assert font.headers["Cache-Control"].endswith("immutable")
    layout_json = client.get("/_dash-layout", headers={"Accept-Encoding": "gzip"})
    assert layout_json.headers.get("Content-Encoding") == "gzip"
    assert "immutable" not in layout_json.headers.get("Cache-Control", "")


def test_callbacks_cover_state_theme_exports_and_downloads():
    import app as app_module

    outputs = set(app_module.app.callback_map)
    assert (
        "..view-state.data...url.search...bands-toggle-index.aria-pressed..."
        "bands-toggle-prices.aria-pressed.."
    ) in outputs
    assert "state-sink.children" in outputs
    assert "theme-store.data" in outputs and "theme-sink.children" in outputs
    assert "copy-status.children" in outputs
    assert "download.data" in outputs
    for key in ("index", "prices", "activations"):
        assert f"export-sink-{key}.children" in outputs


def test_csv_downloads_carry_a_provenance_header():
    import app as app_module

    href = "https://el-nino-atlas.onrender.com/?index_range=1996-09-01,2026-09-01&prices_bands=off"
    for key, builder in app_module.CSV_BUILDERS.items():
        text = builder(app_module.PAGE_DATA, href)
        head = text.splitlines()[:8]
        assert head[0].startswith(f"# {layout.TITLE}: ")
        assert any(line.startswith("# licence: ") for line in head)
        assert any(line.startswith("# retrieved: ") for line in head)
        assert f"# concept DOI: {layout.CITATION_URL}" in head
        assert f"# permalink: {href}" in head
        body = text.splitlines()[8:]
        assert len(body) > 1, key
        assert body[0].startswith(("date,", "id,"))


def test_build_info_names_a_commit_or_unknown(monkeypatch):
    import app as app_module

    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef0123456789")
    info = app_module.build_info()
    assert info.sha == "abcdef0123456789" and info.short == "abcdef0"
    assert info.built_at.endswith(" UTC")
    monkeypatch.delenv("RENDER_GIT_COMMIT")
    monkeypatch.setattr(app_module, "_git_sha", lambda: None)
    assert app_module.build_info().sha == "unknown"


def test_plotly_templates_registered():
    from src import theme

    theme.register_templates()
    assert theme.TEMPLATE_DARK in pio.templates
    assert theme.TEMPLATE_LIGHT in pio.templates
    assert pio.templates.default == theme.TEMPLATE_LIGHT


def test_not_assessed_never_shares_no_alert_colour():
    from src import theme
    from src.layout import legend

    assert theme.STATE_COLOURS["not_assessed"] != theme.STATE_COLOURS["no_alert"]
    assert theme.STATE_COLOURS["not_assessed"] != theme.STATE_COLOURS["alert"]
    rendered = str(legend())
    for state in ("alert", "no_alert", "not_assessed"):
        assert f"legend-{state}" in rendered


@pytest.mark.parametrize("key", ["index", "prices", "activations"])
def test_export_metadata_carries_one_source_line(key):
    import app as app_module

    (store,) = [
        c for c in walk(app_module.app.layout) if getattr(c, "id", None) == f"export-meta-{key}"
    ]
    assert store.data["graph"] == layout.GRAPH_IDS[key]
    assert store.data["source"].startswith(("Source: ", "The World Bank"))
    assert layout.CITATION_URL in store.data["source"]
    assert store.data["stem"] == app_module.CSV_STEMS[key]
