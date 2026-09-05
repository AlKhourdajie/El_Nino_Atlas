"""Gate tests enforcing the licence registry in src/sources.yaml."""

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
    "redistribution",
    "attribution",
    "cadence",
    "status",
    "reason",
    "notes",
}
FETCHABLE_STATUSES = {"approved", "conditional"}
# Superseded is an editorial choice, not a licence bar, but for the fetcher
# gate it behaves exactly as excluded.
NON_FETCHABLE_STATUSES = VALID_STATUSES - FETCHABLE_STATUSES
EXCLUDED_NEEDLES = ("emdat", "em-dat")


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


def test_no_data_files_tracked_in_git():
    tracked = subprocess.run(
        ["git", "ls-files", "data"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    # Human-curated files under data/curated/ are the one tracked exception.
    offenders = [
        p for p in tracked if Path(p).name != ".gitkeep" and not p.startswith("data/curated/")
    ]
    assert not offenders, f"data files must not be committed: {offenders}"
