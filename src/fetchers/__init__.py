"""Data fetchers.

A fetcher module may exist only for a source whose entry in
``src/sources.yaml`` has status ``approved`` or ``conditional``
(enforced by ``tests/test_sources_gate.py``), and is named after its
registry id.

Each fetcher module exposes two functions:

    fetch() -> tuple[Fetched, ...]
        downloads the raw file or files and returns their bytes with the
        URL, sha256 and UTC retrieval time of each;
    parse(fetched) -> pandas.DataFrame
        turns those bytes into the tidy contract of ``src/schema.py``.

``REGISTERED_FETCHERS`` maps each source id to its ``(fetch, parse)``
pair; ``python run.py update`` walks it, validates every frame and writes
snapshots through ``src.data_access.write_snapshot``. Shared helpers live
here so that the fetchers directory holds only one module per registry
id.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import pandas as pd
import requests

from src.schema import registry

USER_AGENT = "El-Nino-Atlas/0.1 (+https://github.com/AlKhourdajie/El_Nino_Atlas)"
TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class Fetched:
    """One downloaded file: its URL, raw bytes, sha256 and UTC retrieval time."""

    url: str
    content: bytes
    sha256: str
    retrieved_at: str


FetchFn = Callable[[], tuple[Fetched, ...]]
ParseFn = Callable[[tuple[Fetched, ...]], pd.DataFrame]

REGISTERED_FETCHERS: dict[str, tuple[FetchFn, ParseFn]] = {}


def utc_now_iso() -> str:
    """The current UTC time as the contract's ``retrieved_at`` string."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def download(url: str, allowed_hosts: frozenset[str]) -> Fetched:
    """GET ``url`` and return it as ``Fetched``.

    Refuses any host outside ``allowed_hosts`` before a request is made,
    raises on HTTP errors and on an empty body, and never retries.
    """
    host = urlparse(url).hostname
    if host not in allowed_hosts:
        raise ValueError(
            f"refusing to download from host {host!r}; permitted hosts are {sorted(allowed_hosts)}"
        )
    retrieved_at = utc_now_iso()
    response = requests.get(url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    content = response.content
    if not content:
        raise ValueError(f"{url} returned an empty body")
    return Fetched(url=url, content=content, sha256=sha256_hex(content), retrieved_at=retrieved_at)


def snapshot_metadata(source_id: str, fetched: tuple[Fetched, ...], frame: pd.DataFrame) -> dict:
    """The provenance metadata written beside a snapshot of ``frame``.

    ``retrieved_at``, ``source_url`` and ``raw_sha256`` describe the first
    downloaded file; ``files`` lists every file. The licence and
    attribution come from the registry entry.
    """
    if not fetched:
        raise ValueError(f"{source_id}: no files were fetched")
    entry = registry()[source_id]
    first = fetched[0]
    dates = sorted(frame["date"])
    return {
        "source_id": source_id,
        "source_name": entry["name"],
        "landing_url": entry["url"],
        "source_url": first.url,
        "retrieved_at": first.retrieved_at,
        "raw_sha256": first.sha256,
        "files": [
            {
                "url": item.url,
                "sha256": item.sha256,
                "bytes": len(item.content),
                "retrieved_at": item.retrieved_at,
            }
            for item in fetched
        ],
        "licence_id": entry["licence_id"],
        "attribution": entry["attribution"],
        "row_count": int(len(frame)),
        "series_ids": sorted(set(frame["series_id"])),
        "first_date": dates[0],
        "last_date": dates[-1],
    }


def _register() -> None:
    from src.fetchers import noaa_oni, worldbank_pink_sheet

    REGISTERED_FETCHERS[noaa_oni.SOURCE_ID] = (noaa_oni.fetch, noaa_oni.parse)
    REGISTERED_FETCHERS[worldbank_pink_sheet.SOURCE_ID] = (
        worldbank_pink_sheet.fetch,
        worldbank_pink_sheet.parse,
    )


_register()
