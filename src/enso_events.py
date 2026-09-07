"""ENSO event classification following the NOAA CPC convention.

NOAA defines El Niño (La Niña) as five or more consecutive overlapping
three-month seasons with the Oceanic Niño Index at or above +0.5 C (at or
below -0.5 C). This module applies that rule to an index frame in the tidy
contract of ``src/schema.py``.

Input
-----
A validated frame for one series with one row per season. ``date`` is the
ISO string of the first day of the season's centre month and the NOAA
table year is the centre month's year, so the season DJF 1998 (Dec 1997
to Feb 1998) is dated 1998-01-01. Seasons must be contiguous; a gap
raises ``ValueError`` rather than being bridged.

Output
------
``enso_event_records`` returns one ``Event`` record per event, with
``onset``, ``end`` and ``peak_date`` as ``date`` objects and ``seasons``
as the tuple of NOAA season labels the event spans.

``classify_enso_events`` returns the same events as one row each, dates
as ISO strings, with these columns:

phase         "el_nino" or "la_nina"
onset         ISO date of the first qualifying season
end           ISO date of the last qualifying season
onset_season  NOAA-style label, e.g. "MJJ 1997"
end_season    NOAA-style label, e.g. "AMJ 1998"
peak          signed ONI value of largest magnitude within the event
peak_date     ISO date of the season carrying the peak
n_seasons     number of seasons in the event
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.schema import validate_frame

THRESHOLD_C = 0.5
MIN_SEASONS = 5

_SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]

EVENT_COLUMNS = [
    "phase",
    "onset",
    "end",
    "onset_season",
    "end_season",
    "peak",
    "peak_date",
    "n_seasons",
]


@dataclass(frozen=True)
class Event:
    """One El Niño or La Niña event.

    ``end`` is ``None`` only for an event that has not ended; the
    classification does not yet produce that. ``provisional`` and
    ``peak_category`` keep their defaults until the rules that set them
    exist.
    """

    phase: str
    onset: date
    end: date | None
    seasons: tuple[str, ...]
    peak: float
    peak_date: date
    provisional: bool = False
    peak_category: str = ""


def season_label(centre: date | str) -> str:
    """NOAA season label for a centre month, e.g. 1998-01-01 -> 'DJF 1998'.

    ``centre`` is a ``date`` or the ISO string of the centre month. The
    table year is the centre month's year: Jan DJF, Feb JFM, Mar FMA,
    Apr MAM, May AMJ, Jun MJJ, Jul JJA, Aug JAS, Sep ASO, Oct SON,
    Nov OND, Dec NDJ.
    """
    if isinstance(centre, str):
        centre = date.fromisoformat(centre)
    return f"{_SEASONS[centre.month - 1]} {centre.year}"


def _months_apart(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def _prepare(index_frame: pd.DataFrame, series_id: str) -> pd.DataFrame:
    """The rows of ``series_id`` sorted by season, with a ``_d`` date column."""
    index = index_frame[index_frame["series_id"] == series_id]
    if index.empty:
        raise ValueError(f"frame contains no rows with series_id {series_id!r}")
    if index["region"].nunique() != 1:
        raise ValueError(f"expected a single region, got {sorted(index['region'].unique())}")
    index = index.assign(_d=index["date"].map(date.fromisoformat)).sort_values("_d")
    dates = index["_d"].tolist()
    for prev, nxt in zip(dates, dates[1:], strict=False):
        if _months_apart(prev, nxt) != 1:
            raise ValueError(f"ONI seasons are not contiguous between {prev} and {nxt}")
    return index.reset_index(drop=True)


def _events(
    values: list[float],
    dates: list[date],
    threshold: float,
    min_seasons: int,
) -> list[Event]:
    """Apply the NOAA run rule to one contiguous series of seasons."""

    def sign(v: float) -> int:
        if v >= threshold:
            return 1
        if v <= -threshold:
            return -1
        return 0

    events: list[Event] = []
    start = 0
    n = len(values)
    while start < n:
        s = sign(values[start])
        if s == 0:
            start += 1
            continue
        stop = start
        while stop + 1 < n and sign(values[stop + 1]) == s:
            stop += 1
        length = stop - start + 1
        if length >= min_seasons:
            run = values[start : stop + 1]
            peak_offset = max(range(length), key=lambda i: abs(run[i]))
            events.append(
                Event(
                    phase="el_nino" if s > 0 else "la_nina",
                    onset=dates[start],
                    end=dates[stop],
                    seasons=tuple(season_label(d) for d in dates[start : stop + 1]),
                    peak=float(run[peak_offset]),
                    peak_date=dates[start + peak_offset],
                )
            )
        start = stop + 1
    return events


def _row(event: Event) -> dict:
    return {
        "phase": event.phase,
        "onset": event.onset.isoformat(),
        "end": None if event.end is None else event.end.isoformat(),
        "onset_season": event.seasons[0],
        "end_season": event.seasons[-1],
        "peak": event.peak,
        "peak_date": event.peak_date.isoformat(),
        "n_seasons": len(event.seasons),
    }


def enso_event_records(
    index_frame: pd.DataFrame,
    threshold: float = THRESHOLD_C,
    min_seasons: int = MIN_SEASONS,
) -> list[Event]:
    """Return one ``Event`` per El Niño or La Niña event in ``index_frame``.

    ``index_frame`` is a tidy contract frame for exactly one series with
    one row per season: ``date`` the ISO string of the season's centre
    month and ``value`` the index in degrees C. Runs shorter than
    ``min_seasons`` are not events.
    """
    validate_frame(index_frame)
    series_ids = sorted(set(index_frame["series_id"]))
    if len(series_ids) != 1:
        raise ValueError(f"expected a frame for exactly one series, got {series_ids}")
    index = _prepare(index_frame, series_ids[0])
    return _events(index["value"].tolist(), index["_d"].tolist(), threshold, min_seasons)


def classify_enso_events(
    index_frame: pd.DataFrame,
    threshold: float = THRESHOLD_C,
    min_seasons: int = MIN_SEASONS,
) -> pd.DataFrame:
    """Return one row per El Niño or La Niña event in ``index_frame``.

    ``index_frame`` is a tidy contract frame for exactly one series, as for
    ``enso_event_records``; the series id may be ``ONI``, ``RONI`` or any
    other single id. An empty frame with the event columns is returned
    when no run meets the criterion. Runs shorter than ``min_seasons`` are
    not events.
    """
    events = enso_event_records(index_frame, threshold, min_seasons)
    return pd.DataFrame([_row(event) for event in events], columns=EVENT_COLUMNS)
