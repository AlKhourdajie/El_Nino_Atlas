"""Tests for the ONI and RONI parsers in src/fetchers/noaa_oni.py.

Every expected number is copied from a line of the committed fixtures in
tests/fixtures/noaa_oni/, quoted in a comment beside it.
"""

import re
from pathlib import Path

import pandas as pd
import pytest

from src.enso_events import season_label
from src.fetchers.noaa_oni import (
    CENTRE_MONTH,
    ONI_HEADER,
    RONI_HEADER,
    parse_oni,
    parse_roni,
)
from src.schema import COLUMNS, validate_frame

FIXTURES = Path(__file__).parent / "fixtures" / "noaa_oni"
ONI_TEXT = (FIXTURES / "oni.ascii.txt").read_text(encoding="ascii")
RONI_TEXT = (FIXTURES / "RONI.ascii.txt").read_text(encoding="ascii")
RETRIEVED_AT = "2026-09-07T14:30:23Z"

# Both fixtures have 920 lines: one header and 919 season rows, DJF 1950
# (line 2) to JJA 2026 (line 920).
ROW_COUNT = 919


def _values(frame: pd.DataFrame) -> pd.Series:
    return frame.set_index("date")["value"]


@pytest.mark.parametrize(
    ("parse", "text", "series_id"),
    [(parse_oni, ONI_TEXT, "ONI"), (parse_roni, RONI_TEXT, "RONI")],
)
def test_fixture_parses_to_a_valid_complete_frame(parse, text, series_id):
    frame = parse(text, retrieved_at=RETRIEVED_AT)
    validate_frame(frame)
    assert list(frame.columns) == list(COLUMNS)
    assert len(frame) == ROW_COUNT
    assert set(frame["source_id"]) == {"noaa_oni"}
    assert set(frame["series_id"]) == {series_id}
    assert set(frame["region"]) == {"NINO3.4"}
    assert set(frame["unit"]) == {"degC"}
    assert set(frame["retrieved_at"]) == {RETRIEVED_AT}
    assert set(frame["licence_id"]) == {"LicenseRef-US-PD"}
    assert frame["date"].iloc[0] == "1950-01-01"  # line 2 is DJF 1950
    assert frame["date"].iloc[-1] == "2026-07-01"  # line 920 is JJA 2026
    assert frame["date"].is_monotonic_increasing


def test_oni_spot_values():
    values = _values(parse_oni(ONI_TEXT))
    assert values["1950-01-01"] == -1.32  # oni.ascii.txt line 2: "  DJF 1950  25.01  -1.32"
    assert values["1997-12-01"] == 2.37  # oni.ascii.txt line 577: "  NDJ 1997  28.96   2.37"
    assert values["2026-07-01"] == 1.80  # oni.ascii.txt line 920: "  JJA 2026  29.09   1.80"


def test_roni_spot_values():
    values = _values(parse_roni(RONI_TEXT))
    assert values["1950-01-01"] == -1.19  # RONI.ascii.txt line 2: "DJF  1950 -1.19"
    assert values["1997-12-01"] == 2.28  # RONI.ascii.txt line 577: "NDJ  1997  2.28"
    assert values["2026-07-01"] == 1.36  # RONI.ascii.txt line 920: "JJA  2026  1.36"


def test_djf_and_ndj_take_the_centre_month_year():
    # DJF 1950 covers December 1949 to February 1950; its table year is
    # the centre month's year, so it is dated 1950-01-01. NDJ 1950 covers
    # November 1950 to January 1951 and is dated 1950-12-01.
    oni = _values(parse_oni(ONI_TEXT))
    assert oni["1950-01-01"] == -1.32  # oni.ascii.txt line 2:  "  DJF 1950  25.01  -1.32"
    assert oni["1950-12-01"] == -0.79  # oni.ascii.txt line 13: "  NDJ 1950  25.41  -0.79"
    assert oni["1951-01-01"] == -0.66  # oni.ascii.txt line 14: "  DJF 1951  25.67  -0.66"
    roni = _values(parse_roni(RONI_TEXT))
    assert roni["1950-12-01"] == -0.50  # RONI.ascii.txt line 13: "NDJ  1950 -0.50"
    assert roni["1951-01-01"] == -0.28  # RONI.ascii.txt line 14: "DJF  1951 -0.28"
    assert "1949-12-01" not in oni.index


