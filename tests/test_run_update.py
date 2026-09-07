"""Tests for ``python run.py update`` and the fetcher plumbing, without the network.

Live downloads are replaced by fakes; the parse functions run on the
committed fixtures.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

import run
from src import data_access
from src.fetchers import (
    REGISTERED_FETCHERS,
    Fetched,
    download,
    noaa_oni,
    sha256_hex,
    snapshot_metadata,
    worldbank_pink_sheet,
)
from src.schema import registry

FIXTURES = Path(__file__).parent / "fixtures"
ONI_BYTES = (FIXTURES / "noaa_oni" / "oni.ascii.txt").read_bytes()
RONI_BYTES = (FIXTURES / "noaa_oni" / "RONI.ascii.txt").read_bytes()
XLSX_BYTES = (FIXTURES / "worldbank_pink_sheet" / "CMO-Historical-Data-Monthly.xlsx").read_bytes()
RETRIEVED_AT = "2026-09-07T14:30:23Z"


def fetched(url: str, content: bytes, retrieved_at: str = RETRIEVED_AT) -> Fetched:
    return Fetched(url=url, content=content, sha256=sha256_hex(content), retrieved_at=retrieved_at)


def oni_fetched() -> tuple[Fetched, ...]:
    return (fetched(noaa_oni.ONI_URL, ONI_BYTES), fetched(noaa_oni.RONI_URL, RONI_BYTES))


@pytest.fixture(autouse=True)
def snapshot_root(tmp_path, monkeypatch):
    root = tmp_path / "snapshots"
    monkeypatch.setattr(data_access, "SNAPSHOT_ROOT", root)
    return root


def test_registry_maps_each_source_to_fetch_and_parse():
    assert set(REGISTERED_FETCHERS) == {"noaa_oni", "worldbank_pink_sheet"}
    assert REGISTERED_FETCHERS["noaa_oni"] == (noaa_oni.fetch, noaa_oni.parse)
    assert REGISTERED_FETCHERS["worldbank_pink_sheet"] == (
        worldbank_pink_sheet.fetch,
        worldbank_pink_sheet.parse,
    )


def test_fetch_urls_match_the_registry_deep_links():
    assert [noaa_oni.ONI_URL, noaa_oni.RONI_URL] == registry()["noaa_oni"]["deep_url"]
    assert worldbank_pink_sheet.DURABLE_URL == registry()["worldbank_pink_sheet"]["deep_url"]


def test_download_refuses_hosts_outside_the_permitted_set():
    with pytest.raises(ValueError, match="refusing to download from host 'example.org'"):
        download("https://example.org/oni.ascii.txt", noaa_oni.ALLOWED_HOSTS)


def test_noaa_parse_joins_both_indices():
    frame = noaa_oni.parse(oni_fetched())
    assert len(frame) == 2 * 919  # 919 season rows in each fixture
    assert sorted(set(frame["series_id"])) == ["ONI", "RONI"]
    assert set(frame["retrieved_at"]) == {RETRIEVED_AT}


def test_noaa_parse_requires_both_files_in_order():
    oni, roni = oni_fetched()
    with pytest.raises(ValueError, match="expected the ONI and RONI files in that order"):
        noaa_oni.parse((roni, oni))
    with pytest.raises(ValueError, match="expected the ONI and RONI files in that order"):
        noaa_oni.parse((oni,))


def test_pink_sheet_parse_reads_the_fetched_workbook():
    frame = worldbank_pink_sheet.parse(
        (fetched("https://thedocs.worldbank.org/x/CMO-Historical-Data-Monthly.xlsx", XLSX_BYTES),)
    )
    assert len(frame) == 5 * 800
    with pytest.raises(ValueError, match="exactly one fetched workbook"):
        worldbank_pink_sheet.parse(())


PAGE = (
    '<a href="https://thedocs.worldbank.org/en/doc/abc-0050012026/related/'
    'CMO-Historical-Data-Monthly.xlsx">Monthly prices</a>'
    '<a href="https://thedocs.worldbank.org/en/doc/abc-0050012026/related/'
    'CMO-Historical-Data-Annual.xlsx">Annual prices</a>'
)


def test_resolve_workbook_url_finds_the_monthly_link():
    assert worldbank_pink_sheet.resolve_workbook_url(PAGE) == (
        "https://thedocs.worldbank.org/en/doc/abc-0050012026/related/"
        "CMO-Historical-Data-Monthly.xlsx"
    )


def test_resolve_workbook_url_accepts_the_same_link_twice_and_relative_links():
    twice = PAGE + PAGE
    assert worldbank_pink_sheet.resolve_workbook_url(twice).endswith("Monthly.xlsx")
    relative = '<a href="/related/CMO-Historical-Data-Monthly.xlsx?x=1&amp;y=2">m</a>'
    assert worldbank_pink_sheet.resolve_workbook_url(relative) == (
        "https://www.worldbank.org/related/CMO-Historical-Data-Monthly.xlsx?x=1&y=2"
    )


def test_resolve_workbook_url_raises_without_a_match():
    with pytest.raises(ValueError, match="no link to CMO-Historical-Data-Monthly.xlsx"):
        worldbank_pink_sheet.resolve_workbook_url('<a href="/other.xlsx">x</a>')


def test_resolve_workbook_url_raises_on_ambiguity_and_foreign_hosts():
    two = PAGE + '<a href="https://thedocs.worldbank.org/other/CMO-Historical-Data-Monthly.xlsx">'
    with pytest.raises(ValueError, match="2 different links"):
        worldbank_pink_sheet.resolve_workbook_url(two)
    foreign = '<a href="https://example.org/CMO-Historical-Data-Monthly.xlsx">m</a>'
    with pytest.raises(ValueError, match="outside"):
        worldbank_pink_sheet.resolve_workbook_url(foreign)


def test_snapshot_metadata_describes_the_files_and_frame():
    files = oni_fetched()
    frame = noaa_oni.parse(files)
    meta = snapshot_metadata("noaa_oni", files, frame)
    assert set(data_access.REQUIRED_METADATA_KEYS) <= set(meta)
    assert meta["source_id"] == "noaa_oni"
    assert meta["source_url"] == noaa_oni.ONI_URL
    assert meta["raw_sha256"] == sha256_hex(ONI_BYTES)
    assert meta["retrieved_at"] == RETRIEVED_AT
    assert [f["url"] for f in meta["files"]] == [noaa_oni.ONI_URL, noaa_oni.RONI_URL]
    assert meta["files"][1]["sha256"] == sha256_hex(RONI_BYTES)
    assert meta["files"][0]["bytes"] == len(ONI_BYTES)
    assert meta["licence_id"] == "LicenseRef-US-PD"
    assert meta["attribution"] == registry()["noaa_oni"]["attribution"]
    assert meta["row_count"] == 2 * 919
    assert meta["series_ids"] == ["ONI", "RONI"]
    assert (meta["first_date"], meta["last_date"]) == ("1950-01-01", "2026-07-01")
    with pytest.raises(ValueError, match="no files were fetched"):
        snapshot_metadata("noaa_oni", (), frame)


def test_update_reports_no_fetchers(monkeypatch, capsys):
    monkeypatch.setattr(run, "REGISTERED_FETCHERS", {})
    assert run.main(["update"]) == 0
    assert capsys.readouterr().out.strip() == "no fetchers registered"


def test_update_writes_then_reports_unchanged(monkeypatch, capsys, snapshot_root):
    monkeypatch.setattr(run, "REGISTERED_FETCHERS", {"noaa_oni": (oni_fetched, noaa_oni.parse)})

    assert run.main(["update"]) == 0
    assert capsys.readouterr().out.strip() == "noaa_oni: written"
    csv_path = snapshot_root / "noaa_oni" / "latest.csv"
    json_path = snapshot_root / "noaa_oni" / "latest.json"
    assert csv_path.is_file() and json_path.is_file()
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    assert meta["row_count"] == 2 * 919
    assert data_access.snapshot_metadata("noaa_oni") == meta
    assert len(data_access.load_frame("noaa_oni")) == 2 * 919

    assert run.main(["update"]) == 0
    assert capsys.readouterr().out.strip() == "noaa_oni: unchanged"


def test_update_keeps_going_and_exits_non_zero_on_failure(monkeypatch, capsys, snapshot_root):
    def broken_fetch() -> tuple[Fetched, ...]:
        raise ConnectionError("no route to host")

    def good_parse(fetched: tuple[Fetched, ...]) -> pd.DataFrame:
        return noaa_oni.parse(fetched)

    monkeypatch.setattr(
        run,
        "REGISTERED_FETCHERS",
        {"worldbank_pink_sheet": (broken_fetch, good_parse), "noaa_oni": (oni_fetched, good_parse)},
    )
    assert run.main(["update"]) == 1
    captured = capsys.readouterr()
    assert captured.out.strip() == "noaa_oni: written"
    assert "worldbank_pink_sheet: failed: ConnectionError: no route to host" in captured.err
    assert (snapshot_root / "noaa_oni" / "latest.csv").is_file()
    assert not (snapshot_root / "worldbank_pink_sheet").exists()


def test_update_rejects_an_invalid_frame(monkeypatch, capsys, snapshot_root):
    def bad_parse(fetched: tuple[Fetched, ...]) -> pd.DataFrame:
        return noaa_oni.parse(fetched).drop(columns=["unit"])

    monkeypatch.setattr(run, "REGISTERED_FETCHERS", {"noaa_oni": (oni_fetched, bad_parse)})
    assert run.main(["update"]) == 1
    assert "noaa_oni: failed: ValueError: missing required columns" in capsys.readouterr().err
    assert not snapshot_root.exists()
