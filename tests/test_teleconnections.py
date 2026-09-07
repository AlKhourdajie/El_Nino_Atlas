"""Tests for the draft teleconnection schematic layer in src/layers/teleconnections.py."""

import copy
import hashlib
import json
import re

import plotly.graph_objects as go
import pytest
from dash import html

from src import theme
from src.layers import teleconnections as tc
from src.layout.explainer import BLOCKS, Explainer, render_explainer
from tests.support import walk


def square(lon0: float, lat0: float, size: float = 10.0) -> dict:
    lon1, lat1 = lon0 + size, lat0 + size
    return {
        "type": "Polygon",
        "coordinates": [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]],
    }


# A band split at the antimeridian, as the curated file will carry it.
TWO_PARTS = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[170.0, -5.0], [180.0, -5.0], [180.0, 5.0], [170.0, 5.0], [170.0, -5.0]]],
        [[[-180.0, -5.0], [-170.0, -5.0], [-170.0, 5.0], [-180.0, 5.0], [-180.0, -5.0]]],
    ],
}


def feature(signal: str, note: str, geometry: dict) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "signal": signal,
            "season": "DJF",
            "basis": "NOAA CPC schematic, DJF",
            "note": note,
        },
        "geometry": geometry,
    }


def collection(*features: dict) -> dict:
    return {"type": "FeatureCollection", "features": list(features)}


def synthetic() -> dict:
    return collection(
        feature("warmer_and_wetter", "Band: wetter and warmer than normal.", TWO_PARTS),
        feature("wetter", "Region A: wetter than normal.", square(10, 10)),
        feature("drier", "Region C: drier than normal.", square(-60, -20)),
        feature("wetter", "Region B: wetter than normal.", square(30, -30)),
    )


def test_one_filled_trace_per_signal_class_in_drawing_order():
    fig = tc.build_figure(synthetic())
    assert isinstance(fig, go.Figure)
    assert [trace.name for trace in fig.data] == ["Wetter", "Drier", "Warmer and wetter"]
    for trace in fig.data:
        assert isinstance(trace, go.Scattergeo)
        assert trace.fill == "toself"
        assert trace.mode == "lines"
        assert trace.hoverinfo == "text"


def test_rings_are_separated_by_gaps_and_carry_their_note():
    fig = tc.build_figure(synthetic())
    by_name = {trace.name: trace for trace in fig.data}

    band = by_name["Warmer and wetter"]
    assert list(band.lon).count(None) == 1
    assert list(band.lat).count(None) == 1
    assert band.lon[0] == 170.0 and band.lon[4] == 170.0
    assert band.lon[-1] == -180.0

    wetter = by_name["Wetter"]
    assert list(wetter.lon).count(None) == 1
    notes = [text for text in wetter.text if text]
    assert set(notes) == {"Region A: wetter than normal.", "Region B: wetter than normal."}
    assert len(notes) == len(wetter.lon) - 1
    assert wetter.legendgroup == "wetter"
    assert wetter.line.color == tc.SIGNAL_COLOURS["wetter"]


def test_layout_is_a_locked_draft_map():
    fig = tc.build_figure(synthetic())
    assert fig.layout.dragmode is False
    assert "draft" in fig.layout.title.text.lower()
    assert fig.layout.showlegend is True
    assert fig.layout.legend.title.text == tc.LEGEND_TITLE
    assert fig.layout.geo.projection.type == "natural earth"
    assert fig.layout.geo.showcoastlines is True
    assert fig.layout.geo.showland is True
    assert tc.GRAPH_CONFIG["scrollZoom"] is False


def test_input_is_not_mutated():
    geojson = synthetic()
    before = copy.deepcopy(geojson)
    tc.build_figure(geojson)
    assert geojson == before


def test_signal_vocabulary_and_colours():
    assert set(tc.SIGNAL_LABELS) == set(tc.SIGNALS)
    assert set(tc.SIGNAL_COLOURS) == set(tc.SIGNALS)
    colours = list(tc.SIGNAL_COLOURS.values())
    assert len(set(colours)) == len(colours)
    assert not set(colours) & set(theme.STATE_COLOURS.values())
    for signal in ("wetter", "drier", "warmer", "cooler", "warmer_and_drier", "cooler_and_wetter"):
        assert signal in tc.SIGNALS


