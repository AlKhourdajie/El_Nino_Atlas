"""Command-line entry point.

Usage::

    python run.py dashboard   serve the Dash app locally
    python run.py update      fetch every registered source and write snapshots

``update`` walks ``src.fetchers.REGISTERED_FETCHERS``: for each source it
fetches the raw files, parses them into the tidy contract, validates the
frame and writes ``data/snapshots/<source_id>/latest.csv`` and
``latest.json`` through ``src.data_access.write_snapshot``, which leaves
both files untouched when the CSV is unchanged. It prints one line per
source (``written``, ``unchanged`` or ``failed``), keeps going after a
failure, and exits non-zero if any source failed.
"""

import argparse
import sys

import config
from src.data_access import write_snapshot
from src.fetchers import REGISTERED_FETCHERS, snapshot_metadata
from src.schema import validate_frame


def cmd_dashboard() -> int:
    from app import app

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
    return 0


def cmd_update() -> int:
    if not REGISTERED_FETCHERS:
        print("no fetchers registered")
        return 0
    failed = 0
    for source_id, (fetch, parse) in REGISTERED_FETCHERS.items():
        try:
            fetched = fetch()
            frame = validate_frame(parse(fetched))
            written = write_snapshot(source_id, frame, snapshot_metadata(source_id, fetched, frame))
        except Exception as exc:
            failed += 1
            print(f"{source_id}: failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        print(f"{source_id}: {'written' if written else 'unchanged'}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dashboard", help="serve the dashboard locally")
    sub.add_parser("update", help="fetch every registered source and write snapshots")
    args = parser.parse_args(argv)
    if args.command == "dashboard":
        return cmd_dashboard()
    return cmd_update()


if __name__ == "__main__":
    sys.exit(main())
