"""Tests for the tidy long-format data contract in src/schema.py."""

import numpy as np
import pandas as pd
import pytest

from src import schema


def good_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_id": ["noaa_oni", "noaa_oni", "worldbank_pink_sheet"],
            "series_id": ["ONI", "ONI", "COFFEE_ARABIC"],
            "region": ["NINO3.4", "NINO3.4", "global"],
            "date": ["1997-12-01", "1998-01-01", "2024-01-01"],
            "value": [2.4, 2.2, 4.1],
            "unit": ["degC", "degC", "$/kg"],
            "retrieved_at": ["2026-09-05T17:00:00Z"] * 3,
            "licence_id": ["LicenseRef-US-PD", "LicenseRef-US-PD", "CC-BY-4.0"],
        }
    )


def test_columns_are_the_contract():
    assert schema.COLUMNS == (
        "source_id",
        "series_id",
        "region",
        "date",
        "value",
        "unit",
        "retrieved_at",
        "licence_id",
    )


def test_valid_frame_passes_and_is_returned_unchanged():
    df = good_frame()
    out = schema.validate_frame(df)
    assert out is df


def test_column_order_is_irrelevant():
    df = good_frame()[list(reversed(schema.COLUMNS))]
    schema.validate_frame(df)


def test_plus_zero_offset_is_accepted_as_utc():
    df = good_frame()
    df["retrieved_at"] = "2026-09-05T17:00:00+00:00"
    schema.validate_frame(df)


def test_not_a_dataframe():
    with pytest.raises(ValueError, match="expected a pandas DataFrame"):
        schema.validate_frame({"source_id": []})


def test_missing_column():
    df = good_frame().drop(columns=["unit"])
    with pytest.raises(ValueError, match=r"missing required columns: \['unit'\]"):
        schema.validate_frame(df)


def test_extra_column():
    df = good_frame().assign(note="x")
    with pytest.raises(ValueError, match=r"unexpected columns: \['note'\]"):
        schema.validate_frame(df)


def test_empty_frame():
    df = good_frame().iloc[0:0]
    with pytest.raises(ValueError, match="frame has no rows"):
        schema.validate_frame(df)


def test_unknown_source_id():
    df = good_frame()
    df.loc[0, "source_id"] = "not_a_source"
    with pytest.raises(ValueError, match=r"source_id not in src/sources.yaml: \['not_a_source'\]"):
        schema.validate_frame(df)


def test_superseded_source_id_is_rejected():
    df = good_frame()
    df.loc[0, "source_id"] = "imf_pcps"
    with pytest.raises(ValueError, match="approved or conditional.*imf_pcps.*superseded"):
        schema.validate_frame(df)


def test_licence_id_must_match_registry_entry():
    df = good_frame()
    df.loc[0, "licence_id"] = "US-PD"
    message = (
        r"licence_id for source_id 'noaa_oni' must be 'LicenseRef-US-PD' as recorded in "
        r"src/sources\.yaml; got \['LicenseRef-US-PD', 'US-PD'\]"
    )
    with pytest.raises(ValueError, match=message):
        schema.validate_frame(df)


def test_licence_id_is_checked_per_source():
    df = good_frame()
    df.loc[2, "licence_id"] = "LicenseRef-US-PD"
    with pytest.raises(ValueError, match="source_id 'worldbank_pink_sheet' must be 'CC-BY-4.0'"):
        schema.validate_frame(df)


def test_registry_entry_without_licence_id_is_rejected(monkeypatch):
    entries = {sid: dict(entry) for sid, entry in schema.registry().items()}
    entries["noaa_oni"]["licence_id"] = None
    monkeypatch.setattr(schema, "registry", lambda: entries)
    with pytest.raises(ValueError, match="registry entry 'noaa_oni' has no licence_id"):
        schema.validate_frame(good_frame())


def test_registry_licence_ids_are_read_from_sources_yaml():
    entries = schema.registry()
    assert entries["noaa_oni"]["licence_id"] == "LicenseRef-US-PD"
    assert entries["worldbank_pink_sheet"]["licence_id"] == "CC-BY-4.0"


def test_null_string_column():
    df = good_frame()
    df.loc[1, "region"] = None
    with pytest.raises(ValueError, match="column 'region' contains null values"):
        schema.validate_frame(df)


def test_empty_string_is_rejected():
    df = good_frame()
    df.loc[1, "licence_id"] = "  "
    with pytest.raises(ValueError, match="column 'licence_id' must contain non-empty strings"):
        schema.validate_frame(df)


def test_date_wrong_format():
    df = good_frame()
    df.loc[0, "date"] = "1997-12"
    with pytest.raises(ValueError, match=r"column 'date' must be YYYY-MM-DD; row 0: '1997-12'"):
        schema.validate_frame(df)


def test_date_impossible_calendar_day():
    df = good_frame()
    df.loc[0, "date"] = "1997-02-30"
    with pytest.raises(ValueError, match="invalid date at row 0"):
        schema.validate_frame(df)


def test_value_must_be_float_dtype():
    df = good_frame()
    df["value"] = ["2.4", "2.2", "4.1"]
    with pytest.raises(ValueError, match="column 'value' must have a float dtype"):
        schema.validate_frame(df)


def test_value_nan_rejected():
    df = good_frame()
    df.loc[2, "value"] = np.nan
    with pytest.raises(ValueError, match="column 'value' contains NaN at row 2"):
        schema.validate_frame(df)


def test_value_inf_rejected():
    df = good_frame()
    df.loc[2, "value"] = np.inf
    with pytest.raises(ValueError, match="non-finite value at row 2"):
        schema.validate_frame(df)


def test_retrieved_at_naive_rejected():
    df = good_frame()
    df.loc[0, "retrieved_at"] = "2026-09-05T17:00:00"
    with pytest.raises(ValueError, match="column 'retrieved_at' must be a UTC ISO 8601"):
        schema.validate_frame(df)


def test_retrieved_at_non_utc_offset_rejected():
    df = good_frame()
    df.loc[0, "retrieved_at"] = "2026-09-05T17:00:00+01:00"
    with pytest.raises(ValueError, match="column 'retrieved_at' must be a UTC ISO 8601"):
        schema.validate_frame(df)


def test_duplicate_key_rejected():
    df = good_frame()
    df.loc[1, "date"] = "1997-12-01"
    with pytest.raises(ValueError, match="duplicate key"):
        schema.validate_frame(df)
