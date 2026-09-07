"""Tests for the Pink Sheet parser in src/fetchers/worldbank_pink_sheet.py.

Every expected number is copied from a cell of the committed fixture
tests/fixtures/worldbank_pink_sheet/CMO-Historical-Data-Monthly.xlsx,
sheet "Monthly Prices", quoted as a cell reference beside it.
"""

import io
from pathlib import Path

import pytest
from openpyxl import Workbook

from src.fetchers.worldbank_pink_sheet import (
    DEFAULT_SUBSET,
    SHEET_NAME,
    parse_pink_sheet,
    registered_series,
)
from src.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "worldbank_pink_sheet"
XLSX = (FIXTURE / "CMO-Historical-Data-Monthly.xlsx").read_bytes()
RETRIEVED_AT = "2026-09-07T14:31:37Z"

# Sheet "Monthly Prices": names in row 5, units in row 6, data in rows 7
# to 806, periods 1960M01 (A7) to 2026M08 (A806): 800 months per series.
MONTHS = 800


def test_fixture_parses_to_a_valid_complete_frame():
    frame = parse_pink_sheet(XLSX, retrieved_at=RETRIEVED_AT)
    validate_frame(frame)
    assert list(frame.columns) == list(COLUMNS)
    assert len(frame) == MONTHS * len(DEFAULT_SUBSET)
    assert frame.groupby("series_id").size().to_dict() == dict.fromkeys(DEFAULT_SUBSET, MONTHS)
    assert list(dict.fromkeys(frame["series_id"])) == list(DEFAULT_SUBSET)
    assert set(frame["source_id"]) == {"worldbank_pink_sheet"}
    assert set(frame["region"]) == {"global"}
    assert set(frame["retrieved_at"]) == {RETRIEVED_AT}
    assert set(frame["licence_id"]) == {"CC-BY-4.0"}
    for _series_id, rows in frame.groupby("series_id"):
        assert rows["date"].iloc[0] == "1960-01-01"  # A7 is "1960M01"
        assert rows["date"].iloc[-1] == "2026-08-01"  # A806 is "2026M08"
        assert rows["date"].is_monotonic_increasing


def test_units_come_from_row_six():
    frame = parse_pink_sheet(XLSX)
    units = frame.groupby("series_id")["unit"].first().to_dict()
    assert units == {
        "COFFEE_ARABIC": "$/kg",  # M6 "($/kg)"
        "COFFEE_ROBUS": "$/kg",  # N6 "($/kg)"
        "COCOA": "$/kg",  # L6 "($/kg)"
        "SUGAR_WLD": "$/kg",  # AV6 "($/kg)"
        "RICE_05": "$/mt",  # AG6 "($/mt)"
    }
    assert units == {s["code"]: s["unit"] for s in registered_series().values()}


def test_spot_values():
    frame = parse_pink_sheet(XLSX).set_index(["series_id", "date"])["value"]
    assert frame["COFFEE_ARABIC", "1960-01-01"] == 0.94  # M7 (row "1960M01")
    assert frame["RICE_05", "2026-08-01"] == 471  # AG806 (row "2026M08")
    assert frame["COCOA", "1997-12-01"] == 1.74  # L462 (row "1997M12")
    assert frame["SUGAR_WLD", "2015-12-01"] == 0.32  # AV678 (row "2015M12")
    assert frame["COFFEE_ROBUS", "2026-08-01"] == 3.98  # N806 (row "2026M08")
    assert frame["COFFEE_ARABIC", "2026-08-01"] == 7.97  # M806 (row "2026M08")


def test_series_names_are_matched_after_stripping_whitespace():
    # AG5 holds "Rice, Thai 5% " with a trailing space; the registry name has none.
    frame = parse_pink_sheet(XLSX, series_codes=["RICE_05"])
    assert len(frame) == MONTHS
    assert frame["value"].iloc[0] == 104.5  # AG7 (row "1960M01")


def test_subset_keeps_the_requested_order():
    frame = parse_pink_sheet(XLSX, series_codes=("RICE_05", "COCOA"))
    assert list(dict.fromkeys(frame["series_id"])) == ["RICE_05", "COCOA"]
    assert len(frame) == 2 * MONTHS


def test_unknown_code_raises():
    with pytest.raises(ValueError, match="series code 'WHEAT' is not recorded"):
        parse_pink_sheet(XLSX, series_codes=["WHEAT"])
    with pytest.raises(ValueError, match="at least one series"):
        parse_pink_sheet(XLSX, series_codes=[])


def workbook_bytes(rows: list[list], sheet: str = SHEET_NAME) -> bytes:
    """A workbook with the Pink Sheet layout: four title rows, names, units, data."""
    book = Workbook()
    ws = book.active
    ws.title = sheet
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


