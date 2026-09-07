"""Tests for the URL view state codec in src/layout/viewstate.py.

The browser keeps the shared time range, the phase-band toggle and the
isolated series in the query string; ``assets/atlas.js`` carries the same
grammar. These tests round-trip the Python codec and check that the
script names the same keys.
"""

import re
from pathlib import Path

import pytest

from src.layout import viewstate

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "assets" / "atlas.js"


def test_default_state_encodes_to_nothing():
    assert viewstate.encode(viewstate.default_state()) == ""
    assert viewstate.parse("") == viewstate.default_state()
    assert viewstate.parse("?") == viewstate.default_state()


@pytest.mark.parametrize(
    "state",
    [
        {"range": ["1996-09-01", "2026-09-01"], "bands": True, "series": {}},
        {"range": "all", "bands": True, "series": {}},
        {"range": None, "bands": False, "series": {}},
        {"range": None, "bands": True, "series": {"index": ["RONI"]}},
        {
            "range": ["2014-10-01", "2017-06-01"],
            "bands": False,
            "series": {"index": ["ONI"], "prices": ["Cocoa", "Sugar, world", "Rice, Thai 5%"]},
        },
    ],
)
def test_round_trip(state):
    search = viewstate.encode(state)
    assert search.startswith("?")
    assert viewstate.parse(search) == state
    assert viewstate.encode(viewstate.parse(search)) == search


def test_series_names_survive_commas_and_percent_signs():
    search = viewstate.encode(
        {"range": None, "bands": True, "series": {"prices": ["Rice, Thai 5%"]}}
    )
    assert search == "?prices=Rice%2C%20Thai%205%25"
    assert viewstate.parse(search)["series"] == {"prices": ["Rice, Thai 5%"]}


def test_encoded_separator_is_accepted():
    state = viewstate.parse("?prices=Cocoa%7CSugar%2C%20world")
    assert state["series"] == {"prices": ["Cocoa", "Sugar, world"]}


def test_plotly_datetimes_are_cut_to_the_day():
    state = viewstate.parse("?range=1996-09-01 12:34:56.789,2026-09-01 00:00:00")
    assert state["range"] == ["1996-09-01", "2026-09-01"]


@pytest.mark.parametrize(
    "search",
    [
        "?range=2026-01-01",
        "?range=b,a",
        "?range=2026-13-01,2027-01-01",
        "?range=2027-01-01,2026-01-01",
    ],
)
def test_malformed_ranges_are_dropped(search):
    assert viewstate.parse(search)["range"] is None


def test_unknown_keys_are_ignored():
    assert viewstate.parse("?utm_source=x&bands=on") == viewstate.default_state()


def test_permalink_replaces_the_query():
    base = "https://el-nino-atlas.onrender.com/?old=1#panel-index"
    assert (
        viewstate.permalink(base, "?bands=off") == "https://el-nino-atlas.onrender.com/?bands=off"
    )
    assert viewstate.permalink(base, "") == "https://el-nino-atlas.onrender.com/"


def test_script_uses_the_same_grammar():
    script = SCRIPT.read_text(encoding="utf-8")
    assert f'var RANGE_KEY = "{viewstate.RANGE_KEY}";' in script
    assert f'var RANGE_ALL = "{viewstate.RANGE_ALL}";' in script
    assert f'var BANDS_KEY = "{viewstate.BANDS_KEY}";' in script
    keys = re.search(r"var SERIES_KEYS = \[([^\]]+)\];", script).group(1)
    assert [k.strip().strip('"') for k in keys.split(",")] == list(viewstate.SERIES_KEYS)
    assert f'var SERIES_SEPARATOR = "{viewstate.SERIES_SEPARATOR}";' in script
    for key, graph_id in viewstate.SERIES_KEYS.items():
        assert f'{key}: "{graph_id}"' in script
