"""The data contract every layer emits: one tidy long-format frame.

Columns (all required, no extras):

    source_id     registry id from src/sources.yaml; status must be
                  approved or conditional
    series_id     stable identifier of the series within the source
    region        spatial unit the value refers to (ISO code, basin, "global")
    date          ISO 8601 calendar date, YYYY-MM-DD
    value         float; finite; missing values are omitted, never NaN
    unit          unit string ("degC", "USD/kg", "index")
    retrieved_at  UTC ISO 8601 timestamp of retrieval, e.g. 2026-09-05T17:00:00Z
    licence_id    short licence identifier ("US-PD", "CC-BY-4.0")

``validate_frame`` raises ``ValueError`` with a specific message on the
first violation found. It never repairs, coerces or drops rows.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from functools import lru_cache
from importlib import resources

import numpy as np
import pandas as pd
import yaml

COLUMNS: tuple[str, ...] = (
    "source_id",
    "series_id",
    "region",
    "date",
    "value",
    "unit",
    "retrieved_at",
    "licence_id",
)
KEY_COLUMNS: tuple[str, ...] = ("source_id", "series_id", "region", "date")
FETCHABLE_STATUSES = frozenset({"approved", "conditional"})

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


@lru_cache(maxsize=1)
def registry() -> dict[str, dict]:
    """The parsed licence registry keyed by source id."""
    text = (resources.files("src") / "sources.yaml").read_text(encoding="utf-8")
    entries = yaml.safe_load(text)["sources"]
    return {entry["id"]: entry for entry in entries}


def fetchable_source_ids() -> frozenset[str]:
    return frozenset(
        sid for sid, entry in registry().items() if entry["status"] in FETCHABLE_STATUSES
    )


def _require_strings(df: pd.DataFrame, column: str) -> None:
    series = df[column]
    if series.isna().any():
        raise ValueError(f"column {column!r} contains null values")
    bad = series[~series.map(lambda v: isinstance(v, str) and v.strip() != "")]
    if not bad.empty:
        raise ValueError(
            f"column {column!r} must contain non-empty strings; first offender at "
            f"row {bad.index[0]}: {bad.iloc[0]!r}"
        )


def _require_iso_dates(df: pd.DataFrame) -> None:
    _require_strings(df, "date")
    for idx, text in df["date"].items():
        if not _DATE_RE.match(text):
            raise ValueError(f"column 'date' must be YYYY-MM-DD; row {idx}: {text!r}")
        try:
            date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"column 'date' has an invalid date at row {idx}: {text!r}") from exc


def _require_utc_timestamps(df: pd.DataFrame) -> None:
    _require_strings(df, "retrieved_at")
    for idx, text in df["retrieved_at"].items():
        if not _UTC_RE.match(text):
            raise ValueError(
                "column 'retrieved_at' must be a UTC ISO 8601 timestamp such as "
                f"2026-09-05T17:00:00Z; row {idx}: {text!r}"
            )
        try:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                f"column 'retrieved_at' has an invalid timestamp at row {idx}: {text!r}"
            ) from exc


def _require_finite_floats(df: pd.DataFrame) -> None:
    series = df["value"]
    if not pd.api.types.is_float_dtype(series):
        raise ValueError(f"column 'value' must have a float dtype, got {series.dtype}")
    if series.isna().any():
        idx = series[series.isna()].index[0]
        raise ValueError(f"column 'value' contains NaN at row {idx}; omit missing rows instead")
    if not np.isfinite(series.to_numpy()).all():
        idx = series[~np.isfinite(series)].index[0]
        raise ValueError(f"column 'value' contains a non-finite value at row {idx}")


def validate_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Validate ``df`` against the contract and return it unchanged.

    Raises ``ValueError`` naming the first violation. The frame is never
    modified, coerced or filtered.
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"expected a pandas DataFrame, got {type(df).__name__}")

    expected = set(COLUMNS)
    actual = set(df.columns)
    if missing := expected - actual:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if extra := actual - expected:
        raise ValueError(f"unexpected columns: {sorted(extra)}")
    if df.empty:
        raise ValueError("frame has no rows")

    for column in ("source_id", "series_id", "region", "unit", "licence_id"):
        _require_strings(df, column)

    allowed = fetchable_source_ids()
    unknown = sorted(set(df["source_id"]) - set(registry()))
    if unknown:
        raise ValueError(f"source_id not in src/sources.yaml: {unknown}")
    barred = sorted(set(df["source_id"]) - allowed)
    if barred:
        statuses = {sid: registry()[sid]["status"] for sid in barred}
        raise ValueError(f"source_id must have status approved or conditional; got {statuses}")

    _require_iso_dates(df)
    _require_finite_floats(df)
    _require_utc_timestamps(df)

    duplicated = df.duplicated(subset=list(KEY_COLUMNS), keep=False)
    if duplicated.any():
        first = df.loc[duplicated, list(KEY_COLUMNS)].iloc[0].to_dict()
        raise ValueError(f"duplicate key {first}; keys are {KEY_COLUMNS}")

    return df
