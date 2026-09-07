"""Snapshot data access: the contract between fetchers and the app.

A fetcher writes one snapshot per source under ``data/snapshots/<source_id>/``:

    latest.csv   the tidy contract frame of ``src/schema.py`` (schema
                 columns, ISO dates, UTF-8, LF line endings)
    latest.json  provenance metadata describing that CSV

The app only reads snapshots; it never fetches. A snapshot may be written
only for a source whose registry entry has status ``approved`` and
``redistribution: "yes"``, because tracked snapshots travel with the
repository. ``tests/test_sources_gate.py`` applies the same rule to the
git index.

``write_snapshot`` touches nothing when the CSV text is identical to the
snapshot already on disk, so a nightly run that finds no new data leaves
no diff.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from src.schema import COLUMNS, registry, validate_frame

SNAPSHOT_ROOT = Path("data/snapshots")

CSV_NAME = "latest.csv"
METADATA_NAME = "latest.json"

REQUIRED_METADATA_KEYS: tuple[str, ...] = (
    "source_id",
    "retrieved_at",
    "source_url",
    "raw_sha256",
    "licence_id",
    "attribution",
    "row_count",
    "series_ids",
)

_STRING_COLUMNS: tuple[str, ...] = tuple(c for c in COLUMNS if c != "value")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


def _missing(source_id: str) -> FileNotFoundError:
    return FileNotFoundError(f"No snapshot for {source_id}. Run: python run.py update")


def _snapshot_file(source_id: str, name: str) -> Path:
    path = SNAPSHOT_ROOT / source_id / name
    if not path.is_file():
        raise _missing(source_id)
    return path


def _require_redistributable(source_id: str) -> None:
    entry = registry().get(source_id)
    if entry is None:
        raise ValueError(f"source_id {source_id!r} is not in src/sources.yaml")
    status = entry["status"]
    redistribution = str(entry["redistribution"]).lower()
    if status != "approved" or redistribution != "yes":
        raise ValueError(
            "snapshots may be written only for sources with status 'approved' and "
            f"redistribution 'yes'; {source_id!r} has status {status!r} and "
            f"redistribution {redistribution!r}"
        )


def _require_frame_for(source_id: str, frame: pd.DataFrame) -> None:
    found = sorted(set(frame["source_id"]))
    if found != [source_id]:
        raise ValueError(f"every row must have source_id {source_id!r}; frame has {found}")


def _require_metadata(source_id: str, frame: pd.DataFrame, metadata: dict) -> None:
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata must be a dict, got {type(metadata).__name__}")
    missing = [key for key in REQUIRED_METADATA_KEYS if key not in metadata]
    if missing:
        raise ValueError(f"metadata is missing required keys {missing}")
    if metadata["source_id"] != source_id:
        raise ValueError(
            f"metadata source_id {metadata['source_id']!r} does not match {source_id!r}"
        )
    retrieved_at = metadata["retrieved_at"]
    if not isinstance(retrieved_at, str) or not _UTC_RE.match(retrieved_at):
        raise ValueError(
            "metadata 'retrieved_at' must be a UTC ISO 8601 timestamp such as "
            f"2026-09-05T17:00:00Z, got {retrieved_at!r}"
        )
    row_count = metadata["row_count"]
    if isinstance(row_count, bool) or row_count != len(frame):
        raise ValueError(f"metadata row_count {row_count!r} does not match {len(frame)} rows")
    series_ids = metadata["series_ids"]
    if not isinstance(series_ids, list | tuple):
        raise ValueError(f"metadata 'series_ids' must be a list, got {series_ids!r}")
    expected = sorted(set(frame["series_id"]))
    if sorted(series_ids) != expected:
        raise ValueError(f"metadata series_ids {sorted(series_ids)} do not match {expected}")


def _csv_text(frame: pd.DataFrame) -> str:
    return frame[list(COLUMNS)].to_csv(index=False, lineterminator="\n")


def write_snapshot(source_id: str, frame: pd.DataFrame, metadata: dict) -> bool:
    """Write ``latest.csv`` and ``latest.json`` for ``source_id``.

    Returns ``True`` when the files were written and ``False`` when the
    new CSV text is identical to the snapshot on disk, in which case
    neither file is touched. Raises ``ValueError`` on any contract
    violation before anything is written.
    """
    validate_frame(frame)
    _require_redistributable(source_id)
    _require_frame_for(source_id, frame)
    _require_metadata(source_id, frame, metadata)

    csv_text = _csv_text(frame)
    json_text = json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    target = SNAPSHOT_ROOT / source_id
    csv_path = target / CSV_NAME
    if csv_path.is_file() and csv_path.read_bytes().decode("utf-8") == csv_text:
        return False

    target.mkdir(parents=True, exist_ok=True)
    csv_path.write_bytes(csv_text.encode("utf-8"))
    (target / METADATA_NAME).write_bytes(json_text.encode("utf-8"))
    return True


def load_frame(source_id: str) -> pd.DataFrame:
    """Read and validate the latest snapshot frame for ``source_id``.

    Text columns are read as strings so ISO dates survive exactly as
    written and no value such as the ISO code "NA" becomes a missing
    value. Raises ``FileNotFoundError`` when no snapshot exists.
    """
    path = _snapshot_file(source_id, CSV_NAME)
    frame = pd.read_csv(
        path,
        encoding="utf-8",
        dtype={**{column: str for column in _STRING_COLUMNS}, "value": "float64"},
        keep_default_na=False,
        float_precision="round_trip",
    )
    return validate_frame(frame)


def snapshot_metadata(source_id: str) -> dict:
    """The provenance metadata written alongside the latest snapshot."""
    path = _snapshot_file(source_id, METADATA_NAME)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)
