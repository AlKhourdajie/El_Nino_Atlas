"""Tests for the URL view state codec in src/layout/viewstate.py.

Each time-series panel keeps its own time range, phase-band toggle and
isolated series in the query string; ``assets/atlas.js`` carries the
same grammar. These tests round-trip the Python codec and check that the
script names the same keys.
"""

import re
from pathlib import Path

import pytest

from src.layout import viewstate

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "assets" / "atlas.js"


def state(**graphs) -> dict:
    """A state with the given per-graph overrides, defaults elsewhere."""
    result = viewstate.default_state()
    for key, values in graphs.items():
        result[key].update(values)
    return result


def test_default_state_encodes_to_nothing():
    assert viewstate.encode(viewstate.default_state()) == ""
    assert viewstate.parse("") == viewstate.default_state()
    assert viewstate.parse("?") == viewstate.default_state()
    assert set(viewstate.default_state()) == {"index", "prices"}


@pytest.mark.parametrize(
    "given",
    [
        state(index={"range": ["1996-09-01", "2026-09-01"]}),
        state(prices={"range": "all"}),
        state(index={"bands": False}, prices={"bands": False}),
        state(index={"series": ["RONI"]}),
        state(
            index={"range": ["2014-10-01", "2017-06-01"], "bands": False, "series": ["ONI"]},
            prices={"range": "all", "series": ["Cocoa", "Sugar, world", "Rice, Thai 5%"]},
        ),
    ],
)
def test_round_trip(given):
    search = viewstate.encode(given)
    assert search.startswith("?")
    assert viewstate.parse(search) == given
    assert viewstate.encode(viewstate.parse(search)) == search


def test_graphs_are_independent():
    search = viewstate.encode(state(index={"range": ["2000-01-01", "2003-01-01"]}))
    assert search == "?index_range=2000-01-01,2003-01-01"
    parsed = viewstate.parse(search)
    assert parsed["prices"] == viewstate.default_graph_state()


def test_series_names_survive_commas_and_percent_signs():
    search = viewstate.encode(state(prices={"series": ["Rice, Thai 5%"]}))
    assert search == "?prices=Rice%2C%20Thai%205%25"
    assert viewstate.parse(search)["prices"]["series"] == ["Rice, Thai 5%"]


def test_encoded_separator_is_accepted():
    parsed = viewstate.parse("?prices=Cocoa%7CSugar%2C%20world")
    assert parsed["prices"]["series"] == ["Cocoa", "Sugar, world"]


def test_plotly_datetimes_are_cut_to_the_day():
    parsed = viewstate.parse("?index_range=1996-09-01 12:34:56.789,2026-09-01 00:00:00")
    assert parsed["index"]["range"] == ["1996-09-01", "2026-09-01"]


@pytest.mark.parametrize(
    "search",
    [
        "?index_range=2026-01-01",
        "?index_range=b,a",
        "?prices_range=2026-13-01,2027-01-01",
        "?prices_range=2027-01-01,2026-01-01",
    ],
)
def test_malformed_ranges_are_dropped(search):
    parsed = viewstate.parse(search)
    assert parsed["index"]["range"] is None and parsed["prices"]["range"] is None


def test_unknown_and_legacy_keys_are_ignored():
    assert viewstate.parse("?utm_source=x&index_bands=on&range=all&bands=off") == (
        viewstate.default_state()
    )


def test_permalink_replaces_the_query():
    base = "https://el-nino-atlas.onrender.com/?old=1#panel-index"
    assert (
        viewstate.permalink(base, "?index_bands=off")
        == "https://el-nino-atlas.onrender.com/?index_bands=off"
    )
    assert viewstate.permalink(base, "") == "https://el-nino-atlas.onrender.com/"


def test_script_uses_the_same_grammar():
    script = SCRIPT.read_text(encoding="utf-8")
    assert f'var RANGE_SUFFIX = "{viewstate.RANGE_SUFFIX}";' in script
    assert f'var BANDS_SUFFIX = "{viewstate.BANDS_SUFFIX}";' in script
    assert f'var RANGE_ALL = "{viewstate.RANGE_ALL}";' in script
    assert f'var SERIES_SEPARATOR = "{viewstate.SERIES_SEPARATOR}";' in script
    graphs = re.search(r"var GRAPHS = \{([^}]+)\};", script).group(1)
    for key, graph_id in viewstate.GRAPH_KEYS.items():
        assert f'{key}: "{graph_id}"' in graphs
