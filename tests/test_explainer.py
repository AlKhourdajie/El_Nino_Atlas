"""Tests for the panel explainer contract in src/layout/explainer.py."""

from dataclasses import FrozenInstanceError

import pytest

from src.layout.explainer import Explainer, render_explainer

LABELS = (
    "What this shows",
    "How it is measured",
    "Why it matters for El Niño",
    "What it does not show",
)
SOURCE_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php"


def example(captions: tuple[str, ...] = ("Figures are authored in degrees C.",)) -> Explainer:
    return Explainer(
        title="Oceanic Niño Index",
        what="The three-month running mean of sea surface temperature anomalies.",
        how="NOAA computes the index from ERSSTv5 in the Niño 3.4 region.",
        why="It is the index behind the NOAA definition of an El Niño event.",
        not_shown="It does not show rainfall or temperature over land.",
        source_name="NOAA Climate Prediction Center",
        source_url=SOURCE_URL,
        licence_label="US Government work, public domain",
        captions=captions,
    )


def test_rendered_card_has_four_labels_and_source():
    rendered = str(render_explainer(example(), retrieved_at="2026-09-05T17:00:00Z"))
    for label in LABELS:
        assert label in rendered
    assert SOURCE_URL in rendered
    assert "NOAA Climate Prediction Center" in rendered
    assert "US Government work, public domain" in rendered
    assert "retrieved 2026-09-05T17:00:00Z" in rendered
    assert "Figures are authored in degrees C." in rendered


def test_labels_appear_in_contract_order():
    rendered = str(render_explainer(example()))
    positions = [rendered.index(label) for label in LABELS]
    assert positions == sorted(positions)


def test_retrieved_clause_omitted_without_timestamp():
    rendered = str(render_explainer(example()))
    assert "retrieved" not in rendered


def test_captions_default_to_empty_and_record_is_frozen():
    explainer = example(captions=())
    assert explainer.captions == ()
    with pytest.raises(FrozenInstanceError):
        explainer.title = "changed"
