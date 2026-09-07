# El Niño Atlas: design notes

## Scope

Despite the broader repository name, this tool is a live tracker of the
**2026-27 El Niño event** only. It links the event to realised
socioeconomic impacts and is structured in three stages that every layer
must declare:

1. **Forecast**: the physical state of the event (ENSO indices, outlooks).
2. **Anticipatory action**: activations and early actions triggered by the
   forecast (humanitarian frameworks, early-warning alerts).
3. **Realised impact**: what actually happened (prices, food security,
   displacement, infrastructure disruption).

The tool is open source under MIT. Data are governed per source by
`src/sources.yaml`, which gates every fetcher and every committed file.

Version 0.2.0, released on 7 September 2026, is the first data release.
It carries the index panel, the activation map, the commodity panel and
the draft schematic, and is served at https://el-nino-atlas.onrender.com.

## Opening line

The page opens with this line, recorded here verbatim.
`tests/test_layout.py` checks `src/layout` against this blockquote, so
the two cannot drift apart.

> An El Niño is under way in the tropical Pacific and is forecast to
> become very strong by late 2026, on top of the warmest global
> background on record. This atlas follows what was forecast, what was
> done in anticipation, and what has happened.

"Very strong" is the NOAA intensity band for a peak of 2.0 °C or more.
Directly beneath the line the page shows one generated line on the
latest three-month season, for example "Latest three-month season (June
to August 2026): RONI +1.36 °C, ONI +1.80 °C, provisional.": the months
of the season, both values with their signs, and the word provisional
while the RONI run that reaches that season is shorter than five
seasons. A season that crosses a year boundary names both years, as in
"December 2026 to February 2027". The line is omitted when no index
snapshot exists.

## Layer table

Mirrors the statuses in `src/sources.yaml`. The registry is authoritative;
if the two disagree, fix this table. The Fetcher column records the code
as of version 0.2.0: `live` means the fetcher runs in the nightly
workflow and its snapshot is committed.

| Stage | Source | Registry id | Status | Redistribution | Fetcher |
|---|---|---|---|---|---|
| Forecast | NOAA ONI and RONI | `noaa_oni` | approved | yes | live, `src/fetchers/noaa_oni.py` |
| Realised impact | World Bank Pink Sheet | `worldbank_pink_sheet` | approved | yes | live, `src/fetchers/worldbank_pink_sheet.py` |
| Context | NOAA CPC El Niño impacts schematic | `noaa_cpc_enso_impacts_schematic` | approved | yes | none; static asset under `assets/teleconnections/`, byte-identical to the CPC image |
| Realised impact | FAOSTAT | `faostat` | approved | yes | none yet |
| Anticipatory action / realised impact | FEWS NET | `fews_net` | conditional | conditional | none yet |
| Anticipatory action / realised impact | OCHA ReliefWeb (metadata and links only) | `ocha_reliefweb` | conditional | conditional | none yet |
| Anticipatory action | OCHA/CERF activation reports | `ocha_cerf_anticipatory_action` | conditional | conditional | none; read by hand into the curated register |
| Context | World Weather Attribution | `world_weather_attribution` | link-only | no | never |
| Context | Carbon Brief attribution map | `carbon_brief_attribution_map` | link-only | no | never |
| Realised impact | EM-DAT | `emdat` | excluded | no | never |
| Realised impact | Munich Re NatCat | `munich_re_natcat` | excluded | no | never |
| Realised impact | Swiss Re NatCat | `swiss_re_natcat` | excluded | no | never |
| Realised impact | IMF PCPS | `imf_pcps` | superseded | no | never |
| Realised impact | IDMC | `idmc` | pending | no | blocked |
| Realised impact | UNDRR DesInventar | `undrr_desinventar` | pending | no | blocked |
| Forecast | GDACS | `gdacs` | pending | no | blocked |
| Anticipatory action | IFRC GO | `ifrc_go` | pending | no | blocked |
| Realised impact | Panama Canal Authority | `panama_canal_authority` | pending | no | blocked |

Status meanings:

- **approved**: fetch, store and redistribute under the stated licence.
- **conditional**: fetch only under the conditions in the registry notes.
- **link-only**: cite and link; never fetch or store.
- **excluded**: a licence or proprietary bar; never used in any form;
  never reintroduced.
