"""Fetcher stub for the World Bank Commodity Price Data ("Pink Sheet").

Provenance
----------
publisher:      World Bank, Prospects Group
dataset:        Commodity Price Data (the "Pink Sheet"), monthly nominal
                prices for energy, agriculture, fertilisers and metals
url:            https://www.worldbank.org/en/research/commodity-markets
licence:        CC BY 4.0
redistribution: yes
attribution:    "Source: World Bank Commodity Price Data (the Pink Sheet),
                CC BY 4.0"
cadence:        monthly
latency:        typically the first week of the following month
registry id:    worldbank_pink_sheet (src/sources.yaml)

Role in the atlas
-----------------
Realised-impact stage: commodity price co-movement with the ENSO state.
Price transmission is disputed; captions must follow the guardrails in
docs/DESIGN.md.
"""

SOURCE_ID = "worldbank_pink_sheet"


def fetch() -> None:
    """Download and parse the Pink Sheet workbook. Not yet implemented."""
    raise NotImplementedError("worldbank_pink_sheet fetcher is a stub; see src/sources.yaml")
