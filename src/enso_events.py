"""ENSO event classification following the NOAA CPC convention.

NOAA defines El Niño (La Niña) as five or more consecutive overlapping
three-month seasons with the index at or above +0.5 C (at or below
-0.5 C). This module applies that rule to an index frame in the tidy
contract of ``src/schema.py``, for the ONI, the RONI or any other single
series of seasonal values in degrees C.

Threshold on one-decimal values
-------------------------------
CPC colours its ONI and RONI tables on the one-decimal values it
displays, while the files carry two decimals. To reproduce the published
episodes, each value is rounded to one decimal as ``floor(10x + 0.5) / 10``
(``threshold_value``) before it is compared with the threshold. Checked
against the CPC tables read on 7 September 2026, that rule reproduces the
displayed ONI (ERSSTv6) cells in 916 of 919 cases and the RONI cells in
912 of 919, and reproduces every coloured ONI episode and 46 of the 47
RONI episodes. The exception is the RONI La Niña that CPC colours from
ASO 1983 to MJJ 1984: FMA 1984 is -0.45 in the file and -0.5 in the
table, so this rule ends that event at JFM 1984 and drops the three
seasons that follow. Rounding half away from zero was tested and
rejected: it reproduced fewer cells (868 and 871) and opened other
episode mismatches. Frame values and event peaks keep the file's two
decimals; only the comparison uses the rounded value.

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
as the tuple of NOAA season labels the event spans so far.

A run at or beyond the threshold that reaches the last available season
has not ended, so its ``end`` is ``None`` whatever its length. If such a
run is shorter than five seasons it is reported as a provisional event
(``provisional`` True) rather than dropped; a run that reaches the last
season with five or more seasons is an event with ``provisional`` False
and ``end`` ``None``. Runs shorter than five seasons that do not reach
the last season are not events.

``peak`` is the value of largest magnitude within the event, in the
file's two decimals, and ``peak_date`` its season. ``peak_category``
applies the bands of Jan Null (Golden Gate Weather Services, "El Niño
and La Niña Years and Intensities", ggweather.com/enso/oni.htm) to the
one-decimal magnitude of the peak: weak 0.5 to 0.9, moderate 1.0 to 1.4,
strong 1.5 to 1.9, very strong 2.0 and above. Null applies the bands to
the ONI and requires a band to hold for three consecutive seasons; this
module describes the peak season alone.

``classify_enso_events`` returns the same events as one row each, dates
as ISO strings, with these columns:

phase          "el_nino" or "la_nina"
onset          ISO date of the first qualifying season
end            ISO date of the last qualifying season, or None while the
               run reaches the last available season
onset_season   NOAA-style label, e.g. "MJJ 1997"
end_season     NOAA-style label of the last qualifying season, or None
               when ``end`` is None
peak           signed index value of largest magnitude within the event
peak_date      ISO date of the season carrying the peak
n_seasons      number of seasons observed in the event so far
provisional    True for a run shorter than five seasons that reaches the
               last available season
peak_category  "weak", "moderate", "strong" or "very_strong"
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal

import pandas as pd

from src.schema import validate_frame

THRESHOLD_C = 0.5
MIN_SEASONS = 5

# Lower bounds of Jan Null's intensity bands on the one-decimal magnitude.
CATEGORY_BOUNDS: tuple[tuple[float, str], ...] = (
    (2.0, "very_strong"),
    (1.5, "strong"),
    (1.0, "moderate"),
    (0.5, "weak"),
)

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
    "provisional",
    "peak_category",
]


@dataclass(frozen=True)
class Event:
    """One El Niño or La Niña event, or a provisional run.

    ``end`` is ``None`` for a run that reaches the last available season,
    because the data do not show it ending. ``provisional`` is True only
    when such a run is still shorter than five seasons. ``peak_category``
    is the Jan Null band of the peak's one-decimal magnitude.
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


def threshold_value(value: float) -> float:
    """The one-decimal value compared with the threshold: floor(10x + 0.5) / 10.

    This is the rounding that reproduces the values in the CPC tables, so
    0.45 becomes 0.5 and -0.45 becomes -0.4. The value is taken through
    its decimal representation so that two-decimal file values round
    exactly.
    """
    scaled = Decimal(repr(float(value))) * 10 + Decimal("0.5")
    return float(scaled.to_integral_value(rounding=ROUND_FLOOR) / 10)


def peak_category(peak: float) -> str:
    """Jan Null's intensity band for the one-decimal magnitude of ``peak``."""
    magnitude = abs(threshold_value(peak))
    for bound, name in CATEGORY_BOUNDS:
        if magnitude >= bound:
            return name
    return ""


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
    rounded = [threshold_value(v) for v in values]

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
        s = sign(rounded[start])
        if s == 0:
            start += 1
            continue
        stop = start
        while stop + 1 < n and sign(rounded[stop + 1]) == s:
            stop += 1
        length = stop - start + 1
        reaches_end = stop == n - 1
        if length >= min_seasons or reaches_end:
            run = values[start : stop + 1]
            peak_offset = max(range(length), key=lambda i: abs(run[i]))
            peak = float(run[peak_offset])
            events.append(
                Event(
                    phase="el_nino" if s > 0 else "la_nina",
                    onset=dates[start],
                    end=None if reaches_end else dates[stop],
                    seasons=tuple(season_label(d) for d in dates[start : stop + 1]),
                    peak=peak,
                    peak_date=dates[start + peak_offset],
                    provisional=length < min_seasons,
                    peak_category=peak_category(peak),
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
        "end_season": None if event.end is None else event.seasons[-1],
        "peak": event.peak,
        "peak_date": event.peak_date.isoformat(),
        "n_seasons": len(event.seasons),
        "provisional": event.provisional,
        "peak_category": event.peak_category,
    }


def enso_event_records(
    index_frame: pd.DataFrame,
    threshold: float = THRESHOLD_C,
    min_seasons: int = MIN_SEASONS,
) -> list[Event]:
    """Return one ``Event`` per El Niño or La Niña event in ``index_frame``.

    ``index_frame`` is a tidy contract frame for exactly one series with
    one row per season: ``date`` the ISO string of the season's centre
    month and ``value`` the index in degrees C. The threshold is applied
    to ``threshold_value`` of each value. Runs shorter than
    ``min_seasons`` are not events unless they reach the last season, in
    which case they are provisional events.
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
    when no run meets the criterion.
    """
    events = enso_event_records(index_frame, threshold, min_seasons)
    rows = [_row(event) for event in events]
    frame = pd.DataFrame(rows, columns=EVENT_COLUMNS)
    # Keep None (not NaN) for an event whose end the data do not show.
    for column in ("end", "end_season"):
        frame[column] = pd.Series([row[column] for row in rows], dtype=object)
    return frame