def test_parse_features_returns_file_order():
    parsed = tc.parse_features(synthetic())
    assert [f.signal for f in parsed] == ["warmer_and_wetter", "wetter", "drier", "wetter"]
    assert len(parsed[0].rings) == 2
    assert parsed[1].rings[0][0] == (10.0, 10.0)


def with_hole() -> dict:
    outer = [[0, 0], [30, 0], [30, 30], [0, 30], [0, 0]]
    inner = [[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]
    return {"type": "Polygon", "coordinates": [outer, inner]}


def mutate_first(geojson: dict, **properties) -> dict:
    geojson["features"][0]["properties"].update(properties)
    return geojson


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda g: {"type": "Feature"}, "expected a GeoJSON FeatureCollection"),
        (lambda g: collection(), "the collection has no features"),
        (lambda g: mutate_first(g, signal="hotter"), "unknown signal 'hotter'"),
        (lambda g: mutate_first(g, season="JJA"), "season must be 'DJF'"),
        (lambda g: mutate_first(g, basis="computed"), "basis must be 'NOAA CPC schematic, DJF'"),
        (lambda g: mutate_first(g, note="  "), "note must be a non-empty string"),
        (lambda g: g["features"][0].pop("properties") and g, "properties must be a mapping"),
        (
            lambda g: collection(feature("wetter", "x", {"type": "Point", "coordinates": [0, 0]})),
            "geometry must be one of",
        ),
        (lambda g: collection(feature("wetter", "x", with_hole())), "holes are not supported"),
        (lambda g: collection(feature("wetter", "x", square(175, 0))), "off the globe"),
        (
            lambda g: collection(
                feature(
                    "wetter",
                    "x",
                    {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
                )
            ),
            "ring is not closed",
        ),
        (
            lambda g: collection(
                feature(
                    "wetter", "x", {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 0]]]}
                )
            ),
            "at least four positions",
        ),
    ],
)
def test_invalid_collections_raise(mutation, message):
    with pytest.raises(ValueError, match=message):
        tc.build_figure(mutation(synthetic()))


def test_load_geojson_round_trip(tmp_path):
    path = tmp_path / "schematic.geojson"
    path.write_text(json.dumps(synthetic()), encoding="utf-8")
    loaded = tc.load_geojson(path)
    assert loaded == synthetic()
    assert len(tc.build_figure(loaded).data) == 3


def test_load_geojson_rejects_bad_file(tmp_path):
    path = tmp_path / "bad.geojson"
    path.write_text(json.dumps(collection()), encoding="utf-8")
    with pytest.raises(ValueError, match="no features"):
        tc.load_geojson(path)


def test_explainer_contract_renders():
    explainer = tc.explainer()
    assert isinstance(explainer, Explainer)
    assert "draft" in explainer.title.lower()
    for field, _label in BLOCKS:
        assert getattr(explainer, field).strip()
    assert explainer.source_url.startswith("https://www.cpc.ncep.noaa.gov/")
    assert explainer.licence_label == "US Government work, public domain"
    rendered = str(render_explainer(explainer))
    for _field, label in BLOCKS:
        assert label in rendered
    assert explainer.source_url in rendered
    assert explainer.captions and "draft" in explainer.captions[0].lower()


def test_explainer_title_matches_the_section_and_how_block_carries_the_link():
    explainer = tc.explainer()
    assert explainer.title == tc.PANEL_TITLE
    link_re = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
    assert link_re.findall(explainer.how) == [(tc.SOURCE_LINK_LABEL, tc.SOURCE_URL)]
    for field in ("what", "why", "not_shown"):
        assert not link_re.search(getattr(explainer, field))
    anchors = [c for c in walk(render_explainer(explainer)) if isinstance(c, html.A)]
    # The source line precedes the "Source and method" disclosure in the card header.
    assert [(a.children, a.href) for a in anchors] == [
        (tc.SOURCE_NAME, tc.SOURCE_URL),
        (tc.SOURCE_LINK_LABEL, tc.SOURCE_URL),
    ]


def public_copy() -> list[str]:
    explainer = tc.explainer()
    return [
        explainer.title,
        explainer.what,
        explainer.how,
        explainer.why,
        explainer.not_shown,
        *explainer.captions,
        tc.TITLE,
        tc.LEGEND_TITLE,
        tc.PANEL_TITLE,
        tc.IMAGE_ALT,
        *tc.SIGNAL_LABELS.values(),
    ]


