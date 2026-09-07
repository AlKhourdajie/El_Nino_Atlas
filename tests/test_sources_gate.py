"""Gate tests enforcing the licence registry in src/sources.yaml."""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SOURCES_YAML = SRC / "sources.yaml"
FETCHERS_DIR = SRC / "fetchers"

VALID_STATUSES = {
    "approved",
    "conditional",
    "link-only",
    "excluded",
    "superseded",
    "pending",
}
VALID_REDISTRIBUTION = {"yes", "conditional", "no"}
REQUIRED_FIELDS = {
    "id",
    "name",
    "publisher",
    "url",
    "licence",
    "licence_id",
    "terms_url",
    "deep_url",
    "redistribution",
    "attribution",
    "cadence",
    "status",
    "reason",
    "notes",
}
# SPDX identifiers (CC-BY-4.0) or LicenseRef- identifiers (LicenseRef-US-PD).
LICENCE_ID_RE = re.compile(r"^(LicenseRef-)?[A-Za-z0-9][A-Za-z0-9.-]*$")
URL_RE = re.compile(r"^https?://\S+$")
PINK_SHEET_SERIES = [
    ("COFFEE_ARABIC", "Coffee, Arabica", "$/kg"),
    ("COFFEE_ROBUS", "Coffee, Robusta", "$/kg"),
    ("COCOA", "Cocoa", "$/kg"),
    ("SUGAR_WLD", "Sugar, world", "$/kg"),
    ("RICE_05", "Rice, Thai 5%", "$/mt"),
]
FETCHABLE_STATUSES = {"approved", "conditional"}
# Superseded is an editorial choice, not a licence bar, but for the fetcher
# gate it behaves exactly as excluded.
NON_FETCHABLE_STATUSES = VALID_STATUSES - FETCHABLE_STATUSES
EXCLUDED_NEEDLES = ("emdat", "em-dat")
SNAPSHOT_FILE_RE = re.compile(r"^data/snapshots/([^/]+)/(latest\.csv|latest\.json)$")


@pytest.fixture(scope="module")
def sources() -> dict[str, dict]:
    with SOURCES_YAML.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    entries = doc["sources"]
    by_id = {entry["id"]: entry for entry in entries}
    assert len(by_id) == len(entries), "duplicate source ids"
    return by_id


def test_registry_schema(sources):
    for source_id, entry in sources.items():
        missing = REQUIRED_FIELDS - set(entry)
        assert not missing, f"{source_id}: missing fields {sorted(missing)}"
        assert entry["status"] in VALID_STATUSES, f"{source_id}: bad status"
        assert str(entry["redistribution"]).lower() in VALID_REDISTRIBUTION, (
            f"{source_id}: bad redistribution"
        )
        assert entry["id"] == source_id
        reason = entry["reason"]
        assert isinstance(reason, str) and reason.strip(), f"{source_id}: empty reason"
        assert "\n" not in reason.strip(), f"{source_id}: reason must be one line"


def _urls(value) -> list:
    return list(value) if isinstance(value, list) else [value]


def test_licence_ids_and_links(sources):
    for source_id, entry in sources.items():
        licence_id = entry["licence_id"]
        if entry["status"] in FETCHABLE_STATUSES:
            assert isinstance(licence_id, str), f"{source_id}: fetchable entries need a licence_id"
        if licence_id is not None:
            assert LICENCE_ID_RE.match(licence_id), f"{source_id}: bad licence_id {licence_id!r}"
        for field in ("terms_url", "deep_url"):
            for url in _urls(entry[field]):
                assert url is None or URL_RE.match(url), f"{source_id}: bad {field} {url!r}"
        if entry["terms_url"] is None:
            assert "terms_url to verify" in entry["notes"], (
                f"{source_id}: notes must name the terms page to verify"
            )


def test_data_source_series_are_recorded(sources):
    assert sources["noaa_oni"]["series"] == ["ONI", "RONI"]
    assert sources["noaa_oni"]["deep_url"] == [
        "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt",
    ]
    pink = sources["worldbank_pink_sheet"]["series"]
    assert [(s["code"], s["name"], s["unit"]) for s in pink] == PINK_SHEET_SERIES
    assert sources["worldbank_pink_sheet"]["deep_url"] == sources["worldbank_pink_sheet"]["url"]


