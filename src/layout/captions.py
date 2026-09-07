"""The caption guardrails of docs/DESIGN.md, verbatim.

Every caption or annotation that touches growth, price transmission or
the 2023-24 temperature contribution carries the corresponding wording.
A panel attaches the caption it needs through ``Explainer.captions``.
``tests/test_layout.py`` checks each constant against its blockquote in
docs/DESIGN.md, so the two cannot drift apart.
"""

GROWTH = (
    "El Niño's depressing effect on growth in exposed economies is directionally "
    "supported across independent studies; headline dollar magnitudes are contested "
    "on econometric grounds."
)

PRICE_TRANSMISSION = (
    "ENSO-to-price transmission is disputed and may have weakened in recent decades; "
    "treat price co-movements as suggestive."
)

TEMPERATURE_CONTRIBUTION = (
    "El Niño contributed on the order of 0.1 degrees C to the 2023-24 global "
    "temperature records; the forced warming trend dominates."
)

# In the order the guardrails appear in docs/DESIGN.md.
CAPTIONS: tuple[str, ...] = (GROWTH, PRICE_TRANSMISSION, TEMPERATURE_CONTRIBUTION)
