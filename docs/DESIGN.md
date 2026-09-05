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

## Layer table

Mirrors the statuses in `src/sources.yaml`. The registry is authoritative;
if the two disagree, fix this table.

| Stage | Source | Registry id | Status | Redistribution | Fetcher |
|---|---|---|---|---|---|
| Forecast | NOAA ONI | `noaa_oni` | approved | yes | stub |
| Realised impact | World Bank Pink Sheet | `worldbank_pink_sheet` | approved | yes | stub |
| Realised impact | FAOSTAT | `faostat` | approved | yes | none yet |
| Anticipatory action / realised impact | FEWS NET | `fews_net` | conditional | conditional | none yet |
| Anticipatory action / realised impact | OCHA ReliefWeb (metadata and links only) | `ocha_reliefweb` | conditional | conditional | none yet |
| Anticipatory action | OCHA/CERF activation reports | `ocha_cerf_anticipatory_action` | conditional | conditional | none yet |
| Context | World Weather Attribution | `world_weather_attribution` | link-only | no | never |
| Context | Carbon Brief attribution map | `carbon_brief_attribution_map` | link-only | no | never |
| Realised impact | EM-DAT | `emdat` | excluded | no | never |
| Realised impact | Munich Re NatCat | `munich_re_natcat` | excluded | no | never |
| Realised impact | Swiss Re NatCat | `swiss_re_natcat` | excluded | no | never |
| Realised impact | IMF PCPS | `imf_pcps` | excluded | no | never |
| Realised impact | IDMC | `idmc` | pending | no | blocked |
| Realised impact | UNDRR DesInventar | `undrr_desinventar` | pending | no | blocked |
| Forecast | GDACS | `gdacs` | pending | no | blocked |
| Anticipatory action | IFRC GO | `ifrc_go` | pending | no | blocked |
| Realised impact | Panama Canal Authority | `panama_canal_authority` | pending | no | blocked |

Status meanings:

- **approved**: fetch, store and redistribute under the stated licence.
- **conditional**: fetch only under the conditions in the registry notes.
- **link-only**: cite and link; never fetch or store.
- **excluded**: never used in any form; never reintroduced.
- **pending**: blocked until the licence check is resolved in the registry.

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
reporting gaps during 2026) render as "not assessed".

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

- **Composite teleconnection base layer.** A canonical map of expected
  El Niño teleconnections (precipitation and temperature anomalies by
  season) as a base layer beneath the impact layers. Deferred until the
  source and its licence are settled.
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
`render.yaml.stub` documents the later one-step Render deployment; it is
not active.
