"""Loader and validator for the hand-curated activation register.

``data/curated/activations.yaml`` is human-curated. This module only
reads it. Entries flagged ``example: true`` pass validation but are
excluded by ``load_activations`` unless ``include_examples`` is set;
the app must never render them.

Entry fields
------------
Every key is present in every entry; ``null`` records that the document
gives no value. Nothing is inferred.

id               stable key, unique across the register, lower case
                 letters, digits, underscores and hyphens
iso3             ISO 3166-1 alpha-3 code in upper case, validated with
                 pycountry
country          country name as used by the framework document
framework        one of ``FRAMEWORKS``: cerf_aa, wfp_aa, ifrc_dref, other
status           one of ``STATUSES``: activated, framework_no_activation
activation_date  ISO calendar date the activation was announced or
                 triggered; null when the status is
                 framework_no_activation
trigger          the forecast or index threshold that fired, or null
forecast_source  the forecast product the trigger reads, or null
amount_usd       amount released in US dollars, or null
people_targeted  people targeted by the activation, or null
sector           sector or sectors funded, or null
source_url       the publisher's own document for the entry
wayback_url      Internet Archive copy of ``source_url``, or null
retrieved        UTC ISO 8601 timestamp when the entry was checked
discrepancies    list, possibly empty, of mappings with exactly the keys
                 ``statement``, ``value`` and ``source_url``; each records
                 a figure that a companion document states differently,
                 with the companion's value and URL; never reconciled
example          optional; true marks an illustrative entry that the
                 validator tolerates and the app never renders

A ``framework_no_activation`` entry records that a framework exists for
the country and did not activate, so ``activation_date``, ``amount_usd``
and ``people_targeted`` must be null. An ``activated`` entry must carry
an ``activation_date``.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pycountry
import yaml

REGISTER_PATH = Path(__file__).resolve().parent.parent / "data" / "curated" / "activations.yaml"

REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "iso3",
    "country",
    "framework",
    "status",
    "activation_date",
    "trigger",
    "forecast_source",
    "amount_usd",
    "people_targeted",
    "sector",
    "source_url",
    "wayback_url",
    "retrieved",
    "discrepancies",
)
OPTIONAL_FIELDS: tuple[str, ...] = ("example",)
DISCREPANCY_FIELDS: tuple[str, ...] = ("statement", "value", "source_url")

FRAMEWORKS: tuple[str, ...] = ("cerf_aa", "wfp_aa", "ifrc_dref", "other")
STATUSES: tuple[str, ...] = ("activated", "framework_no_activation")

# Fields that describe the activation itself; null when nothing activated.
ACTIVATION_FIELDS: tuple[str, ...] = ("activation_date", "amount_usd", "people_targeted")

WAYBACK_PREFIX = "https://web.archive.org/web/"

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_ISO3_RE = re.compile(r"^[A-Z]{3}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


def _non_empty_string(value: Any, field: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: {field!r} must be a non-empty string, got {value!r}")


def _string_or_null(value: Any, field: str, label: str) -> None:
    if value is None:
        return
    _non_empty_string(value, field, label)


def _http_url(value: Any, field: str, label: str) -> None:
    _non_empty_string(value, field, label)
    if not value.startswith(("http://", "https://")):
        raise ValueError(f"{label}: {field!r} must be an http(s) URL, got {value!r}")


def _number_or_null(value: Any, field: str, label: str, integer: bool = False) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{label}: {field!r} must be a number or null, got {value!r}")
    if integer and not isinstance(value, int):
        raise ValueError(f"{label}: {field!r} must be an integer or null, got {value!r}")
    if value < 0:
        raise ValueError(f"{label}: {field!r} must not be negative, got {value!r}")


def _calendar_date(value: Any, field: str, label: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError(f"{label}: {field!r} must be an ISO calendar date, got {value!r}")


def _validate_discrepancy(item: Any, label: str) -> None:
    if not isinstance(item, dict):
        raise ValueError(f"{label}: must be a mapping, got {type(item).__name__}")
    missing = [f for f in DISCREPANCY_FIELDS if f not in item]
    if missing:
        raise ValueError(f"{label}: missing fields {missing}")
    unknown = sorted(set(item) - set(DISCREPANCY_FIELDS))
    if unknown:
        raise ValueError(f"{label}: unknown fields {unknown}")
    _non_empty_string(item["statement"], "statement", label)
    value = item["value"]
    if isinstance(value, bool) or not isinstance(value, int | float | str) or value == "":
        raise ValueError(f"{label}: 'value' must be a number or a non-empty string, got {value!r}")
    _http_url(item["source_url"], "source_url", label)


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

    _non_empty_string(entry["id"], "id", label)
    if not _ID_RE.match(entry["id"]):
        raise ValueError(
            f"{label}: 'id' must use lower case letters, digits, underscores and hyphens, "
            f"got {entry['id']!r}"
        )

    iso3 = entry["iso3"]
    if not isinstance(iso3, str) or not _ISO3_RE.match(iso3):
        raise ValueError(f"{label}: 'iso3' must be three upper case letters, got {iso3!r}")
    if pycountry.countries.get(alpha_3=iso3) is None:
        raise ValueError(f"{label}: 'iso3' {iso3!r} is not an ISO 3166-1 alpha-3 code")

    _non_empty_string(entry["country"], "country", label)

    if entry["framework"] not in FRAMEWORKS:
        raise ValueError(
            f"{label}: 'framework' must be one of {list(FRAMEWORKS)}, got {entry['framework']!r}"
        )
    status = entry["status"]
    if status not in STATUSES:
        raise ValueError(f"{label}: 'status' must be one of {list(STATUSES)}, got {status!r}")

    if status == "activated":
        _calendar_date(entry["activation_date"], "activation_date", label)
    else:
        for field in ACTIVATION_FIELDS:
            if entry[field] is not None:
                raise ValueError(
                    f"{label}: {field!r} must be null when 'status' is {status!r}, "
                    f"got {entry[field]!r}"
                )

    for field in ("trigger", "forecast_source", "sector"):
        _string_or_null(entry[field], field, label)

    _number_or_null(entry["amount_usd"], "amount_usd", label)
    _number_or_null(entry["people_targeted"], "people_targeted", label, integer=True)

    _http_url(entry["source_url"], "source_url", label)

    wayback = entry["wayback_url"]
    if wayback is not None:
        _non_empty_string(wayback, "wayback_url", label)
        if not wayback.startswith(WAYBACK_PREFIX):
            raise ValueError(
                f"{label}: 'wayback_url' must start with {WAYBACK_PREFIX!r} or be null, "
                f"got {wayback!r}"
            )

    retrieved = entry["retrieved"]
    if not isinstance(retrieved, str) or not _UTC_RE.match(retrieved):
        raise ValueError(
            f"{label}: 'retrieved' must be a UTC ISO 8601 string such as "
            f"2026-09-05T00:00:00Z, got {retrieved!r}"
        )

    discrepancies = entry["discrepancies"]
    if not isinstance(discrepancies, list):
        raise ValueError(f"{label}: 'discrepancies' must be a list, possibly empty")
    for i, item in enumerate(discrepancies):
        _validate_discrepancy(item, f"{label}: discrepancies[{i}]")

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

    ids = [e["id"] for e in validated]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"{path}: duplicate ids {duplicates}")

    if include_examples:
        return validated
    return [e for e in validated if not e.get("example", False)]
