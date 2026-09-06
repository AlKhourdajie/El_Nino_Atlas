"""Loader and validator for the hand-curated activation register.

``data/curated/activations.yaml`` is human-curated. This module only
reads it. Entries flagged ``example: true`` pass validation but are
excluded by ``load_activations`` unless ``include_examples`` is set;
the app must never render them.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

REGISTER_PATH = Path(__file__).resolve().parent.parent / "data" / "curated" / "activations.yaml"

REQUIRED_FIELDS: tuple[str, ...] = (
    "date",
    "region",
    "country",
    "framework",
    "agencies",
    "amount_usd",
    "people_covered",
    "trigger",
    "source_url",
    "retrieved_at",
)
OPTIONAL_FIELDS: tuple[str, ...] = ("example",)

_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


def _non_empty_string(entry: dict, field: str, label: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: {field!r} must be a non-empty string, got {value!r}")


def validate_activation(entry: Any, label: str = "activation") -> dict:
    """Validate one register entry; raise ``ValueError`` naming the fault."""
    if not isinstance(entry, dict):
        raise ValueError(f"{label}: entry must be a mapping, got {type(entry).__name__}")

    missing = [f for f in REQUIRED_FIELDS if f not in entry]
    if missing:
        raise ValueError(f"{label}: missing fields {missing}")
    unknown = sorted(set(entry) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if unknown:
        raise ValueError(f"{label}: unknown fields {unknown}")

    if "example" in entry and not isinstance(entry["example"], bool):
        raise ValueError(f"{label}: 'example' must be true or false")

    if not isinstance(entry["date"], date) or isinstance(entry["date"], datetime):
        raise ValueError(f"{label}: 'date' must be an ISO calendar date, got {entry['date']!r}")

    for field in ("region", "country", "framework", "trigger"):
        _non_empty_string(entry, field, label)

    agencies = entry["agencies"]
    if not isinstance(agencies, list) or not agencies:
        raise ValueError(f"{label}: 'agencies' must be a non-empty list")
    for i, agency in enumerate(agencies):
        if not isinstance(agency, str) or not agency.strip():
            raise ValueError(f"{label}: agencies[{i}] must be a non-empty string")

    for field in ("amount_usd", "people_covered"):
        value = entry[field]
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{label}: {field!r} must be a number or null, got {value!r}")
        if value < 0:
            raise ValueError(f"{label}: {field!r} must not be negative, got {value!r}")
    if entry["people_covered"] is not None and not isinstance(entry["people_covered"], int):
        raise ValueError(f"{label}: 'people_covered' must be an integer or null")

    _non_empty_string(entry, "source_url", label)
    if not entry["source_url"].startswith(("http://", "https://")):
        raise ValueError(
            f"{label}: 'source_url' must be an http(s) URL, got {entry['source_url']!r}"
        )

    retrieved = entry["retrieved_at"]
    if not isinstance(retrieved, str) or not _UTC_RE.match(retrieved):
        raise ValueError(
            f"{label}: 'retrieved_at' must be a UTC ISO 8601 string such as "
            f"2026-09-05T00:00:00Z, got {retrieved!r}"
        )

    return entry


def load_activations(path: Path = REGISTER_PATH, include_examples: bool = False) -> list[dict]:
    """Read and validate the register, dropping example entries by default."""
    with Path(path).open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or "activations" not in doc:
        raise ValueError(f"{path}: expected a top-level 'activations' list")
    entries = doc["activations"] or []
    if not isinstance(entries, list):
        raise ValueError(f"{path}: 'activations' must be a list")
    validated = [validate_activation(e, label=f"activations[{i}]") for i, e in enumerate(entries)]
    if include_examples:
        return validated
    return [e for e in validated if not e.get("example", False)]