@pytest.mark.parametrize(("parse", "text"), [(parse_oni, ONI_TEXT), (parse_roni, RONI_TEXT)])
def test_every_row_agrees_with_season_label(parse, text):
    frame = parse(text)
    labels = [f"{line.split()[0]} {line.split()[1]}" for line in text.splitlines()[1:]]
    assert [season_label(d) for d in frame["date"]] == labels
    assert len(labels) == ROW_COUNT


def test_centre_month_table_matches_season_label():
    for season, month in CENTRE_MONTH.items():
        assert season_label(f"2000-{month:02d}-01") == f"{season} 2000"


def test_both_indices_share_keys_only_through_series_id():
    both = pd.concat([parse_oni(ONI_TEXT), parse_roni(RONI_TEXT)], ignore_index=True)
    validate_frame(both)
    assert len(both) == 2 * ROW_COUNT
    assert sorted(set(both["series_id"])) == ["ONI", "RONI"]


def test_retrieved_at_defaults_to_a_utc_timestamp():
    frame = parse_roni(RONI_TEXT)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", frame["retrieved_at"].iloc[0])


def test_headers_are_specific_to_each_file():
    assert ONI_HEADER == ("SEAS", "YR", "TOTAL", "ANOM")
    assert RONI_HEADER == ("SEAS", "YR", "ANOM")
    with pytest.raises(ValueError, match="expected header 'SEAS YR TOTAL ANOM'"):
        parse_oni(RONI_TEXT)
    with pytest.raises(ValueError, match="expected header 'SEAS YR ANOM'"):
        parse_roni(ONI_TEXT)


def _oni_lines(*rows: str) -> str:
    return "\n".join([" SEAS  YR   TOTAL   ANOM", *rows]) + "\n"


GOOD_ROWS = (
    "  DJF 1950  25.01  -1.32",  # oni.ascii.txt line 2
    "  JFM 1950  25.36  -1.20",  # line 3
    "  FMA 1950  25.88  -1.12",  # line 4
)


def test_synthetic_rows_parse():
    frame = parse_oni(_oni_lines(*GOOD_ROWS))
    assert frame["date"].tolist() == ["1950-01-01", "1950-02-01", "1950-03-01"]
    assert frame["value"].tolist() == [-1.32, -1.20, -1.12]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ((), "empty"),
        ((GOOD_ROWS[0], "  XYZ 1950  25.36  -1.20"), "unknown season 'XYZ'"),
        ((GOOD_ROWS[0], "  JFM 50  25.36  -1.20"), "bad year '50'"),
        ((GOOD_ROWS[0], "  JFM 1950  25.36  -1.2"), "bad value '-1.2'"),
        ((GOOD_ROWS[0], "  JFM 1950  abc  -1.20"), "bad value 'abc'"),
        ((GOOD_ROWS[0], "  JFM 1950  -1.20"), "has 3 fields, expected 4"),
        ((GOOD_ROWS[0], GOOD_ROWS[2]), "not contiguous at line 3"),
        ((GOOD_ROWS[0], GOOD_ROWS[0]), "not contiguous at line 3"),
        ((GOOD_ROWS[1], GOOD_ROWS[0]), "not contiguous at line 3"),
        ((GOOD_ROWS[0], "", GOOD_ROWS[1]), "has 0 fields, expected 4"),
    ],
)
def test_anomalies_raise(rows, message):
    text = _oni_lines(*rows) if rows else ""
    with pytest.raises(ValueError, match=message):
        parse_oni(text)


def test_total_column_is_checked_but_not_emitted():
    frame = parse_oni(_oni_lines(*GOOD_ROWS))
    assert "TOTAL" not in frame.columns
    with pytest.raises(ValueError, match="bad value '25.0'"):
        parse_oni(_oni_lines("  DJF 1950  25.0  -1.32"))
