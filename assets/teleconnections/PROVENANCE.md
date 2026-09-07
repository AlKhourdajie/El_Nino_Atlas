# Provenance: NOAA Climate Prediction Center El Niño impacts schematic

The file beside this note, `noaa_cpc_elnino_impacts.jpg`, is the
schematic the draft teleconnection layer shows on the page. It is
byte-identical to the image retrieved from the publisher; only the file
name differs, to state the content and the actual format. Nothing was
cropped, resized or re-encoded.

| Field | Value |
|---|---|
| Publisher | NOAA Climate Prediction Center (NCEP/NWS) |
| Dataset | "Warm Episode Relationships": typical El Niño impacts, December to February (upper panel) and June to August (lower panel) |
| Page URL | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml |
| Image URL | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/impacts/warm.gif |
| Retrieved | 2026-09-07T14:36:16Z |
| sha256 | 849985b5dfc4c951ea7206da135c16d7a4c313addf7f77b071d54c12104d26c5 |
| Size | 143255 bytes |
| Format | JPEG, 940 by 1215 pixels, RGB; the server names the file `.gif` and serves it as `image/gif` |
| Server Last-Modified | Wed, 07 Nov 2012 13:57:16 GMT |
| Licence | US Government work, public domain |
| Attribution | Source: NOAA Climate Prediction Center, typical El Niño temperature and precipitation patterns |
| Registry | `noaa_cpc_enso_impacts_schematic` in `src/sources.yaml`: status approved, redistribution yes, licence_id LicenseRef-US-PD |

The retrieval record is also kept as `noaa_cpc_elnino_impacts_warm.retrieval.json`
in the private `local/candidates/` folder of the main clone, beside the
hand-drawn polygon mask `teleconnections_djf_schematic.geojson`, which is
a draft and is not rendered.

`tests/test_teleconnections.py` checks that the asset's sha256 matches the
value above.
