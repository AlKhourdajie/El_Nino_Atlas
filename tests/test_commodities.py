"""Tests for the commodity price panel in src/layers/commodities.py."""

from dataclasses import replace

import pytest
from dash import html

from src import theme
from src.enso_events import enso_event_records
from src.layers import commodities
from src.layout.captions import PRICE_TRANSMISSION
from src.layout.explainer import render_explainer
from tests.support import index_frame, price_frame, walk

START = "2009-01-01"
MONTHS = 211  # January 2009 to July 2026
BASE_INDEX = 12  # January 2010
UNITS = {
    "COFFEE_ARABIC": "USD/kg",
    "COFFEE_ROBUS": "USD/kg",
    "COCOA": "USD/kg",
    "SUGAR_WLD": "USD/kg",
    "RICE_05": "USD/mt",
}
LEVELS = {
    "COFFEE_ARABIC": 3.0,
    "COFFEE_ROBUS": 1.5,
    "COCOA": 2.5,
    "SUGAR_WLD": 0.4,
    "RICE_05": 500.0,
}


def values(level: float) -> list[float]:
    return [level * (1 + 0.01 * k) for k in range(MONTHS)]


def prices() -> dict[str, tuple[str, list[float]]]:
    return {sid: (UNITS[sid], values(LEVELS[sid])) for sid in UNITS}


@pytest.fixture(scope="module")
def frame():
    return price_frame(prices(), start=START)


@pytest.fixture(scope="module")
def events():
    index = index_frame()
    return enso_event_records(index[index["series_id"] == "RONI"])


@pytest.fixture(scope="module")
def figure(frame, events):
    return commodities.build_figure(frame, events)


def rects(fig) -> list:
    return [shape for shape in fig.layout.shapes if shape.type == "rect"]


def test_five_default_series_in_legend_order(figure):
    assert [trace.name for trace in figure.data] == [
        "Coffee, arabica",
        "Coffee, robusta",
        "Cocoa",
        "Sugar, world",
        "Rice, Thai 5%",
    ]
    assert [trace.legendrank for trace in figure.data] == [1, 2, 3, 4, 5]


def test_series_are_rebased_to_january_2010(figure):
    for trace in figure.data:
        assert trace.x[BASE_INDEX] == "2010-01-01"
        assert trace.y[BASE_INDEX] == 100.0
        expected = (1 + 0.01 * (MONTHS - 1)) / (1 + 0.01 * BASE_INDEX) * 100
        assert trace.y[-1] == pytest.approx(expected)
    assert "January 2010 = 100" in figure.layout.yaxis.title.text


def test_hover_carries_nominal_price_and_unit(figure):
    by_name = {trace.name: trace for trace in figure.data}
    rice = by_name["Rice, Thai 5%"]
    assert list(rice.customdata[BASE_INDEX]) == [500.0 * 1.12, "USD/mt"]
    coffee = by_name["Coffee, arabica"]
    assert list(coffee.customdata[0]) == [3.0, "USD/kg"]
    for trace in figure.data:
        assert "%{customdata[0]" in trace.hovertemplate
        assert "%{customdata[1]}" in trace.hovertemplate


def test_missing_series_raises(frame, events):
    without_rice = frame[frame["series_id"] != "RICE_05"]
    with pytest.raises(ValueError, match="no rows with series_id 'RICE_05'"):
        commodities.build_figure(without_rice, events)


def test_missing_base_month_raises(events):
    late = price_frame(prices(), start="2011-01-01")
    with pytest.raises(ValueError, match="no value for 2010-01-01, the base month"):
        commodities.build_figure(late, events)


def test_mixed_units_in_one_series_raise(frame, events):
    mixed = frame.copy()
    mixed.loc[mixed.index[-1], "unit"] = "USD/lb"
    with pytest.raises(ValueError, match="mixes units"):
        commodities.build_figure(mixed, events)


def test_el_nino_seasons_are_shaded_as_in_the_index_panel(figure, events):
    shapes = rects(figure)
    el_nino = [event for event in events if event.phase == "el_nino"]
    assert len(shapes) == len(el_nino) == 2
    assert all(shape.legendgroup == "el_nino" for shape in shapes)
    assert [(s.x0, s.x1) for s in shapes] == [
        ("1997-05-01", "1998-07-01"),
        ("2026-02-01", "2026-09-01"),
    ]
    assert [s.showlegend for s in shapes] == [True, False]
    assert shapes[0].name == theme.PHASE_LABELS["el_nino"]
    assert shapes[0].fillcolor == theme.rgba(
        theme.PHASE_COLOURS["el_nino"], theme.PHASE_OPACITY["el_nino"]
    )


def test_unended_event_is_shaded_to_the_end_of_the_frame(frame, events):
    fig = commodities.build_figure(frame, [replace(events[-1], end=None)])
    (shape,) = rects(fig)
    assert shape.x1 == "2026-08-01"


def test_axis_spans_the_price_record_only(figure):
    # The 1997-98 event is shaded, yet it must not pull the axis back to 1997.
    assert figure.layout.xaxis.range == ("2009-01-01", "2026-08-01")


def test_figure_sets_no_width(figure):
    assert figure.layout.width is None


def test_figure_layout_suits_narrow_screens(figure):
    assert figure.layout.autosize is True
    assert figure.layout.legend.orientation == "h"
    assert figure.layout.legend.y < 0
    margin = figure.layout.margin
    assert max(margin.l, margin.r, margin.t, margin.b) <= 48


def test_explainer_contract():
    explainer = commodities.explainer()
    assert "Pink Sheet" in explainer.title
    assert "January 2010" in explainer.what
    assert "nominal price" in explainer.what
    assert "Pink Sheet" in explainer.how
    assert explainer.how.count("](") == 1
    assert f"({commodities.SOURCE_URL})" in explainer.how
    assert "descriptive" in explainer.not_shown
    assert "many drivers" in explainer.not_shown
    assert explainer.source_url == commodities.SOURCE_URL
    assert explainer.licence_label == "CC BY 4.0"
    assert explainer.captions == (commodities.REBASE_CAPTION, PRICE_TRANSMISSION)
    assert "nominal US dollars" in commodities.REBASE_CAPTION


def test_explainer_how_block_links_the_world_bank_page():
    card = render_explainer(commodities.explainer())
    anchors = [c for c in walk(card) if isinstance(c, html.A)]
    assert commodities.SOURCE_URL in [a.href for a in anchors]
    assert "](" not in str(card)


def test_public_copy_follows_the_rules():
    explainer = commodities.explainer()
    for text in (
        explainer.title,
        explainer.what,
        explainer.how,
        explainer.why,
        explainer.not_shown,
        commodities.REBASE_CAPTION,
    ):
        assert "—" not in text
        assert " very " not in text
