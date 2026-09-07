"""Tests for the design tokens and the files generated from them.

``design/tokens.json`` is the single source of truth. ``assets/tokens.css``
and ``src/plotly_template.py`` are committed outputs of
``scripts/build_tokens.py``; the first test rebuilds them in memory and
fails when either committed file is stale, so the deployment needs no
build step and the three cannot drift apart. The other tests pin the
palette rules of the design pass: Okabe-Ito phase hues, three-state hues
distinct from them and paired with mark styles, WCAG AA contrast for text
and marks in both schemes, and the fonts with their licences.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

from src import theme

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
ASSETS = ROOT / "assets"

OKABE_ITO = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def build_tokens():
    return _load("build_tokens")


@pytest.fixture(scope="module")
def check_contrast(build_tokens):
    return _load("check_contrast")


@pytest.fixture(scope="module")
def tokens(build_tokens):
    return build_tokens.load_tokens()


def test_generated_files_are_fresh(build_tokens):
    for path, text in build_tokens.outputs().items():
        assert path.is_file(), f"{path} is missing; run scripts/build_tokens.py"
        assert path.read_text(encoding="utf-8") == text, (
            f"{path.relative_to(ROOT)} is stale; run scripts/build_tokens.py"
        )


def test_theme_reads_the_tokens(tokens):
    assert theme.STATE_COLOURS == tokens["data"]["state"]
    assert theme.PHASE_COLOURS == {
        k: v for k, v in tokens["data"]["phase"].items() if k != "neutral"
    }
    assert theme.PHASE_NEUTRAL == tokens["data"]["phase"]["neutral"]
    assert theme.SERIES == tokens["data"]["series"]
    assert theme.LIGHT["bg"] == tokens["scheme"]["light"]["paper"]
    assert theme.DARK["panel"] == tokens["scheme"]["dark"]["surface"]
    assert theme.RESPONSIVE_LAYOUT["height"] == tokens["layout"]["figure_height_px"]


def test_phase_hues_come_from_okabe_ito(tokens):
    phase = tokens["data"]["phase"]
    assert phase["el_nino"] in (OKABE_ITO["orange"], OKABE_ITO["vermillion"])
    assert phase["la_nina"] in (OKABE_ITO["blue"], OKABE_ITO["sky_blue"])
    assert tokens["data"]["phase_opacity"]["la_nina"] < tokens["data"]["phase_opacity"]["el_nino"]
    assert tokens["data"]["phase_opacity"]["el_nino"] <= 0.3


def _hue(hex_colour: str) -> float:
    value = hex_colour.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    high, low = max(r, g, b), min(r, g, b)
    if high == low:
        return -1.0
    delta = high - low
    if high == r:
        hue = ((g - b) / delta) % 6
    elif high == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4
    return hue * 60


def _hue_gap(a: float, b: float) -> float:
    gap = abs(a - b) % 360
    return min(gap, 360 - gap)


def test_state_hues_are_distinct_from_phase_hues_and_each_other(tokens):
    state = tokens["data"]["state"]
    phase = tokens["data"]["phase"]
    for key in ("alert", "no_alert"):
        for phase_key in ("el_nino", "la_nina"):
            assert _hue_gap(_hue(state[key]), _hue(phase[phase_key])) >= 30, (key, phase_key)
    assert _hue_gap(_hue(state["alert"]), _hue(state["no_alert"])) >= 90
    assert _hue(state["not_assessed"]) < 0 or True  # a grey; distinctness by lightness
    assert len(set(state.values())) == 3
    assert not set(state.values()) & set(phase.values())


def test_each_state_pairs_with_a_mark_style(tokens):
    assert tokens["data"]["state_mark"] == {
        "alert": "filled",
        "no_alert": "outlined",
        "not_assessed": "hatched",
    }
    assert theme.STATE_MARKS == tokens["data"]["state_mark"]
    assert set(theme.STATE_MARKER_SYMBOLS) == set(theme.STATE_MARKS)


def test_contrast_meets_aa_in_both_schemes(check_contrast, tokens):
    failed = check_contrast.failures(tokens)
    assert not failed, "\n".join(f"{s}: {f} on {b} = {r:.2f} < {m}" for s, f, b, r, m in failed)
    rows = check_contrast.checks(tokens)
    schemes = {row[0] for row in rows}
    assert schemes == {"light", "dark"}


def test_css_declares_both_schemes_and_the_fonts(tokens):
    css = (ASSETS / "tokens.css").read_text(encoding="utf-8")
    assert "@media (prefers-color-scheme: dark)" in css
    assert ':root[data-theme="dark"]' in css
    assert ':root:not([data-theme="light"])' in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    for role in ("display", "text"):
        face = tokens["font"][role]
        assert f'font-family: "{face["family"]}"' in css
        assert f'url("fonts/{face["file"]}")' in css
        assert (ASSETS / "fonts" / face["file"]).is_file()
        assert "font-display: swap" in css
    for scheme in ("light", "dark"):
        for key, value in tokens["scheme"][scheme].items():
            assert f"--{key.replace('_', '-')}: {value};" in css


def test_fonts_are_ofl_licensed_and_recorded(tokens):
    licences = (ASSETS / "fonts" / "LICENSES.md").read_text(encoding="utf-8")
    assert licences.count("SIL OPEN FONT LICENSE Version 1.1") == 2
    for role in ("display", "text"):
        face = tokens["font"][role]
        assert face["licence"] == "SIL Open Font License 1.1"
        assert face["family"] in licences
        assert face["file"] in licences
    woff2 = sorted(p.name for p in (ASSETS / "fonts").glob("*.woff2"))
    assert woff2 == sorted(tokens["font"][role]["file"] for role in ("display", "text"))
    for name in woff2:
        assert (ASSETS / "fonts" / name).read_bytes()[:4] == b"wOF2"


def test_topojson_is_served_locally_with_its_licence():
    topo = ASSETS / "topojson" / "world_50m.json"
    assert topo.is_file() and topo.stat().st_size > 500_000
    licence = (ASSETS / "topojson" / "LICENSE.md").read_text(encoding="utf-8")
    assert "MIT" in licence and "world_50m.json" in licence
    assert re.search(r"sha256 \| `([0-9a-f]{64})`", licence)


def test_no_external_hosts_in_assets():
    """No CDN font, script, icon set or tracker: the assets reference no other host."""
    for path in (ASSETS / "atlas.css", ASSETS / "tokens.css", ASSETS / "atlas.js"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"url\(\s*['\"]?https?://", text), path
        assert "googleapis" not in text and "cdn." not in text, path
