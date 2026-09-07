"""Tests for the NOAA ENSO event convention in src/enso_events.py.

The first group uses a synthetic series that exercises the rule's edges.
The second group pins the episodes published in the CPC tables against
the committed fixtures in tests/fixtures/noaa_oni/. Every expected number
is copied from a fixture line or a CPC table cell and quoted beside it;
the table values are from the ERSSTv6 ONI table
(https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/)
and the RONI table
(https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/)
as read on 7 September 2026.
"""

from dataclasses import FrozenInstanceError
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.enso_events import (
    EVENT_COLUMNS,
    Event,
    classify_enso_events,
    enso_event_records,
    peak_category,
    season_label,
    threshold_value,
)
from src.fetchers.noaa_oni import parse_oni, parse_roni

FIXTURES = Path(__file__).parent / "fixtures" / "noaa_oni"

# Centre month -> NOAA season label; the table year is the centre month's year.
SEASON_LABELS = {
    "2000-01-01": "DJF 2000",
    "2000-02-01": "JFM 2000",
    "2000-03-01": "FMA 2000",
    "2000-04-01": "MAM 2000",
    "2000-05-01": "AMJ 2000",
    "2000-06-01": "MJJ 2000",
    "2000-07-01": "JJA 2000",
    "2000-08-01": "JAS 2000",
    "2000-09-01": "ASO 2000",
    "2000-10-01": "SON 2000",
    "2000-11-01": "OND 2000",
    "2000-12-01": "NDJ 2000",
}


def oni_frame(values: list[float], start: str = "2000-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(values), freq="MS").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "source_id": "noaa_oni",
            "series_id": "ONI",
            "region": "NINO3.4",
            "date": dates,
            "value": [float(v) for v in values],
            "unit": "degC",
            "retrieved_at": "2026-09-05T17:00:00Z",
            "licence_id": "LicenseRef-US-PD",
        }
    )


# Synthetic series, one value per season from DJF 2000 (2000-01-01):
#   index 0-2     neutral
#   index 3-9     seven seasons >= +0.5 with a 1.5 peak at index 6 -> El Niño
#   index 10-11   neutral
#   index 12-15   four seasons at -0.6 -> too short, no event
#   index 16-17   neutral
#   index 18-22   five seasons at exactly -0.5 -> La Niña (threshold inclusive)
#   index 23      neutral
#   index 24-26   three at +0.7, index 27 at +0.4 -> broken run, no event
#   index 28-29   two at +0.7 reaching the last season -> provisional El Niño
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
    assert len(events) == 3

    nino = events.iloc[0]
    assert nino["phase"] == "el_nino"
    assert nino["onset"] == "2000-04-01"
    assert nino["end"] == "2000-10-01"
    assert nino["n_seasons"] == 7
    assert nino["peak"] == 1.5
    assert nino["peak_date"] == "2000-07-01"
    assert nino["onset_season"] == "MAM 2000"
    assert nino["end_season"] == "SON 2000"
    assert not nino["provisional"]
    assert nino["peak_category"] == "strong"

    nina = events.iloc[1]
    assert nina["phase"] == "la_nina"
    assert nina["onset"] == "2001-07-01"
    assert nina["end"] == "2001-11-01"
    assert nina["n_seasons"] == 5
    assert nina["peak"] == -0.5
    assert nina["peak_category"] == "weak"

    tail = events.iloc[2]
    assert tail["phase"] == "el_nino"
    assert tail["onset"] == "2002-05-01"
    assert tail["end"] is None
    assert tail["end_season"] is None
    assert tail["n_seasons"] == 2
    assert bool(tail["provisional"]) is True


