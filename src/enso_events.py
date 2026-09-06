"""ENSO event classification following the NOAA CPC convention.

NOAA defines El Niño (La Niña) as five or more consecutive overlapping
three-month seasons with the Oceanic Niño Index at or above +0.5 C (at or
below -0.5 C). This module applies that rule to an ONI frame in the tidy
contract of ``src/schema.py`` and returns one row per event.

Input
-----
A validated frame with ``series_id == "oni"`` and one row per season.
``date`` is the first day of the season's centre month, so the season
DJF 1998 (Dec 1997 to Feb 1998) is dated 1998-01-01. Seasons must be
contiguous; a gap raises ``ValueError`` rather than being bridged.

Output columns
--------------
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


def season_label(centre: date) -> str:
    """NOAA season label for a centre month, e.g. 1998-01 -> 'DJF 1998'."""
    return f"{_SEASONS[centre.month - 1]} {centre.year}"


def _months_apart(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def _prepare(oni_frame: pd.DataFrame) -> pd.DataFrame:
    validate_frame(oni_frame)
    oni = oni_frame[oni_frame["series_id"] == "oni"]
    if oni.empty:
        raise ValueError("frame contains no rows with series_id 'oni'")
    if oni["region"].nunique() != 1:
        raise ValueError(f"expected a single region, got {sorted(oni['region'].unique())}")
    oni = oni.assign(_d=oni["date"].map(date.fromisoformat)).sort_values("_d")
    dates = oni["_d"].tolist()
    for prev, nxt in zip(dates, dates[1:], strict=False):
        if _months_apart(prev, nxt) != 1:
            raise ValueError(f"ONI seasons are not contiguous between {prev} and {nxt}")
    return oni.reset_index(drop=True)


def classify_enso_events(
    oni_frame: pd.DataFrame,
    threshold: float = THRESHOLD_C,
    min_seasons: int = MIN_SEASONS,
) -> pd.DataFrame:
    """Return one row per El Niño or La Niña event in ``oni_frame``.

    An empty frame with the event columns is returned when no run meets
    the criterion. Runs shorter than ``min_seasons`` are not events.
    """
    oni = _prepare(oni_frame)
    values = oni["value"].tolist()
    dates = oni["_d"].tolist()

    def sign(v: float) -> int:
        if v >= threshold:
            return 1
        if v <= -threshold:
            return -1
        return 0

    events: list[dict] = []
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
                {
                    "phase": "el_nino" if s > 0 else "la_nina",
                    "onset": dates[start].isoformat(),
                    "end": dates[stop].isoformat(),
                    "onset_season": season_label(dates[start]),
                    "end_season": season_label(dates[stop]),
                    "peak": float(run[peak_offset]),
                    "peak_date": dates[start + peak_offset].isoformat(),
                    "n_seasons": length,
                }
            )
        start = stop + 1

    return pd.DataFrame(events, columns=EVENT_COLUMNS)
