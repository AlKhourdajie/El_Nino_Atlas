"""The public strings of the page are byte-identical to the pre-design baseline.

``tests/baseline_strings.py`` inventories every caption, legend, hero and
footer string. The digests below were recorded from the code before the
design pass (they are the content of ``local/qa/baseline-strings.sha256``,
which is gitignored); the test recomputes them and names any key that
drifted. When the local record exists it is compared as well.
"""

from pathlib import Path

from tests.baseline_strings import baseline_strings, digest, parse_record

ROOT = Path(__file__).resolve().parent.parent
LOCAL_RECORD = ROOT / "local" / "qa" / "baseline-strings.sha256"

# Recorded on 7 September 2026 before the design pass, keys sorted.
EXPECTED: dict[str, str] = {
    "about.0": "4cb6e6d5556d9ebc9418dc93d80e3aba88224123ccef691ead96bff902de3b5e",
    "about.1": "0c60676893764178a4cc49b424705dc4c4941aa4bb3dd9421f2a500435f1b073",
    "axis.commodities.y": "068abed60b9d4f89669d570608373dfe09f7b5f4d520896dae2a8804828384d0",
    "axis.index.y": "d2ce2307fbbe2501de3fee8a478b5ba0f570fb6e767945936c5e49e539836cf2",
    "caption.growth": "be717130c253c17c67a3385e718e741ee24591a0a1c51a36e574294859d0ace4",
    "caption.price_transmission": (
        "619cdd47d353064590472cc74864059e10ddad71bb75299e58d0359730dbd895"
    ),
    "caption.rebase": "6c520c5e85ddf9fc280efa015c49b621761ef9bbe80b18b10956ff19f4d02013",
    "caption.temperature_contribution": (
        "8f8977fa104da898bbdf34105508720629b9304ab221413bb69397399dc1b6c3"
    ),
}


def test_inventory_covers_every_public_string_family():
    strings = baseline_strings()
    families = {key.split(".")[0] for key in strings}
    assert {
        "hero",
        "about",
        "footer",
        "caption",
        "legend",
        "axis",
        "explainer",
        "panel",
        "table",
        "range",
        "series",
        "teleconnections",
        "reading",
        "notice",
    } <= families
    assert len(strings) >= 100


def test_recorded_digests_match():
    strings = baseline_strings()
    drifted = {
        key: digest(strings[key])
        for key, expected in EXPECTED.items()
        if digest(strings[key]) != expected
    }
    assert not drifted, f"strings drifted from the baseline: {sorted(drifted)}"


def test_local_record_matches_when_present():
    if not LOCAL_RECORD.is_file():
        return
    record = parse_record(LOCAL_RECORD.read_text(encoding="utf-8"))
    strings = baseline_strings()
    missing = sorted(set(record) - set(strings) - {"hero.reading"})
    assert not missing, f"inventory lost keys: {missing}"
    drifted = sorted(
        key
        for key, expected in record.items()
        if key in strings and digest(strings[key]) != expected
    )
    assert not drifted, f"strings drifted from local/qa/baseline-strings.sha256: {drifted}"
