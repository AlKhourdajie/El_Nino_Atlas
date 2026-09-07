"""Tests for the panel explainer contract in src/layout/explainer.py."""

from dataclasses import FrozenInstanceError, replace

import pytest
from dash import html

from src.layout.explainer import (
    METHOD_SUMMARY,
    Explainer,
    explainer_body,
    explainer_header,
    lede,
    render_explainer,
    split_lede,
)
from tests.support import walk

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
        what=(
            "The three-month running mean of sea surface temperature anomalies. "
            "Each point is one season."
        ),
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
    assert METHOD_SUMMARY in rendered
    assert SOURCE_URL in rendered
    assert "NOAA Climate Prediction Center" in rendered
    assert "US Government work, public domain" in rendered
    assert "retrieved 2026-09-05T17:00:00Z" in rendered
    assert "Figures are authored in degrees C." in rendered


def test_header_carries_the_lede_source_and_disclosure_and_body_the_rest():
    header = explainer_header(example(), retrieved_at="2026-09-05T17:00:00Z")
    lede_line, source, disclosure = header
    assert (
        lede_line.children == "The three-month running mean of sea surface temperature anomalies."
    )
    assert isinstance(disclosure, html.Details)
    assert disclosure.children[0].children == METHOD_SUMMARY
    assert "How it is measured" in str(disclosure)
    assert "ERSSTv5" in str(disclosure)
    rendered_source = str(source)
    assert "Source: " in rendered_source and "retrieved 2026-09-05T17:00:00Z" in rendered_source
    body = str(explainer_body(example()))
    positions = [body.index(label) for label in (LABELS[0], LABELS[2], LABELS[3])]
    assert positions == sorted(positions)
    assert "Each point is one season." in body
    assert "ERSSTv5" not in body, "the how block lives in the disclosure only"


def test_lede_and_rest_join_back_to_the_block():
    for text in (
        example().what,
        "One sentence only.",
        "Ends with a number 3.4 then continues. Second sentence here.",
        "Quoted? 'Yes' it is. Then more.",
    ):
        first, rest = split_lede(text)
        assert (first + " " + rest if rest else first) == text
        assert first.endswith((".", "?", "!"))
    assert lede(example()) == split_lede(example().what)[0]
    assert split_lede("One sentence only.") == ("One sentence only.", "")


def test_retrieved_clause_omitted_without_timestamp():
    rendered = str(render_explainer(example()))
    assert "retrieved" not in rendered


def test_captions_default_to_empty_and_record_is_frozen():
    explainer = example(captions=())
    assert explainer.captions == ()
    with pytest.raises(FrozenInstanceError):
        explainer.title = "changed"


def test_link_in_a_block_renders_as_an_anchor():
    linked = replace(example(), how="Defined on the [CPC page](https://example.org/roni) in full.")
    card = render_explainer(linked)
    anchors = [c for c in walk(card) if isinstance(c, html.A)]
    (link,) = [a for a in anchors if a.href == "https://example.org/roni"]
    assert link.children == "CPC page"
    how = next(
        c
        for c in walk(card)
        if isinstance(c, html.P) and isinstance(c.children, list) and link in c.children
    )
    assert how.children == ["Defined on the ", link, " in full."]
    assert "](" not in str(card)


def test_blocks_without_links_render_as_plain_text():
    card = render_explainer(example())
    assert not [c for c in walk(card) if isinstance(c, html.A) and c.href != SOURCE_URL]
