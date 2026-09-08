"""The view state the page keeps in its URL.

Each time-series panel has its own time range, its own phase-band toggle
and, after legend clicks, its own set of visible series. The browser
keeps that state in the query string through ``dcc.Location``, so that
any view can be shared and reloads identically. This module is the
Python side of the codec; ``assets/atlas.js`` carries the same grammar
(``tests/test_viewstate.py`` checks that the two agree on the keys) and
the CSV download writes the current URL into its provenance header.

Grammar, with ``<g>`` one of the graph keys ``index`` and ``prices``
-------------------------------------------------------------------
``<g>_range=YYYY-MM-DD,YYYY-MM-DD``   the figure's x-axis window; absent
                                       when the figure shows its authored
                                       default
``<g>_range=all``                      the figure shows its whole record
``<g>_bands=off``                      phase bands hidden; absent when shown
``<g>=RONI|ONI``                       the series left visible, names
                                       joined by ``|``; absent when all

Unknown keys are ignored. A malformed range is dropped rather than
guessed.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from urllib.parse import parse_qsl, quote, unquote

GRAPH_KEYS: dict[str, str] = {"index": "graph-index", "prices": "graph-commodities"}
RANGE_SUFFIX = "_range"
BANDS_SUFFIX = "_bands"
RANGE_ALL = "all"
SERIES_SEPARATOR = "|"

_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def default_graph_state() -> dict[str, Any]:
    return {"range": None, "bands": True, "series": None}


def default_state() -> dict[str, dict[str, Any]]:
    return {key: default_graph_state() for key in GRAPH_KEYS}


def _iso_date(text: str) -> str | None:
    """The ``YYYY-MM-DD`` prefix of a plotly date string, or ``None``."""
    match = _DATE_RE.match(text.strip())
    if not match:
        return None
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return match.group(1)


def _parse_range(value: str) -> Any:
    if value == RANGE_ALL:
        return RANGE_ALL
    parts = value.split(",")
    if len(parts) == 2:
        start, end = _iso_date(parts[0]), _iso_date(parts[1])
        if start and end and start < end:
            return [start, end]
    return None


def parse(search: str) -> dict[str, dict[str, Any]]:
    """The view state encoded in ``search`` (with or without the leading ``?``)."""
    state = default_state()
    query = search[1:] if search.startswith("?") else search
    for key, value in parse_qsl(query, keep_blank_values=True):
        for graph in GRAPH_KEYS:
            if key == graph + RANGE_SUFFIX:
                state[graph]["range"] = _parse_range(value)
            elif key == graph + BANDS_SUFFIX:
                state[graph]["bands"] = value != "off"
            elif key == graph:
                # A browser may percent-encode the separator; no series name holds one.
                joined = value.replace("%7C", SERIES_SEPARATOR).replace("%7c", SERIES_SEPARATOR)
                names = [unquote(n) for n in joined.split(SERIES_SEPARATOR) if n]
                state[graph]["series"] = names or None
    return state


def encode(state: dict[str, dict[str, Any]]) -> str:
    """``state`` as a query string starting with ``?``, or ``""`` for the default."""
    parts: list[str] = []
    for graph in GRAPH_KEYS:
        graph_state = state.get(graph) or {}
        window = graph_state.get("range")
        if window == RANGE_ALL:
            parts.append(f"{graph}{RANGE_SUFFIX}={RANGE_ALL}")
        elif window:
            parts.append(f"{graph}{RANGE_SUFFIX}={window[0]},{window[1]}")
        if graph_state.get("bands") is False:
            parts.append(f"{graph}{BANDS_SUFFIX}=off")
        names = graph_state.get("series")
        if names:
            joined = SERIES_SEPARATOR.join(quote(n, safe="") for n in names)
            parts.append(f"{graph}={joined}")
    return "?" + "&".join(parts) if parts else ""


def permalink(base_url: str, search: str) -> str:
    """``base_url`` without any query, plus ``search``."""
    root = base_url.split("?", 1)[0].split("#", 1)[0]
    return root + (search if search.startswith("?") or not search else "?" + search)
