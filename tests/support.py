"""Shared helpers for the panel and page tests.

Synthetic contract frames that satisfy ``src/schema.py`` (ISO date and
retrieved_at strings, float values), and a walker over Dash component
trees. Nothing here touches the network or the snapshot directory.
"""

from __future__ import annotations

from collections.abc import Iterator

import pandas as pd

RETRIEVED_AT = "2026-09-05T17:00:00Z"

INDEX_START = "1990-01-01"
INDEX_MONTHS = 439  # January 1990 to July 2026


def index_values() -> dict[str, list[float]]:
    """RONI and ONI values with three events under the five-season rule.

    El Niño MJJ 1997 to AMJ 1998 (twelve seasons), La Niña JJA 2010 to
    JFM 2011 (eight seasons), El Niño FMA 2026 to JJA 2026 (five seasons,
    the last season in the frame). ONI runs a little warmer than RONI.
    """
    roni = [0.1] * INDEX_MONTHS
    oni = [0.2] * INDEX_MONTHS
    for i in range(89, 101):  # 1997-06-01 to 1998-05-01
        roni[i], oni[i] = 1.5, 1.8
    for i in range(246, 254):  # 2010-07-01 to 2011-02-01
        roni[i], oni[i] = -1.0, -1.1
    for i in range(434, 439):  # 2026-03-01 to 2026-07-01
        roni[i], oni[i] = 1.2, 1.4
    return {"RONI": roni, "ONI": oni}


def index_frame(
    values: dict[str, list[float]] | None = None,
    start: str = INDEX_START,
    unit: str = "degC",
) -> pd.DataFrame:
    """A ``noaa_oni`` contract frame with one row per season for each series."""
    values = values if values is not None else index_values()
    parts = []
    for series_id, series_values in values.items():
        dates = pd.date_range(start, periods=len(series_values), freq="MS").strftime("%Y-%m-%d")
        parts.append(
            pd.DataFrame(
                {
                    "source_id": "noaa_oni",
                    "series_id": series_id,
                    "region": "nino34",
                    "date": dates,
                    "value": [float(v) for v in series_values],
                    "unit": unit,
                    "retrieved_at": RETRIEVED_AT,
                    "licence_id": "LicenseRef-US-PD",
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def price_frame(
    series: dict[str, tuple[str, list[float]]],
    start: str = "2009-01-01",
) -> pd.DataFrame:
    """A ``worldbank_pink_sheet`` contract frame: series_id -> (unit, monthly values)."""
    parts = []
    for series_id, (unit, values) in series.items():
        dates = pd.date_range(start, periods=len(values), freq="MS").strftime("%Y-%m-%d")
        parts.append(
            pd.DataFrame(
                {
                    "source_id": "worldbank_pink_sheet",
                    "series_id": series_id,
                    "region": "global",
                    "date": dates,
                    "value": [float(v) for v in values],
                    "unit": unit,
                    "retrieved_at": RETRIEVED_AT,
                    "licence_id": "CC-BY-4.0",
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def walk(component) -> Iterator:
    """Yield ``component`` and every descendant in document order."""
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, list | tuple):
        for child in children:
            yield from walk(child)
    elif children is not None and not isinstance(children, str | int | float):
        yield from walk(children)


def component_ids(component) -> list[str]:
    """Every ``id`` in the tree, in document order."""
    return [c.id for c in walk(component) if getattr(c, "id", None)]
