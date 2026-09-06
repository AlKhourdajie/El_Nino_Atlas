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
uv run pre-commit install         # ruff plus the gate tests on every commit
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
- `src/schema.py`: the tidy long-format contract every layer emits.
- `src/enso_events.py`: NOAA-convention ENSO event classification.
- `data/curated/activations.yaml`: hand-curated anticipatory-action register.
- `data/curated/`: human-curated files, tracked in git; `data/raw/` and
  `data/processed/` are fetched at run time and ignored.
- `render.yaml`: Render web-service definition.
- `docs/DESIGN.md`: scope, layer table, legend rule, caption guardrails.
- `CLAUDE.md`: standing rules for every contributor and session.

## Deployment

Production serves the Flask object exposed by `app.py`:

```bash
uv run gunicorn app:server --bind 0.0.0.0:8050
```

`render.yaml` defines a Render web service on Python 3.11 that builds
with uv (falling back to pip if uv is unavailable) and starts
`gunicorn app:server`. Committing the file does not create the service;
connect the repository in the Render dashboard when the tool is ready to
go live.

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
