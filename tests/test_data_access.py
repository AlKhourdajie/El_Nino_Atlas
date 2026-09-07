"""Tests for the snapshot data access contract in src/data_access.py."""

import json

import pandas as pd
import pytest

from src import data_access
from src.schema import COLUMNS

RETRIEVED_AT = "2026-09-05T17:00:00Z"


@pytest.fixture(autouse=True)
def snapshot_root(tmp_path, monkeypatch):
    root = tmp_path / "snapshots"
    monkeypatch.setattr(data_access, "SNAPSHOT_ROOT", root)
    return root


def oni_frame(values: list[float] | None = None) -> pd.DataFrame:
    values = values if values is not None else [2.4, 2.2, 1.9]
    return pd.DataFrame(
        {
            "source_id": "noaa_oni",
            "series_id": "oni",
            "region": "nino34",
            "date": ["1997-12-01", "1998-01-01", "1998-02-01"][: len(values)],
            "value": [float(v) for v in values],
            "unit": "degC",
            "retrieved_at": RETRIEVED_AT,
            "licence_id": "US-PD",
        }
    )


def metadata(frame: pd.DataFrame, source_id: str = "noaa_oni", **overrides) -> dict:
    base = {
        "source_id": source_id,
        "retrieved_at": RETRIEVED_AT,
        "source_url": "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "raw_sha256": "0" * 64,
        "licence_id": "US-PD",
        "attribution": "Source: NOAA Climate Prediction Center, Oceanic Niño Index (ONI)",
        "row_count": len(frame),
        "series_ids": sorted(set(frame["series_id"])),
    }
    base.update(overrides)
    return base


def test_round_trip(snapshot_root):
    frame = oni_frame()
    meta = metadata(frame)

    assert data_access.write_snapshot("noaa_oni", frame, meta) is True
    csv_path = snapshot_root / "noaa_oni" / "latest.csv"
    json_path = snapshot_root / "noaa_oni" / "latest.json"
    assert csv_path.is_file() and json_path.is_file()

    raw = csv_path.read_bytes()
    assert b"\r\n" not in raw
    assert raw.decode("utf-8").splitlines()[0] == ",".join(COLUMNS)
    assert raw.decode("utf-8").splitlines()[1].startswith("noaa_oni,oni,nino34,1997-12-01,2.4,")

    loaded = data_access.load_frame("noaa_oni")
    assert list(loaded.columns) == list(COLUMNS)
    assert loaded.to_dict("list") == frame.to_dict("list")
    assert data_access.snapshot_metadata("noaa_oni") == meta
    assert json.loads(json_path.read_text(encoding="utf-8")) == meta


def test_unchanged_data_writes_nothing(snapshot_root):
    frame = oni_frame()
    assert data_access.write_snapshot("noaa_oni", frame, metadata(frame)) is True
    csv_path = snapshot_root / "noaa_oni" / "latest.csv"
    json_path = snapshot_root / "noaa_oni" / "latest.json"
    csv_before, json_before = csv_path.read_bytes(), json_path.read_bytes()

    later = metadata(frame, retrieved_at="2026-09-06T17:00:00Z", raw_sha256="1" * 64)
    assert data_access.write_snapshot("noaa_oni", frame.copy(), later) is False

    assert csv_path.read_bytes() == csv_before
    assert json_path.read_bytes() == json_before
    assert data_access.snapshot_metadata("noaa_oni")["retrieved_at"] == RETRIEVED_AT


def test_changed_data_is_written(snapshot_root):
    frame = oni_frame()
    assert data_access.write_snapshot("noaa_oni", frame, metadata(frame)) is True

    changed = oni_frame([2.4, 2.2, 2.0])
    later = metadata(changed, retrieved_at="2026-10-05T17:00:00Z")
    assert data_access.write_snapshot("noaa_oni", changed, later) is True

    assert data_access.load_frame("noaa_oni")["value"].tolist() == [2.4, 2.2, 2.0]
    assert data_access.snapshot_metadata("noaa_oni")["retrieved_at"] == "2026-10-05T17:00:00Z"


def test_missing_snapshot_raises():
    message = r"No snapshot for noaa_oni\. Run: python run\.py update"
    with pytest.raises(FileNotFoundError, match=message):
        data_access.load_frame("noaa_oni")
    with pytest.raises(FileNotFoundError, match=message):
        data_access.snapshot_metadata("noaa_oni")


def test_non_approved_source_refused(snapshot_root):
    # fews_net is fetchable (conditional) so the frame itself is valid; the
    # snapshot rule is stricter and must refuse it.
    frame = oni_frame().assign(source_id="fews_net", series_id="ipc_phase", licence_id="custom")
    with pytest.raises(ValueError, match="status 'approved' and redistribution 'yes'"):
        data_access.write_snapshot("fews_net", frame, metadata(frame, source_id="fews_net"))
    assert not (snapshot_root / "fews_net").exists()


def test_unknown_source_refused(snapshot_root):
    frame = oni_frame()
    with pytest.raises(ValueError, match="not in src/sources.yaml"):
        data_access.write_snapshot("not_a_source", frame, metadata(frame, source_id="not_a_source"))
    assert not snapshot_root.exists()


def test_frame_must_belong_to_source(snapshot_root):
    frame = oni_frame()
    meta = metadata(frame, source_id="worldbank_pink_sheet")
    with pytest.raises(ValueError, match="every row must have source_id 'worldbank_pink_sheet'"):
        data_access.write_snapshot("worldbank_pink_sheet", frame, meta)
    assert not snapshot_root.exists()


def test_invalid_frame_refused(snapshot_root):
    frame = oni_frame().drop(columns=["unit"])
    with pytest.raises(ValueError, match="missing required columns"):
        data_access.write_snapshot("noaa_oni", frame, metadata(frame))
    assert not snapshot_root.exists()


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"raw_sha256": None}, "missing required keys"),
        ({"source_id": "worldbank_pink_sheet"}, "does not match 'noaa_oni'"),
        ({"retrieved_at": "2026-09-05T17:00:00"}, "UTC ISO 8601"),
        ({"row_count": 2}, "does not match 3 rows"),
        ({"series_ids": ["oni", "extra"]}, "do not match"),
    ],
)
def test_bad_metadata_refused(snapshot_root, override, message):
    frame = oni_frame()
    meta = metadata(frame)
    for key, value in override.items():
        if value is None:
            del meta[key]
        else:
            meta[key] = value
    with pytest.raises(ValueError, match=message):
        data_access.write_snapshot("noaa_oni", frame, meta)
    assert not snapshot_root.exists()


def test_na_region_survives_round_trip():
    # "NA" is the ISO code for Namibia and must not become a missing value.
    frame = oni_frame().assign(region="NA")
    data_access.write_snapshot("noaa_oni", frame, metadata(frame))
    assert data_access.load_frame("noaa_oni")["region"].tolist() == ["NA"] * 3
