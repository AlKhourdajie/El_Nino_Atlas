# El Niño Atlas

An open-source interactive tracker linking the **2026-27 El Niño** to
realised socioeconomic impacts. Each signal is followed through three
stages: **forecast**, **anticipatory action**, **realised impact**.

**Status: pre-data scaffold.** The app serves a placeholder page with the
three-state legend. No data are fetched yet; no layers are active.

## What the atlas shows

The atlas follows a single event, the 2026-27 El Niño, from the first
forecast signal to what can be measured afterwards. Every layer sits in
one of three stages and is drawn from a source listed in
`src/sources.yaml`. Nothing is shown from a source whose licence has not
been cleared, and nothing is shown from EM-DAT.

### Stages and metrics

| Stage | Metric | Source | Status |
|---|---|---|---|
| Forecast | Oceanic Niño Index (ONI): three-month running mean of Niño 3.4 sea-surface temperature anomaly, degrees C, monthly | NOAA CPC | approved, parser pending |
| Forecast | ENSO event spans derived from the ONI under the NOAA convention: phase, onset, end, peak | derived | implemented |
| Forecast | Global disaster alerts (GDACS) | EC JRC and OCHA | pending licence check |
| Anticipatory action | Activations: date, country, framework, agencies, amount released (USD), people covered, trigger that fired | CERF, IFRC GO, hand-curated register | curated register in place, no entries yet |
| Anticipatory action | Food-security outlooks and alerts | FEWS NET | conditional |
| Realised impact | Monthly commodity prices for coffee (arabica and robusta), cocoa, sugar and rice | World Bank Pink Sheet | approved, parser pending |
| Realised impact | Food production and producer prices | FAOSTAT | approved |
| Realised impact | Humanitarian reporting, metadata and links only | OCHA ReliefWeb | conditional |
| Realised impact | Internal displacement | IDMC | pending licence check |
| Realised impact | National disaster loss records | UNDRR DesInventar | pending licence check |
| Realised impact | Panama Canal draught restrictions and transits | Panama Canal Authority | pending licence check |
| Context | Attribution studies and maps | World Weather Attribution, Carbon Brief | link-only, never fetched |

Figures are authored in degrees C. The ONI thresholds follow NOAA: an
event is five or more consecutive overlapping three-month seasons at or
beyond plus or minus 0.5 degrees C.

### How to read it

Every layer classifies each unit (a country, a basin, a commodity, an
activation) into exactly one of three states:

- **Alert**: an active alert, activation or realised impact.
- **No alert**: assessed, and nothing to report.
- **Not assessed**: no assessment exists for that unit or period. This is
  shown with its own hatched swatch and never in the "No alert" colour,
  because absence of evidence is not evidence of absence.

The tracker reports the event as observed, including weak, null and
negative outcomes. Divergence between the stages is content in its own
right: an activation whose trigger fired but whose hazard did not
verify is displayed as such. No layer selects or phrases content to make
the event look stronger or weaker.

Captions on growth effects, price transmission and the 2023-24
temperature contribution follow the guardrails in `docs/DESIGN.md`:
growth effects are directionally supported but dollar magnitudes are
contested; ENSO-to-price transmission is disputed and price
co-movements are suggestive only; El Niño contributed on the order of
0.1 degrees C to the 2023-24 records while the forced warming trend
dominates.

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
