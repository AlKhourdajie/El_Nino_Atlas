"""Data fetchers.

A fetcher module may exist only for a source whose entry in
``src/sources.yaml`` has status ``approved`` or ``conditional``
(enforced by ``tests/test_sources_gate.py``). Fetchers are registered
here by source id once they are implemented; stubs are not registered,
so ``python run.py update`` reports "no fetchers registered".

Shared helpers used by every fetcher module live here so that the
fetchers directory holds only one module per registry id.
"""

from collections.abc import Callable
from datetime import UTC, datetime

REGISTERED_FETCHERS: dict[str, Callable[[], None]] = {}


def utc_now_iso() -> str:
    """The current UTC time as the contract's ``retrieved_at`` string."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