- **superseded**: an editorial choice, not a licence bar; another source
  covers the same ground. Behaves as excluded for the fetcher gate.
- **pending**: blocked until the licence check is resolved in the registry.

### Panels on the page

The page runs along the spine in this order. Every data panel module
exposes `build_figure(...)` and `explainer()`; the schematic module
exposes `build_image_panel()`. A panel whose snapshot is missing keeps
its explainer and shows the notice "Data snapshot not yet available" in
place of its figure.

| Panel | Stage | Module | Data | State in 0.2.0 |
|---|---|---|---|---|
| The event: RONI and ONI | Forecast | `src/layers/enso_index.py` | `noaa_oni` snapshot | live |
| Anticipatory action: activation map and table | Anticipatory action | `src/layers/activations_map.py` | `data/curated/activations.yaml` read through `src/activations.py`, example entries excluded | live from the curated register; entries enter it only on the maintainer's approval in the weekly routine, see Curated entries below |
| Realised impact: commodity prices | Realised impact | `src/layers/commodities.py` | `worldbank_pink_sheet` snapshot, with the RONI events for shading | live |
| Where El Niño usually matters: draft schematic | Context | `src/layers/teleconnections.py` | `assets/teleconnections/noaa_cpc_elnino_impacts.jpg` | draft, shown as published; computed composites deferred |

The activation map shows the shared three-state legend above the map
and the entry table beneath it. With no curated entries it shows every
country as not tracked, which is the correct reading of an empty
register.

## Event classification

`src/enso_events.py` applies the NOAA Climate Prediction Center (CPC)
rule to one index series: El Niño (La Niña) is five or more consecutive
overlapping three-month seasons with the index at or above +0.5 °C (at
or below -0.5 °C). The decisions taken on 7 September 2026:

- **One-decimal rounding.** CPC colours its episode tables on the
  one-decimal values it displays, while the files carry two decimals.
  Each value is rounded as `floor(10x + 0.5) / 10`
  (`threshold_value`) before it is compared with the threshold, so
  0.45 counts as 0.5 and -0.45 as -0.4. Checked against the CPC tables
  read on 7 September 2026, this reproduces every coloured ONI episode
  and 46 of the 47 RONI episodes; the one exception, and the rounding
  that was tested and rejected, are recorded in the module docstring.
  Frame values and event peaks keep the file's two decimals.
- **ERSSTv6.** Both CPC files carry the ERSST version 6 series, and
  their one-decimal values match the v6 tables that the registry entry
  `noaa_oni` links.
- **RONI is the primary index.** CPC made the Relative Oceanic Niño
  Index its official index for ENSO monitoring and prediction on
  1 February 2026 (NWS Public Information Statement 26-05). The page
  draws RONI as the primary line and ONI as the muted secondary line,
  shades the events that the rule yields on RONI, and the commodity
  panel uses the same events.
- **A run reaching the latest season has no end.** A run at or beyond
  the threshold that reaches the last available season has `end` None
  whatever its length, because the data do not show it ending.
- **Provisional.** Such a run shorter than five seasons is reported as a
  provisional event rather than dropped. The panel draws it with a
  dashed outline and the label "provisional", and the reading line
  beneath the opening line carries the word. A run of five or more
  seasons that reaches the last season is an event with `end` None and
  `provisional` False. A run shorter than five seasons that ends before
  the last season is not an event.
- **Strength bands.** Jan Null's bands on the one-decimal magnitude of
  the peak: weak 0.5 to 0.9, moderate 1.0 to 1.4, strong 1.5 to 1.9,
  very strong 2.0 and above. Null applies the bands to ONI over three
  seasons; the module describes the peak season alone.

Open question, closed on 7 September 2026: whether ONI or RONI is the
primary index. Closed in favour of RONI, following CPC's switch on
1 February 2026. ONI stays on the page as the secondary line so that the
two can be compared, and the two lines diverge most when the whole
tropics are warm.

## Snapshots and curated entries

