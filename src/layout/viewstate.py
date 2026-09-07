"""The view state the page keeps in its URL.

The time-series panels share one time range, one phase-band toggle and,
per figure, the set of series left visible after legend clicks. The
browser keeps that state in the query string through ``dcc.Location``,
so that any view can be shared and reloads identically. This module is
the Python side of the codec; ``assets/atlas.js`` carries the same
grammar (``tests/test_viewstate.py`` checks that the two agree on the
keys) and the CSV download writes the current URL into its provenance
header.

Grammar
-------
``range=YYYY-MM-DD,YYYY-MM-DD``   the shared x-axis window; absent when
                                   each figure shows its authored default
``range=all``                      every figure shows its whole record
``bands=off``                      phase bands hidden; absent when shown
``index=RONI|ONI``                 series visible in the index figure,
                                   names joined by ``|``; absent when all
``prices=Cocoa|Sugar, world``      the same for the commodity figure

Unknown keys are ignored. A malformed range is dropped rather than
guessed.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from urllib.parse import parse_qsl, quote, unquote

RANGE_KEY = "range"
RANGE_ALL = "all"
BANDS_KEY = "bands"
SERIES_KEYS: dict[str, str] = {"index": "graph-index", "prices": "graph-commodities"}
SERIES_SEPARATOR = "|"

_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def default_state() -> dict[str, Any]:
    return {"range": None, "bands": True, "series": {}}


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


def parse(search: str) -> dict[str, Any]:
    """The view state encoded in ``search`` (with or without the leading ``?``)."""
    state = default_state()
    query = search[1:] if search.startswith("?") else search
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key == RANGE_KEY:
            parts = value.split(",")
            if value == RANGE_ALL:
                state["range"] = RANGE_ALL
            elif len(parts) == 2:
                start, end = _iso_date(parts[0]), _iso_date(parts[1])
                if start and end and start < end:
                    state["range"] = [start, end]
        elif key == BANDS_KEY:
            state["bands"] = value != "off"
        elif key in SERIES_KEYS:
            # A browser may percent-encode the separator; no series name holds one.
            joined = value.replace("%7C", SERIES_SEPARATOR).replace("%7c", SERIES_SEPARATOR)
            names = [unquote(n) for n in joined.split(SERIES_SEPARATOR) if n]
            if names:
                state["series"][key] = names
    return state


def encode(state: dict[str, Any]) -> str:
    """``state`` as a query string starting with ``?``, or ``""`` for the default."""
    parts: list[str] = []
    window = state.get("range")
    if window == RANGE_ALL:
        parts.append(f"{RANGE_KEY}={RANGE_ALL}")
    elif window:
        parts.append(f"{RANGE_KEY}={window[0]},{window[1]}")
    if state.get("bands") is False:
        parts.append(f"{BANDS_KEY}=off")
    for key in SERIES_KEYS:
        names = (state.get("series") or {}).get(key)
        if names:
            joined = SERIES_SEPARATOR.join(quote(n, safe="") for n in names)
            parts.append(f"{key}={joined}")
    return "?" + "&".join(parts) if parts else ""


def permalink(base_url: str, search: str) -> str:
    """``base_url`` without any query, plus ``search``."""
    root = base_url.split("?", 1)[0].split("#", 1)[0]
    return root + (search if search.startswith("?") or not search else "?" + search)