def test_public_copy_rules():
    for text in public_copy():
        assert "—" not in text, text
        assert ";" not in text, text
        assert " very " not in text and " extremely " not in text, text
    explainer = tc.explainer()
    assert "National Oceanic and Atmospheric Administration" in explainer.what
    assert "increased rainfall across the east-central and eastern Pacific" in explainer.how
    assert explainer.why.startswith("The impacts the other layers track begin with shifts")
    assert "shows where an El Niño signal is expected" in explainer.why
    assert explainer.why.endswith("and the places outside them.")
    assert explainer.captions[0].endswith(
        "above the June to August panel. The shaded areas are the publisher's own and carry "
        "no statistical test."
    )
    assert "composites computed from public-domain gridded data" in explainer.not_shown
    assert explainer.not_shown.startswith("The schematic summarises tendencies across past events")
    assert "December to February" in explainer.what


def test_not_shown_states_the_text_and_image_discrepancies():
    not_shown = tc.explainer().not_shown
    assert "Central America" in not_shown
    assert "south-western United States" in not_shown


def test_copy_names_both_panels_of_the_image():
    assert tc.PANEL_TITLE == "Where El Niño usually matters: draft schematic"
    for text in (tc.explainer().what, tc.IMAGE_ALT):
        assert "December to February above" in text
        assert "June to August below" in text


def test_image_panel_shows_the_schematic_with_its_explainer():
    panel = tc.build_image_panel()
    assert isinstance(panel, html.Section)
    rendered = str(panel)
    assert tc.IMAGE_ASSET in rendered
    assert "/assets/teleconnections/noaa_cpc_elnino_impacts.jpg" in rendered
    for _field, label in BLOCKS:
        assert label in rendered
    assert "draft" in tc.PANEL_TITLE.lower()
    assert tc.PANEL_TITLE in rendered
    assert tc.IMAGE_ALT in rendered
    assert tc.SOURCE_URL in rendered
    assert f"retrieved {tc.IMAGE_RETRIEVED_AT}" in rendered


def test_image_panel_has_the_page_panel_shape():
    panel = tc.build_image_panel()
    assert panel.id == "panel-teleconnections"
    assert panel.className == "card"
    assert next(c for c in walk(panel) if isinstance(c, html.H2)).children == tc.PANEL_TITLE
    images = [c for c in walk(panel) if isinstance(c, html.Img)]
    assert len(images) == 1 and images[0].alt == tc.IMAGE_ALT
    # The draft label stays: the title carries it and no stage overline replaces it.
    assert not [c for c in walk(panel) if getattr(c, "className", None) == "card__stage"]
    (figure,) = [c for c in walk(panel) if isinstance(c, html.Figure)]
    assert images[0] in list(walk(figure))


def test_image_fills_the_column_and_keeps_its_ratio():
    assert tc.IMAGE_STYLE["maxWidth"] == "100%"
    assert tc.IMAGE_STYLE["width"] == "100%"
    assert tc.IMAGE_STYLE["height"] == "auto"
    (image,) = [c for c in walk(tc.build_image_panel()) if isinstance(c, html.Img)]
    # The file's own pixel size, per assets/teleconnections/PROVENANCE.md.
    assert (image.width, image.height) == ("940", "1215")
    rendered = str(tc.build_image_panel())
    assert "'maxWidth': '100%'" in rendered
    assert "'height': 'auto'" in rendered


def test_image_panel_accepts_the_app_asset_url():
    rendered = str(tc.build_image_panel(image_src="/prefix/assets/x.jpg", retrieved_at=None))
    assert "/prefix/assets/x.jpg" in rendered
    assert f"retrieved {tc.IMAGE_RETRIEVED_AT}" not in rendered


def test_asset_is_byte_identical_to_the_retrieved_image():
    data = tc.IMAGE_FILE.read_bytes()
    assert data[:3] == b"\xff\xd8\xff", "the asset is a JPEG"
    assert hashlib.sha256(data).hexdigest() == tc.IMAGE_SHA256
    provenance = (tc.IMAGE_FILE.parent / "PROVENANCE.md").read_text(encoding="utf-8")
    for needle in (tc.IMAGE_SHA256, tc.IMAGE_RETRIEVED_AT, tc.IMAGE_URL, tc.SOURCE_URL):
        assert needle in provenance