**Snapshot rule.** A snapshot is the pair
`data/snapshots/<source_id>/latest.csv` and `latest.json`, written by
`src/data_access.write_snapshot` in the tidy contract of
`src/schema.py` with provenance metadata beside it. A snapshot may be
written, and tracked in git, only for a source whose registry entry has
status `approved` and `redistribution: "yes"`;
`tests/test_sources_gate.py` applies the same rule to the git index. The
nightly workflow (`.github/workflows/nightly_update.yml`) runs every
registered fetcher, runs the test suite and commits "Update snapshots"
only when a CSV changed. The app only reads snapshots and never fetches;
a panel whose snapshot is missing shows its notice. Everything else
fetched at run time goes to `data/raw/` or `data/processed/`, which are
ignored.

**Curated entries.** `data/curated/activations.yaml` is human-curated:
one entry per country per framework, typed from the framework's own
document with its URL, an archived copy and a retrieval time.
`src/activations.py` validates every field and excludes entries flagged
`example`, which the app never renders. Figures that companion documents
state differently are recorded in the entry and never reconciled.

**Candidates flow.** A session that finds new activations drafts them as
candidates in the main clone's private `local/candidates/` folder, which
git ignores. Candidates enter `data/curated/` only on the maintainer's
explicit per-entry approval in a session, as part of the weekly routine;
nothing moves there on a session's own judgement, and no entry is ever
invented. The same rule applies to the hand-drawn teleconnection mask,
which stays in `local/candidates/` until approved.

## The three-state legend rule

Every layer classifies each unit (country, region, commodity, activation)
into exactly one of three states:

| State | Meaning | Token |
|---|---|---|
| Alert | an active alert, activation or realised impact | `alert` |
| No alert | assessed, and no alert | `no_alert` |
| Not assessed | no assessment exists for this unit or period | `not_assessed` |

"Not assessed" is the absence of evidence, not evidence of absence. It
must always render distinctly from "No alert" and must never share its
colour. The tokens live in `src/theme.py`; "not assessed" additionally
uses a hatched, dashed-outline swatch so the distinction survives
greyscale printing and colour-vision deficiency. A gate test asserts the
colours differ. Coverage gaps in any source (for example FEWS NET
reporting gaps during 2026) render as "not assessed". On the activation
map the three states read as activated, framework with no activation,
and not tracked.

## Falsifiability

The tracker reports the event as observed, including weak, null and
negative outcomes. A forecast that does not verify, an activation whose
trigger fired but whose hazard did not materialise, or a realised-impact
layer that stays at "no alert" throughout are results, not failures of
the tool.

Divergence between the forecast, activation and realised-impact layers
is itself content to display. Activations whose trigger fired but whose
hazard did not verify are shown as such, alongside those that did.

No layer selects, orders, thresholds or phrases content to confirm event
severity. Where a choice of presentation would make the event look
stronger or weaker, the choice is documented here and the same rule is
applied whichever way the evidence falls.

## Caption guardrails

Every caption or annotation that touches these claims must carry the
corresponding wording, verbatim or in substance:

> El Niño's depressing effect on growth in exposed economies is
> directionally supported across independent studies; headline dollar
> magnitudes are contested on econometric grounds.

> ENSO-to-price transmission is disputed and may have weakened in recent
> decades; treat price co-movements as suggestive.

> El Niño contributed on the order of 0.1 degrees C to the 2023-24 global
> temperature records; the forced warming trend dominates.

Figures are authored in degrees C.

## Deferred

- **Computed teleconnection composites.** The context layer shows the
  CPC schematic as published, a draft with no statistical test.
  Composites computed from public-domain gridded data with significance
  tests, and the hand-drawn mask in `local/candidates/`, wait on a
  settled method and the maintainer's approval.
- **EM-DAT analysis.** Lives in the accompanying paper only. Nothing
  derived from it enters this tool; the gate test rejects any reference
  under `src/`.
- **Pending licence checks.** IDMC, UNDRR DesInventar, GDACS, IFRC GO and
  the Panama Canal Authority remain blocked until their registry status
  changes.
- **Bootstrap stylesheet.** Currently loaded from a CDN via
  `dash-bootstrap-components`; vendor it locally if offline rendering is
  needed.

## Deployment

Local: `uv run python run.py dashboard`. Production: `gunicorn app:server`.
`render.yaml` defines the Render web service (Python 3.11, uv-based build
with a pip fallback, `gunicorn app:server`) that serves
https://el-nino-atlas.onrender.com from `main`. `autoDeploy` is off, so
each deploy is a manual step in the Render dashboard.
