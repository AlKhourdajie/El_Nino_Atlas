"""Validation of the hand-curated activation register."""

from datetime import date

import pytest

from src.activations import REGISTER_PATH, load_activations, validate_activation


def example_entry() -> dict:
    return {
        "date": date(2026, 1, 1),
        "region": "Example region",
        "country": "Example country",
        "framework": "Example framework",
        "agencies": ["Example agency"],
        "amount_usd": None,
        "people_covered": None,
        "trigger": "Example trigger",
        "source_url": "https://example.org/x",
        "retrieved_at": "2026-09-05T00:00:00Z",
    }


def test_register_file_validates():
    entries = load_activations(REGISTER_PATH, include_examples=True)
    assert entries, "register should contain at least the example entry"
    assert all(isinstance(e, dict) for e in entries)


def test_examples_are_excluded_by_default():
    all_entries = load_activations(REGISTER_PATH, include_examples=True)
    rendered = load_activations(REGISTER_PATH)
    assert all(not e.get("example", False) for e in rendered)
    assert len(rendered) == len([e for e in all_entries if not e.get("example", False)])


def test_valid_entry_passes():
    validate_activation(example_entry())
    validate_activation({**example_entry(), "example": True})
    validate_activation({**example_entry(), "amount_usd": 1_500_000, "people_covered": 20_000})


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda e: e.pop("trigger"), r"missing fields \['trigger'\]"),
        (lambda e: e.update(extra=1), r"unknown fields \['extra'\]"),
        (lambda e: e.update(example="yes"), "'example' must be true or false"),
        (lambda e: e.update(date="2026-01-01"), "'date' must be an ISO calendar date"),
        (lambda e: e.update(country=""), "'country' must be a non-empty string"),
        (lambda e: e.update(agencies=[]), "'agencies' must be a non-empty list"),
        (lambda e: e.update(agencies=["ok", ""]), r"agencies\[1\] must be a non-empty string"),
        (lambda e: e.update(amount_usd="1m"), "'amount_usd' must be a number or null"),
        (lambda e: e.update(amount_usd=-5), "'amount_usd' must not be negative"),
        (lambda e: e.update(people_covered=12.5), "'people_covered' must be an integer or null"),
        (lambda e: e.update(source_url="example.org"), "'source_url' must be an http\\(s\\) URL"),
        (lambda e: e.update(retrieved_at="2026-09-05"), "'retrieved_at' must be a UTC ISO 8601"),
    ],
)
def test_invalid_entries_raise(mutation, message):
    entry = example_entry()
    mutation(entry)
    with pytest.raises(ValueError, match=message):
        validate_activation(entry)


def test_non_mapping_entry_raises():
    with pytest.raises(ValueError, match="entry must be a mapping"):
        validate_activation(["not", "a", "mapping"])
