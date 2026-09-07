# Provenance: World Bank Commodity Price Data (the Pink Sheet) fixture

Registry id: `worldbank_pink_sheet` (`src/sources.yaml`). Publisher:
World Bank, Prospects Group.

## File

| File | Exact URL used | Retrieved (UTC) | sha256 | Bytes |
|---|---|---|---|---|
| `CMO-Historical-Data-Monthly.xlsx` | https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx | 2026-09-07T14:31:37Z | 9fdcfa8a2aed9a1bb545a10c1a5ce036c6a0acd4766f450424ca800b4b5a0225 | 586735 |

The response carried `Last-Modified: Wed, 02 Sep 2026 20:17:37 GMT`, and
cell A4 of the `Monthly Prices` sheet reads "Updated on September 02,
2026". The file was downloaded with PowerShell `Invoke-WebRequest` and
copied into this folder unchanged; the hash was recomputed after the
copy.

## How the link was found (rotation note)

The durable page is https://www.worldbank.org/en/research/commodity-markets
(fetched 2026-09-07T14:30:34Z). Its link with the text "Monthly prices"
pointed to the URL above. The path segment
`74e8be41ceb20fa0da750cda2f6b9e4e-0050012026` changes with each release,
so the fetcher resolves the current link from the durable page on every
run by the file name `CMO-Historical-Data-Monthly.xlsx` and never stores
the deep link as durable. The same page linked
`CMO-Historical-Data-Annual.xlsx` and the September 2026 Pink Sheet PDF.

## Layout at retrieval

- Sheets: `Mismatch Details`, `Monthly Prices`, `Monthly Indices`,
  `Description`, `Index Weights`. `Mismatch Details` is a cell-by-cell
  comparison table left in the published workbook; the parser reads only
  `Monthly Prices`, by name.
- `Monthly Prices`: rows 1 to 4 hold titles and the update date; row 5
  holds the series names; row 6 holds the units in parentheses, for
  example `($/kg)`; rows 7 to 806 hold the data for `1960M01` to
  `2026M08` (800 rows), with the period in column A as `YYYYMmm`.
- This release has no row of series codes such as `COFFEE_ARABIC`, and no
  such string appears in any sheet.
- Unavailable values are marked with the character "…" (U+2026). The
  workbook's own note (sheet `Description`, cell B130) reads: "Periods
  where data are unavailable are indicated by "..". Column `DAP` uses a
  three-dot string for 1960M01 to 1966M12, and four cells of
  `Rice, Thai 25%` contain `#VALUE!`. The five default series
  (`Cocoa` column L, `Coffee, Arabica` M, `Coffee, Robusta` N,
  `Rice, Thai 5%` AG, `Sugar, world` AV) are numeric in all 800 rows.
  The name in cell AG5 carries a trailing space in the workbook.

## Terms

- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)
  under the World Bank Terms of Use for Datasets,
  https://www.worldbank.org/ext/en/legal/terms-conditions/datasets
  (fetched 2026-09-07). The older address
  https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets now
  resolves to the general Terms and Conditions page.
- Attribution wording those terms require: "You agree to provide
  attribution to The World Bank and its data providers in the following
  format: The World Bank: Dataset name: Data source (if known)." The
  dataset name on the workbook is "World Bank Commodity Price Data (The
  Pink Sheet)". The `Description` sheet names the underlying providers
  per series (for the five default series: the International Cocoa
  Organization, the International Coffee Organization, the International
  Sugar Organization, Bloomberg Finance L.P., Thomson Reuters Datastream
  and the World Bank).
- The terms add a mandatory dispute-resolution clause to CC BY 4.0, require
  the same acknowledgement in any sub-licence, and note that some
  third-party data may carry different conditions.

## Cadence

Monthly. The Pink Sheet is published in the first week of the month with
data to the end of the previous month; this release is dated
2 September 2026 and runs to `2026M08`.
