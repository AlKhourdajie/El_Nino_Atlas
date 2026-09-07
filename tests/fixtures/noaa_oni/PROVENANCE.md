# Provenance: NOAA CPC ONI and RONI fixtures

Registry id: `noaa_oni` (`src/sources.yaml`). Publisher: NOAA Climate
Prediction Center (CPC), National Weather Service.

## Files

| File | Exact URL used | Retrieved (UTC) | sha256 | Bytes |
|---|---|---|---|---|
| `oni.ascii.txt` | https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt | 2026-09-07T14:30:23Z | 93f8c86c7a660f46318abe33b38c0479d184812d95a479a1fe869c0c2363a9e4 | 23000 |
| `RONI.ascii.txt` | https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt | 2026-09-07T14:30:26Z | 2f1c446b0c293358af6452808799b0dca75f89b0a1d6f86eb1887dc3de9b5eae | 14720 |

Both files were downloaded with PowerShell `Invoke-WebRequest` and copied
into this folder unchanged; the hashes above were recomputed after the
copy. Both are plain ASCII with LF line endings, which is how git stores
them; a checkout with `core.autocrlf` set to true rewrites the working
copy with CRLF, so the hashes apply to the LF bytes as downloaded.

## Content at retrieval

- `oni.ascii.txt`: header `SEAS  YR   TOTAL   ANOM`, then 919 rows from
  `DJF 1950` to `JJA 2026`. `TOTAL` is the three-month mean Niño 3.4 sea
  surface temperature in degrees C; `ANOM` is the ONI in degrees C.
- `RONI.ascii.txt`: header `SEAS   YR  ANOM`, then 919 rows from
  `DJF 1950` to `JJA 2026`. There is no `TOTAL` column.
- Values carry two decimals. Rounded to one decimal they agree with the
  CPC tables based on ERSSTv6 (ONI table at `.../enso/oni/v6/`, RONI
  table at `.../enso/roni/`) in all but 3 of 919 ONI cells and 7 of 919
  RONI cells, each a value ending in 5 that the table rounds the other
  way. They do not agree with the older ERSSTv5 tables (`.../oni/v5/`
  and `.../roni/v5/` differ in 532 and 544 cells).
- Season convention: the table year is the centre month's year, so
  `DJF 1950` covers December 1949 to February 1950 and `NDJ 1950` covers
  November 1950 to January 1951. The CPC tables show the same rows under
  the column headings "Dec Jan Feb" to "Nov Dec Jan".

## Terms

- Licence: work of the United States Government, public domain
  (registry `licence_id` `LicenseRef-US-PD`).
- Attribution: the CPC pages state no attribution requirement. Their
  footers link the National Weather Service disclaimer at
  https://weather.gov/disclaimer.php, which was not fetched in this
  session because the host is outside the permitted list. The atlas
  renders the registry attribution string wherever the data appear.

## Cadence and revision

- The ONI and RONI table pages state: "This page is updated by the 5th
  of each month." The session brief expected an update around the 10th;
  the files retrieved on 7 September 2026 already contained `JJA 2026`.
- The same pages state that, because of the high-frequency filter applied
  to the ERSST data, values "may change up to two months after the
  initial 'real time' value is posted", so the most recent values are
  estimates and a snapshot can change retrospectively.
- Per NWS Public Information Statement 26-05, linked from the ONI page,
  the RONI is used for official ENSO monitoring and prediction. The ONI
  page continues to be updated.

## Pages consulted on 2026-09-07 (all on www.cpc.ncep.noaa.gov)

- `/products/analysis_monitoring/ensostuff/ONI_v5.php` (the registry
  `url`; now a notice that the page has moved to the ERSSTv6 table)
- `/products/analysis_monitoring/enso/oni/v6/` (ONI table, ERSSTv6)
- `/products/analysis_monitoring/enso/oni/v5/` (ONI table, ERSSTv5)
- `/products/analysis_monitoring/enso/roni/` (RONI table, ERSSTv6)
- `/products/analysis_monitoring/enso/roni/v5/` (RONI table, ERSSTv5)
- `/data/indices/` (directory listing that links both files)
