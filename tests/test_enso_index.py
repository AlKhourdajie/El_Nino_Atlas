"""Tests for the ENSO index panel in src/layers/enso_index.py."""

from dataclasses import replace
from datetime import date

import plotly.graph_objects as go
import pytest
from dash import html

from src import theme
from src.enso_events import enso_event_records
from src.layers import enso_index
from src.layout.captions import TEMPERATURE_CONTRIBUTION
from src.layout.explainer import render_explainer
from tests.support import index_frame, index_values, walk

LAST_SEASON = "2026-07-01"
X_END = "2026-09-01"  # the last season ends two months after its centre


@pytest.fixture(scope="module")
def frame():
    return index_frame()


@pytest.fixture(scope="module")
def events(frame):
    return enso_event_records(frame[frame["series_id"] == "RONI"])


@pytest.fixture(scope="module")
def figure(frame, events):
    return enso_index.build_figure(frame, events)


def rects(fig: go.Figure) -> list:
    return [shape for shape in fig.layout.shapes if shape.type == "rect"]


def test_synthetic_events_are_as_described(events):
    assert [(e.phase, e.onset, e.end) for e in events] == [
        ("el_nino", date(1997, 6, 1), date(1998, 5, 1)),
        ("la_nina", date(2010, 7, 1), date(2011, 2, 1)),
        ("el_nino", date(2026, 3, 1), date(2026, 7, 1)),
    ]


def test_roni_is_primary_and_oni_is_muted(figure, frame):
    by_name = {trace.name: trace for trace in figure.data}
    assert set(by_name) == {"RONI", "ONI"}
    roni, oni = by_name["RONI"], by_name["ONI"]
    assert roni.line.width > oni.line.width
    assert roni.line.color == theme.INDEX_LINE_COLOURS["primary"]
    assert oni.line.color == theme.INDEX_LINE_COLOURS["secondary"]
    assert roni.legendrank < oni.legendrank
    assert list(roni.y) == index_values()["RONI"]
    assert list(oni.y) == index_values()["ONI"]
    assert roni.x[0] == "1990-01-01" and roni.x[-1] == LAST_SEASON


def test_values_are_in_degrees_c(figure):
    assert "°C" in figure.layout.yaxis.title.text
    for trace in figure.data:
        assert "°C" in trace.hovertemplate
    with pytest.raises(ValueError, match="must be in 'degC'"):
        enso_index.build_figure(index_frame(unit="K"), [])


def test_hover_names_the_season(figure):
    roni = next(trace for trace in figure.data if trace.name == "RONI")
    assert roni.customdata[0] == "DJF 1990"
    assert roni.customdata[-1] == "JJA 2026"


def test_missing_series_raises(frame):
    without_oni = frame[frame["series_id"] != "ONI"]
    with pytest.raises(ValueError, match="no rows with series_id 'ONI'"):
        enso_index.build_figure(without_oni, [])


def test_events_are_shaded_over_their_seasons(figure, events):
    shapes = rects(figure)
    assert len(shapes) == len(events) == 3
    assert [(s.x0, s.x1) for s in shapes] == [
        ("1997-05-01", "1998-07-01"),
        ("2010-06-01", "2011-04-01"),
        ("2026-02-01", "2026-09-01"),
    ]
    for shape, event in zip(shapes, events, strict=True):
        assert shape.legendgroup == event.phase
        assert shape.name == theme.PHASE_LABELS[event.phase]
        assert shape.fillcolor == theme.rgba(
            theme.PHASE_COLOURS[event.phase], theme.PHASE_OPACITY[event.phase]
        )
        assert shape.line.width == 0
        assert shape.layer == "below"


def test_each_phase_has_one_legend_entry(figure):
    shown = [s.legendgroup for s in rects(figure) if s.showlegend]
    assert sorted(shown) == ["el_nino", "la_nina"]


def test_la_nina_is_shaded_more_lightly_than_el_nino():
    assert theme.PHASE_OPACITY["la_nina"] < theme.PHASE_OPACITY["el_nino"]


def test_phase_colours_are_not_state_colours():
    for colour in theme.PHASE_COLOURS.values():
        assert colour not in theme.STATE_COLOURS.values()


def test_provisional_event_has_dashed_outline_and_label(frame, events):
    provisional = replace(events[-1], end=None, provisional=True)
    fig = enso_index.build_figure(frame, [provisional])
    (shape,) = rects(fig)
    assert (shape.x0, shape.x1) == ("2026-02-01", X_END)
    assert shape.line.dash == "dash"
    assert shape.line.width > 0
    assert shape.label.text == "provisional"


def test_unknown_phase_raises(frame, events):
    with pytest.raises(ValueError, match="unknown event phase 'neutral'"):
        enso_index.build_figure(frame, [replace(events[0], phase="neutral")])


def test_shading_can_be_limited_to_one_phase(events):
    fig = go.Figure()
    enso_index.add_event_shading(fig, events, until=date(2026, 9, 1), phases=("el_nino",))
    assert [s.legendgroup for s in rects(fig)] == ["el_nino", "el_nino"]


def test_threshold_lines_at_half_a_degree(figure):
    lines = [shape for shape in figure.layout.shapes if shape.type == "line"]
    assert sorted(shape.y0 for shape in lines) == [-0.5, 0.5]


def test_range_buttons_and_default_window(figure):
    buttons = figure.layout.xaxis.rangeselector.buttons
    assert [b.label for b in buttons] == ["From 1950", "30 years", "5 years"]
    assert buttons[0].step == "all"
    assert (buttons[1].count, buttons[1].step, buttons[1].stepmode) == (30, "year", "backward")
    assert (buttons[2].count, buttons[2].step, buttons[2].stepmode) == (5, "year", "backward")
    assert figure.layout.xaxis.range == ("1996-09-01", X_END)
    assert figure.layout.xaxis.type == "date"


def test_figure_sets_no_width(figure):
    assert figure.layout.width is None


def test_explainer_contract():
    explainer = enso_index.explainer()
    assert "RONI" in explainer.title and "ONI" in explainer.title
    assert "RONI" in explainer.what and "ONI" in explainer.what
    assert "shading" in explainer.what.lower()
    assert "minus the average anomaly of the global tropics" in explainer.how
    assert "five consecutive overlapping three-month seasons" in explainer.how
    assert explainer.how.count("](") == 1
    assert f"({enso_index.RONI_URL})" in explainer.how
    assert "neither a weekly value nor an impact" in explainer.not_shown
    assert explainer.source_name == "NOAA Climate Prediction Center"
    assert explainer.source_url == enso_index.SOURCE_URL
    assert explainer.licence_label == "US public domain"
    assert explainer.captions == (TEMPERATURE_CONTRIBUTION,)


def test_explainer_how_block_links_the_roni_page():
    card = render_explainer(enso_index.explainer())
    anchors = [c for c in walk(card) if isinstance(c, html.A)]
    assert enso_index.RONI_URL in [a.href for a in anchors]
    assert "](" not in str(card)


def test_public_copy_follows_the_rules():
    explainer = enso_index.explainer()
    for text in (
        explainer.title,
        explainer.what,
        explainer.how,
        explainer.why,
        explainer.not_shown,
    ):
        assert "—" not in text
        assert " very " not in text
