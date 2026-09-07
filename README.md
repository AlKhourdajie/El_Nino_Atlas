# El Niño Atlas

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22644790.svg)](https://doi.org/10.5281/zenodo.22644790)

Live site: https://el-nino-atlas.onrender.com

Maintained by [Alaa Al Khourdajie](https://sites.google.com/site/akhourdajie/), Imperial College London.

An El Niño is under way in the tropical Pacific and is forecast to become very strong by late 2026, on top of the warmest global background on record. The El Niño Atlas follows this one event forward in time, from what was forecast through what was done in anticipation to what has happened. The basis for every link is stated, and regions and periods without a record are marked as such.

The atlas is a research tool in development. Version 0.2.0 (September 2026) carries three panels and one draft map. The code is released under the MIT licence, and each data source is used under its own terms, listed below.

## Why an event-resolved atlas

Hazard catalogues, forecast dashboards and response dashboards each cover one stage of an event and keep their records apart. The atlas takes the 2026-27 El Niño as its unit and organises the three records around it, so that every entry is tied to this event with a stated basis and the stages sit on one page. Divergence between the stages is a finding in its own right, so a forecast that failed to verify, an activation whose hazard never arrived and a price that moved for another reason are recorded with the same care as a confirmed impact.

## How to read the atlas

**Order.** The page opens with the state of El Niño in the Pacific, followed by the realised impacts that public data can measure, the anticipatory action taken on forecasts, and a draft map of where an effect is expected. Each panel carries its stage label.

**Three states.** Where a panel shows regions, each region is in one of three states: something recorded; assessed with nothing recorded; or not assessed. The third state has its own grey, and a region that a source did not cover is shown in it, because a "nothing recorded" label would attribute to the source an assessment it never made.

**Provisional.** The rule that identifies an El Niño needs five consecutive three-month seasons at or beyond the threshold. Until the fifth season is in, the 2026-27 event is marked provisional, and the classification of the latest seasons can change as new months arrive.

**Basis of every claim.** Every association between El Niño and an outcome rests on a mechanism stated by a cited source. Where two things merely coincide in time, the atlas records the coincidence as such. Every panel names what it does not show, and three fixed sentences accompany any panel that touches economic growth, prices or the global temperature record. They are listed under Caption guardrails.

## The panels

### The event: RONI and ONI

**What this shows.** Two indices of the El Niño Southern Oscillation (ENSO) published by the National Oceanic and Atmospheric Administration (NOAA) Climate Prediction Center (CPC): the Relative Oceanic Niño Index (RONI) as the primary line and the Oceanic Niño Index (ONI) as a secondary line, from 1950 to the latest complete season. Each point is a three-month season in degrees Celsius, plotted at its centre month. Shading marks the seasons of each event that the five-season rule yields on RONI, warm shading for El Niño and light cool shading for La Niña. A dashed outline and the word provisional mark an event whose classification can still change.

**How it is measured.** ONI is the three-month running mean of the sea surface temperature anomaly in the Niño 3.4 region of the central Pacific (5°N to 5°S, 120°W to 170°W), relative to a 30-year base period. RONI, CPC's official index since 1 February 2026, starts from the same anomaly, subtracts the average anomaly of the global tropics (20°N to 20°S) and rescales the result to match the amplitude of ONI. CPC identifies El Niño or La Niña when the index is at or beyond +0.5 °C or −0.5 °C for five consecutive overlapping three-month seasons. The definition is set out in the [CPC RONI announcement](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/announcement.php). The values come from the [CPC ONI table](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/) and the [CPC RONI table](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/), both computed on ERSST version 6.

**Why it matters for El Niño.** ENSO is the largest source of year-to-year variation in the global climate, and every forecast, activation and impact in the atlas is tied to the state of the event that this index measures. Because the tropical oceans have warmed, the Niño 3.4 anomaly on its own partly reflects the background trend. RONI subtracts the tropical mean so that the index follows the contrast that drives the atmospheric response. The two lines diverge most when the whole tropics are warm.

**What it does not show.** A seasonal index measures the state of the ocean. Weekly values, local rainfall and temperature, losses in any place, and the forecasts issued ahead of the event lie outside this panel. The latest seasons are shaded only once the five-season rule is met.

### Anticipatory action: activations

**What this shows.** A world map with each country in one of three states: an anticipatory-action framework activated for this El Niño; a framework in place with no activation recorded; or not tracked by the atlas. Each entry lists the framework, the trigger, the date, the funding released and the number of people targeted, with a link to the primary document and to an archived copy of it. Where companion documents give different figures, both are shown as they stand.

**How it is measured.** Anticipatory action is humanitarian funding released before a forecast hazard arrives, on triggers agreed in advance. The entries are taken from the primary documents of the United Nations Central Emergency Response Fund ([CERF](https://cerf.un.org)), the World Food Programme ([WFP](https://www.wfp.org)) and the Food and Agriculture Organization ([FAO](https://www.fao.org)). Every entry is typed from the document by hand and checked by the maintainer before it enters the atlas.

**Why it matters for El Niño.** Activation is the first observable response to a forecast. Its timing and scale, set against what later happened, form the core of the forecast-to-impact record.

**What it does not show.** An activation records money released on a forecast trigger. Whether the hazard occurred and whether the action worked lie outside this panel. Most countries are shown as not tracked, which is the current coverage of the atlas, and the tracked area grows as entries are added.

### Realised impact: commodity prices

**What this shows.** Monthly world prices for five agricultural commodities: arabica coffee, robusta coffee, cocoa, sugar and rice. Each series is rebased so that January 2010 equals 100, which puts five different units on one axis. Hovering over a point shows the nominal price in its own unit. Shading marks El Niño seasons as in the index panel, so that price movements can be read against the state of the event.

**How it is measured.** The World Bank's Commodity Price Data, known as the Pink Sheet, is a monthly release of nominal US dollar prices for energy, agricultural, fertiliser and metal commodities, most series from 1960, alongside price indices for each group. Each price is the monthly average for a stated grade in a stated market. The release and its documentation are on the [World Bank commodity markets page](https://www.worldbank.org/en/research/commodity-markets).

**Why it matters for El Niño.** Coffee, cocoa, sugar and rice are grown in regions where El Niño shifts rainfall and temperature, so their world prices are among the first public series in which a realised effect on food and export earnings could appear. The panel places the price series beside the El Niño seasons so that the reader can see whether the two align during this event or diverge.

**What it does not show.** Co-movement here is descriptive, since prices respond to many drivers, among them stocks, exchange rates, energy and fertiliser costs, trade policy and demand, and a price move during an El Niño season therefore stands as an observation without attribution or size estimate. The series are nominal, so long-run movements include inflation, and they are world prices, distinct from what producers received or consumers paid in any one country.

### Where El Niño usually matters: draft schematic

**What this shows.** NOAA CPC's schematic of the regions where El Niño has tended to shift rainfall and temperature in past events, reproduced as published, with December to February in the upper panel and June to August in the lower panel.

**How it is measured.** CPC draws the schematic as a summary of past events, and it carries no statistical test. Source: [CPC El Niño impacts](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml), a US government work.

**Why it matters for El Niño.** It shows where an El Niño signal is expected, which is the basis on which later realised-impact layers will be admitted to the atlas.

**What it does not show.** The schematic summarises tendencies across past events, and single events differ from it. CPC's page text lists Central America as drier in December to February while the image draws no such area, and the image shows a wet area over the south-western United States that the text omits. The panel is a draft and will be replaced by composites computed from public-domain gridded data with significance tests.

## Method notes

**ENSO classification.** The classifier applies CPC's rule to both indices: five or more consecutive overlapping three-month seasons at or beyond ±0.5 °C. The threshold is applied to the one-decimal values that CPC publishes, which is how CPC's own episode tables are built. The classifier is tested against those tables, with the 1997-98 and 2015-16 El Niño and the 2010-11 La Niña pinned on both indices. Strength bands follow the thresholds in Jan Null's widely used tables: weak 0.5 to 0.9, moderate 1.0 to 1.4, strong 1.5 to 1.9, very strong 2.0 and above. A run that reaches the latest available season has no end date, and a run shorter than five seasons is provisional.

**Snapshots.** A scheduled job runs every fetcher each night, validates the result against a fixed schema (source, series, region, date, value, unit, retrieval time, licence) and commits a snapshot when the source has changed. The site serves the snapshot, and each panel states its retrieval date. Snapshots are committed for sources whose licence permits redistribution.

**Curated entries.** Anticipatory-action entries live in `data/curated/` and are entered by hand from primary documents, with the source URL and an archived copy of the page. A discrepancies field records figures that differ between companion documents.

**Falsifiability.** The atlas reports the event as observed, including weak, null and negative outcomes, and presentation choices that affect apparent severity are documented and applied symmetrically.

## Caption guardrails

These three sentences appear, verbatim, on any panel that touches the subject named.

1. El Niño's depressing effect on growth in exposed economies is directionally supported across independent studies; headline dollar magnitudes are contested on econometric grounds.
2. ENSO-to-price transmission is disputed and may have weakened in recent decades; treat price co-movements as suggestive.
3. El Niño contributed on the order of 0.1 degrees C to the 2023-24 global temperature records; the forced warming trend dominates.

## Data sources and licences

`src/sources.yaml` is a machine-readable registry of every source considered. Each entry carries a status, a one-line reason, the terms page, the licence identifier and the deep links. Tests enforce the registry: fetchers exist only for sources with approved or conditional status, and excluded sources appear only in the registry. Current statuses:

| Status | Sources |
|---|---|
| Approved | NOAA CPC ONI and RONI (US public domain); World Bank Pink Sheet (CC BY 4.0); FAOSTAT (CC BY 4.0, no layer yet); NOAA CPC El Niño impacts schematic (US public domain) |
| Conditional | FEWS NET (open API, custom attribution, reporting gaps in 2026); ReliefWeb (metadata and links only); OCHA and CERF activation reports (verified per document) |
| Link only | World Weather Attribution; Carbon Brief attribution map |
| Superseded | IMF Primary Commodity Prices (duplicates the Pink Sheet under worse terms) |
| Excluded | EM-DAT (terms prohibit redistribution and derivative databases); Munich Re and Swiss Re catastrophe data (proprietary) |
| Pending | IDMC; UNDRR DesInventar; GDACS; IFRC GO; Panama Canal Authority |

Excluded sources may inform the accompanying paper and contribute nothing to the atlas.

## Repository layout

```
app.py                   Dash application, exposing `server` for gunicorn
run.py                   Command line: `dashboard` serves the site, `update` refreshes snapshots
config.py                Host, port and debug from environment variables
src/sources.yaml         Source registry (statuses, reasons, terms, licences, links)
src/schema.py            Tidy long-format contract and validation, including the registry gate
src/data_access.py       Snapshot reading and writing
src/enso_events.py       ENSO classification on CPC's rule
src/activations.py       Validation and loading of curated activation entries
src/fetchers/            One module per approved source: fetch and parse
src/layers/              One module per panel: figure and explainer text
src/layout/              Page builders, three-state legend, explainer rendering
src/theme.py             Colour tokens and Plotly templates
assets/                  Static files served with the page, with provenance notes
data/curated/            Hand-curated entries
data/snapshots/          Latest snapshot per source, written by the nightly job
tests/                   Test suite; `fixtures/` holds copies of source files with provenance notes
docs/DESIGN.md           Design record: scope, layers, rules, guardrails, deferred items
CITATION.cff             Citation metadata and the concept DOI
CLAUDE.md                Standing rules for coding agents working in this repository
LICENSE                  MIT licence for the code
pyproject.toml           Project metadata and dependencies; `uv.lock` pins them
render.yaml              Hosting configuration
.github/workflows/       Continuous integration and the nightly update
.pre-commit-config.yaml  Lint and the gate tests before each commit
```

## Run it locally

```
uv sync
uv run python run.py update
uv run python run.py dashboard
uv run pytest
```

`pip install .` also works from a clean checkout. The site reads the snapshots that `update` writes.

## Cite

Cite the software with the concept DOI, which resolves to the latest version: https://doi.org/10.5281/zenodo.22644790. `CITATION.cff` carries the full reference. Cite each data source under its own terms. The source line on each panel gives the attribution.

## Corrections

Open an issue with the source URL. A correction to a curated entry needs the primary document that supports it. A source's status changes only with its terms page cited in the registry.

## Licence

Code: MIT. Data: per source, as listed in `src/sources.yaml` and shown on each panel.