def test_four_season_run_is_not_an_event():
    events = classify_enso_events(oni_frame([0.0] + [0.9] * 4 + [0.0]))
    assert events.empty
    assert (
        list(events.columns)
        == EVENT_COLUMNS
        == [
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
    )


def test_run_crossing_year_boundary_labels_seasons():
    # Five seasons centred Nov 2005 to Mar 2006: OND 2005 ... FMA 2006.
    events = classify_enso_events(oni_frame([0.0] + [-1.0] * 5 + [0.0], start="2005-10-01"))
    assert len(events) == 1
    assert events.loc[0, "onset_season"] == "OND 2005"
    assert events.loc[0, "end_season"] == "FMA 2006"


def test_season_label_wraps_december():
    assert season_label(date(1997, 12, 1)) == "NDJ 1997"
    assert season_label(date(1998, 1, 1)) == "DJF 1998"


def test_gap_in_seasons_raises():
    df = oni_frame([0.6] * 8).drop(index=3)
    with pytest.raises(ValueError, match="not contiguous"):
        classify_enso_events(df)


def test_classify_requires_exactly_one_series():
    one = oni_frame([0.6] * 6)
    other = one.assign(series_id="RONI")
    with pytest.raises(ValueError, match="exactly one series"):
        classify_enso_events(pd.concat([one, other], ignore_index=True))


def test_classify_accepts_any_single_series_id():
    for series_id in ("RONI", "something_else"):
        events = classify_enso_events(
            oni_frame([0.0] + [0.9] * 5 + [0.0]).assign(series_id=series_id)
        )
        assert len(events) == 1
        assert events.loc[0, "onset_season"] == "JFM 2000"
        assert events.loc[0, "end_season"] == "MJJ 2000"


def test_season_label_accepts_iso_strings():
    for iso, label in SEASON_LABELS.items():
        assert season_label(iso) == label
        assert season_label(date.fromisoformat(iso)) == label


def test_synthetic_event_records():
    records = enso_event_records(oni_frame(SYNTHETIC))
    assert len(records) == 3
    assert all(isinstance(record, Event) for record in records)

    nino, nina, tail = records
    assert nino.phase == "el_nino"
    assert nino.onset == date(2000, 4, 1)
    assert nino.end == date(2000, 10, 1)
    assert nino.seasons == (
        "MAM 2000",
        "AMJ 2000",
        "MJJ 2000",
        "JJA 2000",
        "JAS 2000",
        "ASO 2000",
        "SON 2000",
    )
    assert nino.peak == 1.5
    assert nino.peak_date == date(2000, 7, 1)
    assert nino.provisional is False
    assert nino.peak_category == "strong"

    assert nina.phase == "la_nina"
    assert nina.onset == date(2001, 7, 1)
    assert nina.end == date(2001, 11, 1)
    assert nina.seasons == ("JJA 2001", "JAS 2001", "ASO 2001", "SON 2001", "OND 2001")
    assert nina.peak == -0.5
    assert nina.peak_date == date(2001, 7, 1)
    assert nina.peak_category == "weak"

    assert tail.phase == "el_nino"
    assert tail.onset == date(2002, 5, 1)
    assert tail.end is None
    assert tail.seasons == ("AMJ 2002", "MJJ 2002")
    assert tail.provisional is True
    assert tail.peak == 0.7
    assert tail.peak_category == "weak"


def test_records_and_frame_agree():
    frame = classify_enso_events(oni_frame(SYNTHETIC))
    records = enso_event_records(oni_frame(SYNTHETIC))
    assert len(frame) == len(records) == 3
    for row, record in zip(frame.to_dict("records"), records, strict=True):
        assert row["phase"] == record.phase
        assert row["onset"] == record.onset.isoformat()
        assert row["end"] == (None if record.end is None else record.end.isoformat())
        assert row["onset_season"] == record.seasons[0]
        assert row["end_season"] == (None if record.end is None else record.seasons[-1])
        assert row["peak"] == record.peak
        assert row["peak_date"] == record.peak_date.isoformat()
        assert row["n_seasons"] == len(record.seasons)
        assert row["provisional"] == record.provisional
        assert row["peak_category"] == record.peak_category


def test_event_records_require_exactly_one_series():
    one = oni_frame([0.6] * 6)
    other = one.assign(series_id="nino34_anomaly")
    with pytest.raises(ValueError, match="exactly one series"):
        enso_event_records(pd.concat([one, other], ignore_index=True))


def test_event_records_accept_any_single_series_id():
    frame = oni_frame([0.0] + [0.9] * 5 + [0.0]).assign(series_id="nino34")
    records = enso_event_records(frame)
    assert len(records) == 1
    assert records[0].seasons == ("JFM 2000", "FMA 2000", "MAM 2000", "AMJ 2000", "MJJ 2000")


def test_event_record_is_frozen():
    record = enso_event_records(oni_frame(SYNTHETIC))[0]
    with pytest.raises(FrozenInstanceError):
        record.peak = 0.0


def test_threshold_value_rounds_like_the_cpc_tables():
    # floor(10x + 0.5) / 10: a value ending in 5 rounds up, so 0.45 gives
    # 0.5 while -0.45 gives -0.4, as the CPC tables show.
    assert threshold_value(0.45) == 0.5
    assert threshold_value(-0.45) == -0.4
    assert threshold_value(0.46) == 0.5
    assert threshold_value(0.44) == 0.4
    assert threshold_value(-0.46) == -0.5
    assert threshold_value(0.95) == 1.0
    assert threshold_value(-0.85) == -0.8
    assert threshold_value(1.36) == 1.4
    assert threshold_value(-1.57) == -1.6
    assert threshold_value(0.0) == 0.0
    assert threshold_value(-0.04) == 0.0
    assert threshold_value(1.15) == 1.2


def test_threshold_applies_to_the_one_decimal_value():
    # 0.46 rounds to 0.5 and counts; 0.44 rounds to 0.4 and breaks the run.
    events = classify_enso_events(oni_frame([0.0, 0.46, 0.6, 0.7, 0.8, 0.46, 0.0]))
    assert len(events) == 1
    assert events.loc[0, "n_seasons"] == 5
    assert classify_enso_events(oni_frame([0.0, 0.44, 0.6, 0.7, 0.8, 0.6, 0.0])).empty
    # -0.45 rounds to -0.4 and breaks a cold run; -0.46 rounds to -0.5 and joins it.
    assert classify_enso_events(oni_frame([0.0, -0.6, -0.6, -0.45, -0.6, -0.6, 0.0])).empty
    assert len(classify_enso_events(oni_frame([0.0, -0.6, -0.6, -0.46, -0.6, -0.6, 0.0]))) == 1


def test_peak_keeps_two_decimals_and_category_uses_one():
    (event,) = enso_event_records(oni_frame([0.0, 0.5, 1.94, 0.6, 0.7, 0.8, 0.0]))
    assert event.peak == 1.94
    assert event.peak_category == "strong"  # 1.94 rounds to 1.9
    (event,) = enso_event_records(oni_frame([0.0, 0.5, 1.95, 0.6, 0.7, 0.8, 0.0]))
    assert event.peak == 1.95
    assert event.peak_category == "very_strong"  # 1.95 rounds to 2.0


@pytest.mark.parametrize(
    ("peak", "category"),
    [
        (0.5, "weak"),
        (0.94, "weak"),
        (0.95, "moderate"),
        (-1.44, "moderate"),
        (1.45, "strong"),
        (-1.94, "strong"),
        (1.95, "very_strong"),
        (-2.59, "very_strong"),
        (0.4, ""),
    ],
)
def test_peak_category_bands(peak, category):
    assert peak_category(peak) == category


def test_run_reaching_the_last_season_has_no_end():
    # Five seasons at or over the threshold up to the last row: an event,
    # not provisional, whose end the data do not show.
    (event,) = enso_event_records(oni_frame([0.0, 0.0] + [0.9] * 5))
    assert event.end is None
    assert event.provisional is False
    assert event.seasons == ("FMA 2000", "MAM 2000", "AMJ 2000", "MJJ 2000", "JJA 2000")
    frame = classify_enso_events(oni_frame([0.0, 0.0] + [0.9] * 5))
    assert frame.loc[0, "end"] is None
    assert frame.loc[0, "end_season"] is None
    assert frame.loc[0, "n_seasons"] == 5


def test_short_run_reaching_the_last_season_is_provisional():
    (event,) = enso_event_records(oni_frame([0.0, 0.0, 0.0, -0.6, -0.7, -0.8]))
    assert event.phase == "la_nina"
    assert event.provisional is True
    assert event.end is None
    assert event.seasons == ("MAM 2000", "AMJ 2000", "MJJ 2000")
    assert event.peak == -0.8
    assert event.peak_date == date(2000, 6, 1)
    assert event.peak_category == "weak"
    frame = classify_enso_events(oni_frame([0.0, 0.0, 0.0, -0.6, -0.7, -0.8]))
    assert bool(frame.loc[0, "provisional"]) is True
    assert frame.loc[0, "end"] is None
    assert frame.loc[0, "n_seasons"] == 3


def test_short_run_before_the_last_season_is_dropped():
    assert classify_enso_events(oni_frame([0.0, 0.6, 0.7, 0.8, 0.0])).empty


# --------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def oni_events() -> list[Event]:
    return enso_event_records(parse_oni((FIXTURES / "oni.ascii.txt").read_text(encoding="ascii")))


@pytest.fixture(scope="module")
def roni_events() -> list[Event]:
    return enso_event_records(parse_roni((FIXTURES / "RONI.ascii.txt").read_text(encoding="ascii")))


def covering(events: list[Event], phase: str, month: date) -> Event:
    hits = [
        e
        for e in events
        if e.phase == phase and e.onset <= month and (e.end is None or month <= e.end)
    ]
    assert len(hits) == 1, f"expected one {phase} event covering {month}, got {len(hits)}"
    return hits[0]


def test_event_counts_match_the_cpc_tables(oni_events, roni_events):
    # The ONI table colours 45 episodes and the RONI table 47; each index
    # adds one provisional run at the end of the record (2026).
    assert len([e for e in oni_events if not e.provisional]) == 45
    assert len([e for e in oni_events if e.provisional]) == 1
    assert len([e for e in roni_events if not e.provisional]) == 47
    assert len([e for e in roni_events if e.provisional]) == 1


def test_oni_1997_98_el_nino(oni_events):
    # CPC ONI table, 1997 row: MAM 0.3 black, AMJ 0.7 first red, ... NDJ 2.4;
    # 1998 row: MAM 1.0 last red, AMJ 0.4 black.
    # oni.ascii.txt line 570 "  AMJ 1997  28.44   0.71", line 581 "  MAM 1998  28.63   1.03",
    # line 582 "  AMJ 1998  28.13   0.40".
    event = covering(oni_events, "el_nino", date(1997, 12, 1))
    assert event.onset == date(1997, 5, 1)
    assert event.end == date(1998, 4, 1)
    assert event.seasons[0] == "AMJ 1997"
    assert event.seasons[-1] == "MAM 1998"
    assert len(event.seasons) == 12
    assert event.peak == 2.37  # line 577 "  NDJ 1997  28.96   2.37"; table NDJ 1997 2.4
    assert event.peak_date == date(1997, 12, 1)
    assert event.peak_category == "very_strong"
    assert event.provisional is False


def test_oni_2015_16_el_nino(oni_events):
    # CPC ONI table, 2014 row: ASO 0.2 black, SON 0.5 first red; 2016 row:
    # AMJ 0.6 last red, MJJ 0.1 black.
    # oni.ascii.txt line 779 "  SON 2014  27.22   0.51", line 798 "  AMJ 2016  28.37   0.57",
    # line 799 "  MJJ 2016  27.72   0.09".
    event = covering(oni_events, "el_nino", date(2015, 12, 1))
    assert event.onset == date(2014, 10, 1)
    assert event.end == date(2016, 5, 1)
    assert event.seasons[0] == "SON 2014"
    assert event.seasons[-1] == "AMJ 2016"
    assert len(event.seasons) == 20
    assert event.peak == 2.59  # line 793 "  NDJ 2015  29.15   2.59"; table NDJ 2015 2.6
    assert event.peak_date == date(2015, 12, 1)
    assert event.peak_category == "very_strong"


def test_oni_2010_11_la_nina(oni_events):
    # CPC ONI table, 2010 row: AMJ -0.2 black, MJJ -0.7 first blue; 2011 row:
    # AMJ -0.5 last blue, MJJ -0.3 black.
    # oni.ascii.txt line 726 "  AMJ 2010  27.72  -0.16", line 727 "  MJJ 2010  27.03  -0.66",
    # line 738 "  AMJ 2011  27.29  -0.50", line 739 "  MJJ 2011  27.29  -0.34".
    event = covering(oni_events, "la_nina", date(2010, 12, 1))
    assert event.onset == date(2010, 6, 1)
    assert event.end == date(2011, 5, 1)
    assert event.seasons[0] == "MJJ 2010"
    assert event.seasons[-1] == "AMJ 2011"
    assert len(event.seasons) == 12
    assert event.peak == -1.57  # line 732 "  OND 2010  25.14  -1.57"; table OND 2010 -1.6
    assert event.peak_date == date(2010, 11, 1)
    assert event.peak_category == "strong"


def test_oni_2026_state(oni_events):
    # CPC ONI table, 2026 row: DJF -0.4, JFM -0.2, FMA 0.1, MAM 0.5, AMJ 0.9,
    # MJJ 1.4, JJA 1.8, all uncoloured because the run is shorter than five seasons.
    # oni.ascii.txt line 917 "  MAM 2026  28.09   0.46" (0.5 at one decimal),
    # line 918 "  AMJ 2026  28.74   0.95", line 919 "  MJJ 2026  29.02   1.39",
    # line 920 "  JJA 2026  29.09   1.80".
    last = oni_events[-1]
    assert last.phase == "el_nino"
    assert last.provisional is True
    assert last.end is None
    assert last.onset == date(2026, 4, 1)  # MAM 2026 is centred on April
    assert last.seasons == ("MAM 2026", "AMJ 2026", "MJJ 2026", "JJA 2026")
    assert last.peak == 1.80
    assert last.peak_date == date(2026, 7, 1)
    assert last.peak_category == "strong"


def test_oni_shows_no_2025_26_la_nina(oni_events):
    # CPC ONI table, 2025 row: SON -0.6, OND -0.6, NDJ -0.6 uncoloured; 2026 DJF -0.4.
    # oni.ascii.txt line 911 "  SON 2025  26.14  -0.57", line 912 "  OND 2025  26.04  -0.61",
    # line 913 "  NDJ 2025  25.96  -0.60", line 914 "  DJF 2026  26.15  -0.39".
    assert not [e for e in oni_events if e.phase == "la_nina" and e.onset.year >= 2024]


def test_roni_1997_98_el_nino(roni_events):
    # CPC RONI table, 1997 row: FMA 0.2 black, MAM 0.5 first red; 1998 row:
    # MAM 0.8 last red, AMJ 0.1 black.
    # RONI.ascii.txt line 569 "MAM  1997  0.47" (0.5 at one decimal),
    # line 581 "MAM  1998  0.81", line 582 "AMJ  1998  0.07".
    event = covering(roni_events, "el_nino", date(1997, 12, 1))
    assert event.onset == date(1997, 4, 1)
    assert event.end == date(1998, 4, 1)
    assert event.seasons[0] == "MAM 1997"
    assert event.seasons[-1] == "MAM 1998"
    assert len(event.seasons) == 13
    assert event.peak == 2.28  # line 577 "NDJ  1997  2.28"; table OND 1997 2.3 and NDJ 1997 2.3
    assert event.peak_date == date(1997, 12, 1)
    assert event.peak_category == "very_strong"
    assert event.provisional is False


def test_roni_2015_16_el_nino(roni_events):
    # CPC RONI table, 2014 row: SON 0.4 black, OND 0.5 first red; 2015 row:
    # JFM 0.5 red; 2016 row: MAM 0.7 last red, AMJ 0.1 black.
    # RONI.ascii.txt line 780 "OND  2014  0.54", line 783 "JFM  2015  0.47" (0.5 at one
    # decimal, so the run holds), line 797 "MAM  2016  0.65", line 798 "AMJ  2016  0.08".
    event = covering(roni_events, "el_nino", date(2015, 12, 1))
    assert event.onset == date(2014, 11, 1)
    assert event.end == date(2016, 4, 1)
    assert event.seasons[0] == "OND 2014"
    assert event.seasons[-1] == "MAM 2016"
    assert len(event.seasons) == 18
    assert event.peak == 2.25  # line 793 "NDJ  2015  2.25"; table NDJ 2015 2.3
    assert event.peak_date == date(2015, 12, 1)
    assert event.peak_category == "very_strong"


def test_roni_2010_11_la_nina(roni_events):
    # CPC RONI table, 2010 row: MAM 0.1 black, AMJ -0.5 first blue; 2011 row:
    # AMJ -0.5 last blue, MJJ -0.3 black.
    # RONI.ascii.txt line 726 "AMJ  2010 -0.50", line 738 "AMJ  2011 -0.52",
    # line 739 "MJJ  2011 -0.29".
    event = covering(roni_events, "la_nina", date(2010, 12, 1))
    assert event.onset == date(2010, 5, 1)
    assert event.end == date(2011, 5, 1)
    assert event.seasons[0] == "AMJ 2010"
    assert event.seasons[-1] == "AMJ 2011"
    assert len(event.seasons) == 13
    assert event.peak == -1.63  # line 732 "OND  2010 -1.63"; table SON 2010 -1.6 and OND 2010 -1.6
    assert event.peak_date == date(2010, 11, 1)
    assert event.peak_category == "strong"


def test_roni_2025_26_la_nina(roni_events):
    # CPC RONI table, 2025 row: JJA -0.4 black, JAS -0.6 first blue ... NDJ -1.0;
    # 2026 row: DJF -0.9, JFM -0.8 last blue, FMA -0.4 black.
    # RONI.ascii.txt line 909 "JAS  2025 -0.59", line 915 "JFM  2026 -0.76",
    # line 916 "FMA  2026 -0.44".
    event = covering(roni_events, "la_nina", date(2025, 12, 1))
    assert event.onset == date(2025, 8, 1)
    assert event.end == date(2026, 2, 1)
    assert event.seasons[0] == "JAS 2025"
    assert event.seasons[-1] == "JFM 2026"
    assert len(event.seasons) == 7
    assert event.peak == -1.04  # line 913 "NDJ  2025 -1.04"; table OND 2025 -1.0 and NDJ 2025 -1.0
    assert event.peak_date == date(2025, 12, 1)
    assert event.peak_category == "moderate"
    assert event.provisional is False


def test_roni_2026_state(roni_events):
    # CPC RONI table, 2026 row: FMA -0.4, MAM 0.0, AMJ 0.5, MJJ 1.0, JJA 1.4,
    # the last three uncoloured because the run is shorter than five seasons.
    # RONI.ascii.txt line 918 "AMJ  2026  0.49" (0.5 at one decimal),
    # line 919 "MJJ  2026  0.97", line 920 "JJA  2026  1.36".
    last = roni_events[-1]
    assert last.phase == "el_nino"
    assert last.provisional is True
    assert last.end is None
    assert last.onset == date(2026, 5, 1)  # AMJ 2026 is centred on May
    assert last.seasons == ("AMJ 2026", "MJJ 2026", "JJA 2026")
    assert last.peak == 1.36
    assert last.peak_date == date(2026, 7, 1)
    assert last.peak_category == "moderate"


def test_roni_1983_84_la_nina_ends_one_season_early():
    # Known deviation from the CPC RONI table, which colours ASO 1983 -0.6 to
    # MJJ 1984 -0.5 (ten seasons). The file has FMA 1984 as -0.45, which the
    # threshold rule rounds to -0.4, so the event ends at JFM 1984 and the
    # three seasons MAM to MJJ 1984 form a run too short to be an event.
    # RONI.ascii.txt line 406 "ASO  1983 -0.59", line 411 "JFM  1984 -0.52",
    # line 412 "FMA  1984 -0.45", line 413 "MAM  1984 -0.59", line 414 "AMJ  1984 -0.62",
    # line 415 "MJJ  1984 -0.51", line 416 "JJA  1984 -0.32".
    events = enso_event_records(parse_roni((FIXTURES / "RONI.ascii.txt").read_text("ascii")))
    event = covering(events, "la_nina", date(1983, 12, 1))
    assert event.onset == date(1983, 9, 1)
    assert event.end == date(1984, 2, 1)
    assert len(event.seasons) == 6
    for month in (date(1984, 4, 1), date(1984, 5, 1), date(1984, 6, 1)):  # MAM, AMJ, MJJ 1984
        assert not [e for e in events if e.onset <= month <= (e.end or date.max)]
