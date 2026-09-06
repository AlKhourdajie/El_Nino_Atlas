"""Tests for the NOAA ENSO event convention in src/enso_events.py.

The first group uses a synthetic ONI series that exercises the rule's
edges. The second group runs against the NOAA fixture and is skipped
until tests/fixtures/noaa_oni/oni.ascii.txt is committed.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.enso_events import classify_enso_events, season_label

FIXTURE = Path(__file__).parent / "fixtures" / "noaa_oni" / "oni.ascii.txt"


def oni_frame(values: list[float], start: str = "2000-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(values), freq="MS").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "source_id": "noaa_oni",
            "series_id": "oni",
            "region": "nino34",
            "date": dates,
            "value": [float(v) for v in values],
            "unit": "degC",
            "retrieved_at": "2026-09-05T17:00:00Z",
            "licence_id": "US-PD",
        }
    )


# Synthetic series, one value per season from JFM 2000 (2000-01-01):
#   index 0-2     neutral
#   index 3-9     seven seasons >= +0.5 with a 1.5 peak at index 6 -> El Niño
#   index 10-11   neutral
#   index 12-15   four seasons at -0.6 -> too short, no event
#   index 16-17   neutral
#   index 18-22   five seasons at exactly -0.5 -> La Niña (threshold inclusive)
#   index 23      neutral
#   index 24-26   three at +0.7, index 27 at +0.4, index 28-29 two at +0.7 -> broken run, no event
SYNTHETIC = (
    [0.1, 0.2, 0.4]
    + [0.5, 0.8, 1.2, 1.5, 1.1, 0.7, 0.5]
    + [0.3, -0.2]
    + [-0.6, -0.6, -0.6, -0.6]
    + [-0.3, 0.0]
    + [-0.5, -0.5, -0.5, -0.5, -0.5]
    + [0.0]
    + [0.7, 0.7, 0.7, 0.4, 0.7, 0.7]
)


def test_synthetic_events_recovered():
    events = classify_enso_events(oni_frame(SYNTHETIC))
    assert len(events) == 2

    nino = events.iloc[0]
    assert nino["phase"] == "el_nino"
    assert nino["onset"] == "2000-04-01"
    assert nino["end"] == "2000-10-01"
    assert nino["n_seasons"] == 7
    assert nino["peak"] == 1.5
    assert nino["peak_date"] == "2000-07-01"
    assert nino["onset_season"] == "MAM 2000"
    assert nino["end_season"] == "SON 2000"

    nina = events.iloc[1]
    assert nina["phase"] == "la_nina"
    assert nina["onset"] == "2001-07-01"
    assert nina["end"] == "2001-11-01"
    assert nina["n_seasons"] == 5
    assert nina["peak"] == -0.5


def test_four_season_run_is_not_an_event():
    events = classify_enso_events(oni_frame([0.0] + [0.9] * 4 + [0.0]))
    assert events.empty
    assert list(events.columns) == [
        "phase",
        "onset",
        "end",
        "onset_season",
        "end_season",
        "peak",
        "peak_date",
        "n_seasons",
    ]


def test_run_crossing_year_boundary_labels_seasons():
    # Five seasons centred Nov 2005 to Mar 2006: OND 2005 ... FMA 2006.
    events = classify_enso_events(oni_frame([0.0] + [-1.0] * 5 + [0.0], start="2005-10-01"))
    assert len(events) == 1
    assert events.loc[0, "onset_season"] == "OND 2005"
    assert events.loc[0, "end_season"] == "FMA 2006"


def test_season_label_wraps_december():
    from datetime import date

    assert season_label(date(1997, 12, 1)) == "NDJ 1997"
    assert season_label(date(1998, 1, 1)) == "DJF 1998"


def test_gap_in_seasons_raises():
    df = oni_frame([0.6] * 8).drop(index=3)
    with pytest.raises(ValueError, match="not contiguous"):
        classify_enso_events(df)


def test_no_oni_series_raises():
    df = oni_frame([0.6] * 6).assign(series_id="something_else")
    with pytest.raises(ValueError, match="no rows with series_id 'oni'"):
        classify_enso_events(df)


@pytest.mark.skipif(not FIXTURE.exists(), reason="NOAA ONI fixture not yet committed")
def test_known_events_from_fixture():
    from src.fetchers.noaa_oni import parse_oni

    events = classify_enso_events(parse_oni(FIXTURE.read_text(encoding="utf-8")))

    def covering(phase: str, month: str) -> pd.Series:
        hits = events[
            (events["phase"] == phase) & (events["onset"] <= month) & (events["end"] >= month)
        ]
        assert len(hits) == 1, f"expected one {phase} event covering {month}, got {len(hits)}"
        return hits.iloc[0]

    assert covering("el_nino", "1997-12-01")["peak"] >= 2.0
    assert covering("el_nino", "2015-12-01")["peak"] >= 2.0
    assert covering("la_nina", "2010-12-01")["peak"] <= -1.0
