"""Fetcher stub for the NOAA Oceanic Niño Index (ONI).

Provenance
----------
publisher:      NOAA Climate Prediction Center (NCEP/NWS)
dataset:        Oceanic Niño Index (ONI), version 5, three-month running
                mean of ERSSTv5 SST anomalies in the Niño 3.4 region
url:            https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php
licence:        US Government work, public domain
redistribution: yes
attribution:    "Source: NOAA Climate Prediction Center, Oceanic Niño Index (ONI)"
cadence:        monthly
latency:        roughly the first two weeks of the following month
registry id:    noaa_oni (src/sources.yaml)

Role in the atlas
-----------------
Forecast-stage layer: the headline ENSO state indicator.
"""

SOURCE_ID = "noaa_oni"


def fetch() -> None:
    """Download and parse the ONI table. Not yet implemented."""
    raise NotImplementedError("noaa_oni fetcher is a stub; see src/sources.yaml")
