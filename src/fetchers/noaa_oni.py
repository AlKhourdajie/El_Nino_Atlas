"""Fetcher for the NOAA Oceanic Niño Index (ONI) and Relative Oceanic Niño Index (RONI).

Provenance
----------
publisher:      NOAA Climate Prediction Center (NCEP/NWS)
dataset:        Oceanic Niño Index (ONI) and Relative Oceanic Niño Index
                (RONI): three-month running means of ERSSTv6 sea surface
                temperature anomalies in the Niño 3.4 region (5N to 5S,
                120W to 170W); the RONI subtracts the tropical mean (20N to
                20S) anomaly and is rescaled to the Niño 3.4 variance
url:            https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/
                (RONI table: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/)
files:          https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
                https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt
licence:        US Government work, public domain (licence_id LicenseRef-US-PD)
redistribution: yes
attribution:    "Source: NOAA Climate Prediction Center, Oceanic Niño Index
                (ONI) and Relative Oceanic Niño Index (RONI)"
cadence:        monthly; the CPC table pages are updated by the 5th of each month
latency:        the season ending in month M is published by the 5th of
                month M+1; values may change for up to two months after
                first posting, so the latest seasons are estimates
registry id:    noaa_oni (src/sources.yaml)

File format
-----------
``oni.ascii.txt`` has the header ``SEAS  YR   TOTAL   ANOM`` and one row
per overlapping three-month season from DJF 1950: the season label, the
table year, the three-month mean Niño 3.4 sea surface temperature
(``TOTAL``, degrees C) and its anomaly (``ANOM``, the ONI in degrees C).
``RONI.ascii.txt`` has the header ``SEAS   YR  ANOM`` and no ``TOTAL``
column. Only the anomaly enters the tidy contract, as series ``ONI`` and
``RONI`` for region ``NINO3.4`` in ``degC``. Every token is checked and
any departure from this format raises ``ValueError``.

Season-year convention
----------------------
The table year is the year of the season's centre month: ``DJF 1950``
covers December 1949 to February 1950 and ``NDJ 1950`` covers November
1950 to January 1951. The CPC tables show the same rows under the column
headings "Dec Jan Feb" to "Nov Dec Jan". ``date`` is the ISO string of the
first day of the centre month, so ``DJF 1950`` becomes ``1950-01-01`` and
``NDJ 1950`` becomes ``1950-12-01``. ``src.enso_events.season_label``
inverts this exactly (``season_label("1950-01-01") == "DJF 1950"``);
tests/test_noaa_oni.py checks the round trip for every row of both files.

Role in the atlas
-----------------
Forecast-stage layer: the headline ENSO state indicators.
"""

from __future__ import annotations

import re

import pandas as pd

from src.fetchers import Fetched, download, utc_now_iso
from src.schema import COLUMNS, registry, validate_frame

SOURCE_ID = "noaa_oni"
REGION = "NINO3.4"
UNIT = "degC"
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
RONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
ALLOWED_HOSTS = frozenset({"www.cpc.ncep.noaa.gov", "origin.cpc.ncep.noaa.gov"})

# Season label -> centre month; the table year is the centre month's year.
CENTRE_MONTH = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}

ONI_HEADER = ("SEAS", "YR", "TOTAL", "ANOM")
RONI_HEADER = ("SEAS", "YR", "ANOM")

_YEAR_RE = re.compile(r"^\d{4}$")
_VALUE_RE = re.compile(r"^-?\d+\.\d{2}$")


def _licence_id() -> str:
    return registry()[SOURCE_ID]["licence_id"]


def _parse_cpc_table(
    text: str, series_id: str, header: tuple[str, ...], retrieved_at: str | None
) -> pd.DataFrame:
    """Parse one CPC whitespace-delimited season table into the tidy contract."""
    lines = text.splitlines()
    if not lines:
        raise ValueError(f"{series_id}: the file is empty")
    if tuple(lines[0].split()) != header:
        raise ValueError(
            f"{series_id}: expected header {' '.join(header)!r}, got {lines[0].strip()!r}"
        )
    anom = header.index("ANOM")
    dates: list[str] = []
    values: list[float] = []
    previous: tuple[int, int] | None = None
    for number, line in enumerate(lines[1:], start=2):
        tokens = line.split()
        if len(tokens) != len(header):
            raise ValueError(
                f"{series_id}: line {number} has {len(tokens)} fields, expected "
                f"{len(header)}: {line!r}"
            )
        season, year = tokens[0], tokens[1]
        if season not in CENTRE_MONTH:
            raise ValueError(f"{series_id}: line {number} has unknown season {season!r}")
        if not _YEAR_RE.match(year):
            raise ValueError(f"{series_id}: line {number} has a bad year {year!r}")
        for token in tokens[2:]:
            if not _VALUE_RE.match(token):
                raise ValueError(f"{series_id}: line {number} has a bad value {token!r}")
        month = CENTRE_MONTH[season]
        current = (int(year), month)
        if previous is not None:
            apart = (current[0] - previous[0]) * 12 + (current[1] - previous[1])
            if apart != 1:
                raise ValueError(
                    f"{series_id}: seasons are not contiguous at line {number} "
                    f"({season} {year} follows a season {apart} months earlier)"
                )
        previous = current
        dates.append(f"{year}-{month:02d}-01")
        values.append(float(tokens[anom]))
    frame = pd.DataFrame(
        {
            "source_id": SOURCE_ID,
            "series_id": series_id,
            "region": REGION,
            "date": dates,
            "value": values,
            "unit": UNIT,
            "retrieved_at": retrieved_at or utc_now_iso(),
            "licence_id": _licence_id(),
        },
        columns=list(COLUMNS),
    )
    return validate_frame(frame)


def parse_oni(text: str, retrieved_at: str | None = None) -> pd.DataFrame:
    """Parse ``oni.ascii.txt`` into the tidy contract as series ``ONI``.

    ``retrieved_at`` is the UTC ISO timestamp of the download; it defaults
    to now. The ``TOTAL`` column is validated and dropped.
    """
    return _parse_cpc_table(text, "ONI", ONI_HEADER, retrieved_at)


def parse_roni(text: str, retrieved_at: str | None = None) -> pd.DataFrame:
    """Parse ``RONI.ascii.txt`` into the tidy contract as series ``RONI``."""
    return _parse_cpc_table(text, "RONI", RONI_HEADER, retrieved_at)


def fetch() -> tuple[Fetched, ...]:
    """Download ``oni.ascii.txt`` and ``RONI.ascii.txt`` from the CPC data directory."""
    return (download(ONI_URL, ALLOWED_HOSTS), download(RONI_URL, ALLOWED_HOSTS))


def parse(fetched: tuple[Fetched, ...]) -> pd.DataFrame:
    """Parse the two files from ``fetch`` into one frame with series ONI and RONI."""
    urls = [item.url for item in fetched]
    if urls != [ONI_URL, RONI_URL]:
        raise ValueError(f"expected the ONI and RONI files in that order, got {urls}")
    oni, roni = fetched
    frame = pd.concat(
        [
            parse_oni(oni.content.decode("ascii"), oni.retrieved_at),
            parse_roni(roni.content.decode("ascii"), roni.retrieved_at),
        ],
        ignore_index=True,
    )
    return validate_frame(frame)