def test_approved_redistributable_sources(sources):
    approved = {
        sid
        for sid, e in sources.items()
        if e["status"] == "approved" and e["redistribution"] == "yes"
    }
    assert approved == {
        "noaa_oni",
        "worldbank_pink_sheet",
        "noaa_cpc_enso_impacts_schematic",
        "faostat",
    }
    assert sources["noaa_cpc_enso_impacts_schematic"]["licence_id"] == "LicenseRef-US-PD"


def test_every_fetcher_has_fetchable_source(sources):
    modules = [p.stem for p in FETCHERS_DIR.glob("*.py") if p.name != "__init__.py"]
    assert modules, "no fetcher modules found"
    for module in modules:
        assert module in sources, f"fetcher {module} has no entry in sources.yaml"
        status = sources[module]["status"]
        assert status not in NON_FETCHABLE_STATUSES, (
            f"fetcher {module} maps to status {status!r}; only "
            f"{sorted(FETCHABLE_STATUSES)} may have fetchers"
        )
        assert status in FETCHABLE_STATUSES


def test_superseded_and_excluded_have_no_fetcher(sources):
    modules = {p.stem for p in FETCHERS_DIR.glob("*.py") if p.name != "__init__.py"}
    barred = {sid for sid, e in sources.items() if e["status"] in {"excluded", "superseded"}}
    assert barred, "expected at least one excluded or superseded entry"
    assert not (modules & barred), f"fetchers exist for barred sources: {modules & barred}"


def test_no_excluded_source_referenced_under_src():
    offenders = []
    for path in SRC.rglob("*"):
        if not path.is_file() or path == SOURCES_YAML or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for needle in EXCLUDED_NEEDLES:
            if needle in text:
                offenders.append(f"{path.relative_to(ROOT)} mentions {needle!r}")
    assert not offenders, "\n".join(offenders)


def tracked_data_file_is_permitted(path: str, sources: dict[str, dict]) -> bool:
    """The rule for files under data/ in the git index.

    Human-curated files under data/curated/ and .gitkeep placeholders are
    always permitted. The snapshot pair data/snapshots/<source_id>/latest.csv
    and latest.json is permitted only when that source has status approved
    and redistribution "yes". Nothing else under data/ may be tracked.
    """
    if Path(path).name == ".gitkeep" or path.startswith("data/curated/"):
        return True
    match = SNAPSHOT_FILE_RE.match(path)
    if not match:
        return False
    entry = sources.get(match.group(1))
    return (
        entry is not None
        and entry["status"] == "approved"
        and str(entry["redistribution"]).lower() == "yes"
    )


def test_no_data_files_tracked_in_git(sources):
    tracked = subprocess.run(
        ["git", "ls-files", "data"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    offenders = [p for p in tracked if not tracked_data_file_is_permitted(p, sources)]
    assert not offenders, f"data files must not be committed: {offenders}"


@pytest.mark.parametrize(
    ("path", "permitted"),
    [
        ("data/curated/activations.yaml", True),
        ("data/raw/.gitkeep", True),
        ("data/snapshots/noaa_oni/latest.csv", True),
        ("data/snapshots/noaa_oni/latest.json", True),
        ("data/snapshots/worldbank_pink_sheet/latest.csv", True),
        ("data/snapshots/noaa_cpc_enso_impacts_schematic/latest.json", True),
        ("data/snapshots/noaa_oni/2026-09.csv", False),
        ("data/snapshots/noaa_oni/raw/oni.ascii.txt", False),
        ("data/snapshots/fews_net/latest.csv", False),
        ("data/snapshots/imf_pcps/latest.csv", False),
        ("data/snapshots/idmc/latest.json", False),
        ("data/snapshots/not_a_source/latest.csv", False),
        ("data/raw/oni.ascii.txt", False),
        ("data/processed/oni.csv", False),
    ],
)
def test_tracked_data_file_rule(sources, path, permitted):
    assert tracked_data_file_is_permitted(path, sources) is permitted
