"""Data fetchers (stubs only).

A fetcher module may exist only for a source whose entry in
``src/sources.yaml`` has status ``approved`` or ``conditional``
(enforced by ``tests/test_sources_gate.py``). Fetchers are registered
here by source id once they are implemented; stubs are not registered,
so ``python run.py update`` reports "no fetchers registered".
"""

from collections.abc import Callable

REGISTERED_FETCHERS: dict[str, Callable[[], None]] = {}
