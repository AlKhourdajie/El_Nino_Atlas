"""Tests for the anticipatory-action activation map layer."""

import logging

import pycountry
import pytest
from dash import html

from src import theme
from src.activations import REGISTER_PATH, load_activations
from src.layers import activations_map as layer
from src.layers.activations_map import (
    GRAPH_CONFIG,
    NOT_TRACKED,
    STATE_ORDER,
    build_figure,
    build_panel,
    build_table,
    explainer,
)
from src.layout.explainer import Explainer
from tests.support import walk
from tests.test_activations import discrepancy, example_entry, no_activation_entry


def entries() -> list[dict]:
    return [example_entry(), no_activation_entry()]


def choropleth(fig):
    return next(t for t in fig.data if t.type == "choropleth")


def legend_traces(fig):
    return [t for t in fig.data if t.type == "scattergeo"]


def state_of(fig, iso3: str) -> str:
    trace = choropleth(fig)
    return STATE_ORDER[int(trace.z[list(trace.locations).index(iso3)])]


def colour_of(fig, iso3: str) -> str:
    """Resolve the fill colour plotly gives ``iso3`` through the stepped colourscale."""
    trace = choropleth(fig)
    z = trace.z[list(trace.locations).index(iso3)]
    normalised = (z - trace.zmin) / (trace.zmax - trace.zmin)
    bands = [(float(start), colour) for start, colour in trace.colorscale[::2]]
    return [colour for start, colour in bands if start <= normalised + 1e-9][-1]


def test_every_pycountry_code_is_a_location():
    trace = choropleth(build_figure(entries()))
    assert trace.locationmode == "ISO-3"
    assert sorted(trace.locations) == sorted(c.alpha_3 for c in pycountry.countries)
    assert len(trace.locations) == len(set(trace.locations))


def test_entries_take_alert_and_no_alert_and_others_not_tracked():
    fig = build_figure(entries())
    assert state_of(fig, "GTM") == "alert"
    assert state_of(fig, "NIC") == "no_alert"
    assert state_of(fig, "HND") == NOT_TRACKED
    others = [c for c in choropleth(fig).locations if c not in ("GTM", "NIC")]
    assert all(state_of(fig, code) == NOT_TRACKED for code in others)


def test_no_entry_renders_with_the_not_tracked_colour():
    fig = build_figure(entries())
    not_tracked = theme.STATE_COLOURS[NOT_TRACKED]
    for entry in entries():
        assert state_of(fig, entry["iso3"]) != NOT_TRACKED
        assert colour_of(fig, entry["iso3"]) != not_tracked
    assert colour_of(fig, "GTM") == theme.STATE_COLOURS["alert"]
    assert colour_of(fig, "NIC") == theme.STATE_COLOURS["no_alert"]
    assert colour_of(fig, "HND") == not_tracked


def test_colourscale_uses_only_the_three_theme_tokens():
    colours = {colour for _, colour in choropleth(build_figure(entries())).colorscale}
    assert colours == set(theme.STATE_COLOURS.values())


def test_example_entry_never_renders():
    flagged = {**example_entry(), "example": True}
    fig = build_figure([flagged])
    assert state_of(fig, "GTM") == NOT_TRACKED
    assert "example_gtm_cerf_aa" not in str(build_table([flagged]))

    register = load_activations(REGISTER_PATH, include_examples=True)
    examples = [e for e in register if e.get("example")]
    assert examples, "the register should carry its example entry"
    fig = build_figure(register)
    for entry in examples:
        assert state_of(fig, entry["iso3"]) == NOT_TRACKED
    rendered = str(build_panel(register))
    assert all(entry["id"] not in rendered for entry in examples)


def test_empty_register_renders_no_rows():
    assert layer.NO_ENTRIES_TEXT in str(build_table([]))


def test_register_entries_render_one_row_each_and_never_not_tracked():
    register = load_activations(REGISTER_PATH)
    rendered = str(build_table(register))
    assert (layer.NO_ENTRIES_TEXT in rendered) == (not register)
    fig = build_figure(register)
    for entry in register:
        assert f"activation-{entry['id']}" in rendered
        assert state_of(fig, entry["iso3"]) != NOT_TRACKED


