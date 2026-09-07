# Standing rules for the El Niño Atlas

These rules apply to every session and every contributor. They are not
suggestions.

## Data governance

- `src/sources.yaml` is the licence registry and gates all data work.
  No fetcher exists without an entry whose status is `approved` or
  `conditional`. `tests/test_sources_gate.py` enforces this.
- Excluded sources (status `excluded`) are never reintroduced in any
  form: no fetcher, no cached file, no derived table, no hard-coded
  values, no mention under `src/`. In particular, nothing from EM-DAT
  enters this tool; its analysis lives in the accompanying paper only.
- `excluded` means a licence or proprietary bar. `superseded` means an
  editorial choice: another source covers the same ground. Both bar a
  fetcher. Every registry entry carries a one-line `reason` for its
  status.
- Files under `data/curated/` are human-curated. Never add, edit or
  delete entries there unless explicitly instructed in-session, and
  never invent entries.
- No data file is committed unless its source entry says
  `redistribution: "yes"`. Everything else is fetched at run time into
  `data/raw/` or `data/processed/`, which are gitignored apart from
  `.gitkeep`.
- Under `data/` outside `data/curated/`, the only files that may be
  tracked are `data/snapshots/<source_id>/latest.csv` and `latest.json`
  for a source whose registry entry has status `approved` and
  `redistribution: "yes"`; `tests/test_sources_gate.py` enforces this.
- `link-only` sources are cited and linked, never fetched. `pending`
  sources stay blocked until the registry says otherwise.

## Fetchers

- Fetchers fail loudly on parsing anomalies. Raise; never silently
  substitute, interpolate, or fabricate values. Missing data renders as
  "not assessed".
- Every fetcher module carries the provenance docstring: publisher,
  dataset, canonical URL from `src/sources.yaml`, licence,
  redistribution, attribution string, cadence, latency, registry id.
- A fetcher module is named after its registry id.

## Presentation

- "Not assessed" always renders distinctly from "no alert" and never
  shares its colour. Tokens live in `src/theme.py`.
- The tracker reports the event as observed, including weak, null and
  negative outcomes; divergence between layers is content to display,
  and no layer selects or phrases content to confirm event severity.
- Figures are authored in degrees C.
- Captions on growth, price transmission, and the 2023-24 temperature
  contribution follow the guardrails in `docs/DESIGN.md` verbatim or in
  substance.

## Panels and public copy

- Every panel module exposes `build_figure(...)` and
  `explainer() -> Explainer` (`src/layout/explainer.py`); the app renders
  the explainer beside the figure with `render_explainer`.
- Public copy rules: British English; no em-dashes; plain verbs; no
  intensifiers; no metaphor; no contrastive negation ("not X but Y" and
  its variants); acronyms expanded on first use.
- The "how" block uses the source's own wording with one link.

## Style

- British English in all documentation and user-facing text.
- Commit subjects are imperative and capitalised. One concern per
  commit.
- `uv run pytest` must be green before any commit. `uv run ruff check .`
  must pass.
- Python 3.11 via uv. Add dependencies with `uv add`; never hand-edit
  pins or `uv.lock`.
