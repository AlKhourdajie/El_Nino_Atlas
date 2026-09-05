"""Command-line entry point.

Usage::

    python run.py dashboard   serve the Dash app locally
    python run.py update      run every registered fetcher (none yet)
"""

import argparse
import sys

import config
from src.fetchers import REGISTERED_FETCHERS


def cmd_dashboard() -> int:
    from app import app

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
    return 0


def cmd_update() -> int:
    if not REGISTERED_FETCHERS:
        print("no fetchers registered")
        return 0
    for source_id, fetch in REGISTERED_FETCHERS.items():
        print(f"fetching {source_id}")
        fetch()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dashboard", help="serve the dashboard locally")
    sub.add_parser("update", help="run all registered data fetchers")
    args = parser.parse_args(argv)
    if args.command == "dashboard":
        return cmd_dashboard()
    return cmd_update()


if __name__ == "__main__":
    sys.exit(main())