def test_country_with_mixed_entries_renders_activated():
    mixed = [
        no_activation_entry(),
        {**example_entry(), "id": "nic_wfp", "iso3": "NIC", "framework": "wfp_aa"},
    ]
    assert state_of(build_figure(mixed), "NIC") == "alert"
    assert state_of(build_figure(list(reversed(mixed))), "NIC") == "alert"


def test_hover_shows_country_framework_date_amount_and_people():
    trace = choropleth(build_figure(entries()))
    hover = dict(zip(trace.locations, trace.text, strict=True))
    for needle in (
        "<b>Guatemala</b>",
        "Central Emergency Response Fund (CERF) anticipatory action",
        "Date: 5 March 2026",
        "Amount (US dollars): 1,000,000",
        "People targeted: 20,000",
    ):
        assert needle in hover["GTM"]
    assert "Status: Framework, no activation" in hover["NIC"]
    assert hover["NIC"].count("none") == 3
    assert hover["HND"] == "<b>Honduras</b><br>Not tracked: no entry in the register"
    assert trace.hovertemplate == "%{text}<extra></extra>"


def test_null_figures_render_as_not_assessed():
    unknown = {**example_entry(), "amount_usd": None, "people_targeted": None, "trigger": None}
    trace = choropleth(build_figure([unknown]))
    hover = dict(zip(trace.locations, trace.text, strict=True))["GTM"]
    assert "Amount (US dollars): not assessed" in hover
    assert "People targeted: not assessed" in hover
    assert "not assessed" in str(build_table([unknown]))


def test_layout_is_static_natural_earth():
    fig = build_figure(entries())
    assert fig.layout.dragmode is False
    assert fig.layout.geo.projection.type == "natural earth"
    assert choropleth(fig).showscale is False
    assert GRAPH_CONFIG["scrollZoom"] is False
    assert GRAPH_CONFIG["displayModeBar"] is False
    assert GRAPH_CONFIG["showSendToCloud"] is False
    assert fig.layout.height == theme.MAP_HEIGHT
    assert fig.layout.uirevision == theme.UI_REVISION


def test_legend_lists_the_three_state_labels_beneath_the_map():
    fig = build_figure(entries())
    traces = legend_traces(fig)
    assert len(traces) == len(STATE_ORDER)
    by_name = {t.name: t for t in traces}
    for state in STATE_ORDER:
        # Short labels keep the horizontal legend inside a narrow screen; the
        # definitions stay in the hover text.
        trace = by_name[layer.STATE_LABELS[state]]
        assert trace.marker.symbol == theme.STATE_MARKER_SYMBOLS[state]
    assert all(t.showlegend is True and t.hoverinfo == "skip" for t in traces)
    assert fig.layout.legend.orientation == "h"
    assert fig.layout.legend.yanchor == "top" and fig.layout.legend.y <= 0
    assert fig.layout.legend.font.size == layer.LEGEND_FONT_SIZE
    hover = dict(zip(choropleth(fig).locations, choropleth(fig).text, strict=True))
    assert layer.STATE_DEFINITIONS[NOT_TRACKED] in hover["HND"]


def test_entries_carry_centroid_markers_in_their_mark_style():
    fig = build_figure(entries())
    by_name = {t.name: t for t in legend_traces(fig)}
    activated = by_name[layer.STATE_LABELS["alert"]]
    assert list(activated.locations) == ["GTM"]
    assert activated.marker.symbol == "circle"
    assert activated.marker.color == theme.STATE_COLOURS["alert"]
    framework = by_name[layer.STATE_LABELS["no_alert"]]
    assert list(framework.locations) == ["NIC"]
    assert framework.marker.symbol == "circle-open"
    assert framework.marker.line.color == theme.STATE_COLOURS["no_alert"]
    not_tracked = by_name[layer.STATE_LABELS["not_assessed"]]
    assert not_tracked.locations is None and list(not_tracked.lon) == [None]
    # Roles let the client recolour the map per scheme.
    assert choropleth(fig).meta["role"] == "choropleth"
    assert {t.meta["state"] for t in legend_traces(fig)} == set(STATE_ORDER)
    assert all(t.meta["role"] == "state" for t in legend_traces(fig))


