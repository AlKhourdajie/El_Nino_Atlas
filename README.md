# El Niño Atlas

An open-source interactive tracker linking the **2026-27 El Niño** to
realised socioeconomic impacts. Each signal is followed through three
stages: **forecast**, **anticipatory action**, **realised impact**.

**Status: pre-data scaffold.** The app serves a placeholder page with the
three-state legend. No data are fetched yet; no layers are active.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11.

```bash
uv sync
uv run python run.py dashboard    # serve on http://127.0.0.1:8050
uv run python run.py update       # run registered fetchers (none yet)
uv run ruff check .
uv run pytest
```

Host, port and debug mode are read from `ATLAS_HOST`, `ATLAS_PORT` (or
`PORT`) and `ATLAS_DEBUG`; see `config.py`.

## Layout

- `app.py`: builds the Dash app at import and exposes `server` for gunicorn.
- `run.py`: command-line entry point.
- `src/theme.py`: colour tokens and Plotly templates.
- `src/layout.py`: page builders.
- `src/layers/`, `src/fetchers/`: stub packages.
- `src/sources.yaml`: the licence registry that gates all data work.
- `docs/DESIGN.md`: scope, layer table, legend rule, caption guardrails.
- `CLAUDE.md`: standing rules for every contributor and session.

## Licence

Code is released under the MIT licence (see `LICENSE`).

Data are **not** covered by the code licence. Each source is governed by
its entry in `src/sources.yaml`, which records the licence,
redistribution terms and required attribution, and which gates every
fetcher. Only sources marked `redistribution: "yes"` may ever be
committed to this repository.

This tool contains no EM-DAT content and never will; EM-DAT's terms
prohibit redistribution and derivative databases, so any such analysis
lives in the accompanying paper only.

## Citation

See `CITATION.cff`.