TITLES = [
    ["World Bank Commodity Price Data (The Pink Sheet)"],
    ["monthly"],
    ["(nominal)"],
    ["Updated"],
]
NAMES = [None, "Cocoa", "Coffee, Arabica"]
UNITS = [None, "($/kg)", "($/kg)"]


TWO = ["COCOA", "COFFEE_ARABIC"]


def synthetic(*data: list) -> bytes:
    return workbook_bytes([*TITLES, NAMES, UNITS, *data])


def test_synthetic_workbook_parses():
    frame = parse_pink_sheet(
        synthetic(["1960M01", 0.63, 0.94], ["1960M02", 0.61, 0.95]),
        series_codes=["COCOA", "COFFEE_ARABIC"],
    )
    assert frame["date"].tolist() == ["1960-01-01", "1960-02-01"] * 2
    assert frame["value"].tolist() == [0.63, 0.61, 0.94, 0.95]


def test_unavailable_markers_are_omitted():
    frame = parse_pink_sheet(
        synthetic(["1960M01", "…", 0.94], ["1960M02", "...", 0.95], ["1960M03", 0.6, 0.96]),
        series_codes=["COCOA", "COFFEE_ARABIC"],
    )
    cocoa = frame[frame["series_id"] == "COCOA"]
    assert cocoa["date"].tolist() == ["1960-03-01"]
    assert len(frame[frame["series_id"] == "COFFEE_ARABIC"]) == 3


def test_missing_sheet_raises():
    with pytest.raises(ValueError, match="no sheet 'Monthly Prices'"):
        parse_pink_sheet(workbook_bytes([*TITLES, NAMES, UNITS], sheet="Other"))


def test_missing_series_name_raises():
    with pytest.raises(ValueError, match=r"'RICE_05' \('Rice, Thai 5%'\) not found in row 5"):
        parse_pink_sheet(synthetic(["1960M01", 0.63, 0.94]), series_codes=["RICE_05"])


def test_unit_mismatch_raises():
    book = workbook_bytes([*TITLES, NAMES, [None, "($/mt)", "($/kg)"], ["1960M01", 630, 0.94]])
    with pytest.raises(ValueError, match="unit of 'COCOA' is '\\$/mt' in the workbook"):
        parse_pink_sheet(book, series_codes=["COCOA"])


def test_unit_not_in_parentheses_raises():
    book = workbook_bytes([*TITLES, NAMES, [None, "$/kg", "($/kg)"], ["1960M01", 0.63, 0.94]])
    with pytest.raises(ValueError, match="cell B6 should hold the unit of 'COCOA'"):
        parse_pink_sheet(book, series_codes=["COCOA"])


@pytest.mark.parametrize("cell", ["#VALUE!", None, True, "n.a."])
def test_other_non_numeric_cells_raise(cell):
    with pytest.raises(ValueError, match="cell B7 for 'COCOA' is not a number"):
        parse_pink_sheet(synthetic(["1960M01", cell, 0.94]), series_codes=["COCOA"])


@pytest.mark.parametrize("period", ["1960-01", "1960M13", "1960M00", 1960])
def test_bad_periods_raise(period):
    with pytest.raises(ValueError, match="cell A8"):
        parse_pink_sheet(synthetic(["1960M01", 0.63, 0.94], [period, 0.6, 0.9]), series_codes=TWO)


def test_gaps_and_duplicates_raise():
    with pytest.raises(ValueError, match="not contiguous at cell A8"):
        parse_pink_sheet(
            synthetic(["1960M01", 0.63, 0.94], ["1960M03", 0.6, 0.9]), series_codes=TWO
        )
    with pytest.raises(ValueError, match="not contiguous at cell A8"):
        parse_pink_sheet(
            synthetic(["1960M01", 0.63, 0.94], ["1960M01", 0.6, 0.9]), series_codes=TWO
        )


def test_data_after_a_blank_row_raises():
    rows = synthetic(["1960M01", 0.63, 0.94], [None, None, None], ["Source", 1, 2])
    with pytest.raises(ValueError, match="row 9 has data after a blank row"):
        parse_pink_sheet(rows, series_codes=TWO)


def test_no_data_rows_raises():
    with pytest.raises(ValueError, match="no data row with a YYYYMmm period"):
        parse_pink_sheet(workbook_bytes([*TITLES, NAMES, UNITS]))


def test_series_without_values_raises():
    with pytest.raises(ValueError, match="series 'COCOA' has no values"):
        parse_pink_sheet(synthetic(["1960M01", "…", 0.94]), series_codes=["COCOA"])