def test_prose_columns_keep_a_minimum_width():
    table = build_table(entries())
    (header_row,) = [
        tr for tr in walk(table) if isinstance(tr, html.Tr) and getattr(tr, "id", None) is None
    ]
    widths = {th.children: getattr(th, "style", None) for th in header_row.children}
    for column in ("Trigger", "Notes"):
        assert widths[column] == {"minWidth": layer.TEXT_COLUMN_MIN_WIDTH}
    assert all(widths[c] is None for c in layer.TABLE_HEADERS if c not in ("Trigger", "Notes"))
    (row,) = [
        tr for tr in walk(table) if getattr(tr, "id", None) == "activation-example_gtm_cerf_aa"
    ]
    cells = dict(zip(layer.TABLE_HEADERS, row.children, strict=True))
    assert cells["Trigger"].style == {"minWidth": layer.TEXT_COLUMN_MIN_WIDTH}
    assert cells["Notes"].style == {"minWidth": layer.TEXT_COLUMN_MIN_WIDTH}
    assert getattr(cells["Country"], "style", None) is None
    assert layer.TEXT_COLUMN_MIN_WIDTH.endswith("rem")
    assert table.className == "table-wrap" and table.children.id == "activations-table"


def test_unplaceable_code_count_is_logged(caplog):
    with caplog.at_level(logging.INFO, logger="src.layers.activations_map"):
        build_figure(entries())
    messages = [r.getMessage() for r in caplog.records]
    assert any(f"of {len(pycountry.countries)} ISO-3 codes" in m for m in messages)


def test_plotly_country_table_is_read_from_the_bundle():
    codes = layer.plotly_country_codes()
    assert len(codes) >= 200
    assert {"GTM", "HND", "SLV", "NIC"} <= codes


def test_table_links_and_discrepancy_note():
    with_note = {**example_entry(), "discrepancies": [discrepancy()]}
    rendered = str(build_table([with_note, no_activation_entry()]))
    assert example_entry()["source_url"] in rendered
    assert example_entry()["wayback_url"] in rendered
    assert "Companion documents differ." in rendered
    assert "Amount released, companion document: 900,000" in rendered
    assert "https://example.org/companion" in rendered
    assert "activation-example_gtm_cerf_aa" in rendered
    assert "activation-example_nic_cerf_aa" in rendered
    assert layer.has_discrepancies([with_note]) and not layer.has_discrepancies(entries())

    plain = str(build_table([{**no_activation_entry(), "wayback_url": None}]))
    assert "Companion documents differ." not in plain
    assert "none" in plain


def test_panel_holds_graph_and_table():
    rendered = str(build_panel(entries()))
    assert "activations-map" in rendered
    assert "activations-table" in rendered


def test_explainer_contract():
    ex = explainer()
    assert isinstance(ex, Explainer)
    assert ex.licence_label == "per document, linked"
    for agency in ("OCHA", "WFP", "FAO"):
        assert agency in ex.source_name
    assert ex.source_url.startswith("https://cerf.un.org")
    assert f"]({layer.CERF_ANTICIPATORY_ACTION_URL})" in ex.how
    assert ex.how.count("](http") == 1, "the how block carries exactly one link"
    assert ex.what.endswith("both are shown as they stand.")
    assert ex.why.startswith("Because El Niño is forecast months before the rainfall")
    assert "where a framework existed without activating" in ex.why
    assert ex.why.endswith("whether the forecast hazard later arrived or failed to.")
    assert ex.not_shown.startswith("An activation records money released on a forecast trigger.")
    assert "lie outside this panel" in ex.not_shown
    for text in (ex.title, ex.what, ex.how, ex.why, ex.not_shown, ex.source_name):
        assert "—" not in text, "no em-dashes in public copy"
        assert ";" not in text, "no semicolons in public copy"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1_000_000, "1,000,000"), (2.5, "2.50"), (3.0, "3"), ("USD 2.4 million", "USD 2.4 million")],
)
def test_format_figure(value, expected):
    assert layer.format_figure(value) == expected
