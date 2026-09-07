"""Validation of the hand-curated activation register."""

from datetime import date

import pycountry
import pytest
import yaml

from src.activations import (
    FRAMEWORKS,
    REGISTER_PATH,
    REQUIRED_FIELDS,
    STATUSES,
    load_activations,
    validate_activation,
)

WAYBACK = "https://web.archive.org/web/20260907000000/https://example.org/x"


def example_entry() -> dict:
    return {
        "id": "example_gtm_cerf_aa",
        "iso3": "GTM",
        "country": "Guatemala",
        "framework": "cerf_aa",
        "status": "activated",
        "activation_date": date(2026, 3, 5),
        "trigger": "Example trigger",
        "forecast_source": "Example forecast source",
        "amount_usd": 1_000_000,
        "people_targeted": 20_000,
        "sector": "Example sector",
        "source_url": "https://example.org/x",
        "wayback_url": WAYBACK,
        "retrieved": "2026-09-07T00:00:00Z",
        "discrepancies": [],
    }


def no_activation_entry() -> dict:
    return {
        **example_entry(),
        "id": "example_nic_cerf_aa",
        "iso3": "NIC",
        "country": "Nicaragua",
        "status": "framework_no_activation",
        "activation_date": None,
        "amount_usd": None,
        "people_targeted": None,
    }


def discrepancy() -> dict:
    return {
        "statement": "Amount released, companion document",
        "value": 900_000,
        "source_url": "https://example.org/companion",
    }


def test_register_file_validates():
    entries = load_activations(REGISTER_PATH, include_examples=True)
    assert entries, "register should contain at least the example entry"
    assert all(isinstance(e, dict) for e in entries)
    assert all(set(REQUIRED_FIELDS) <= set(e) for e in entries)


def test_register_iso3_codes_are_known_to_pycountry():
    for entry in load_activations(REGISTER_PATH, include_examples=True):
        assert pycountry.countries.get(alpha_3=entry["iso3"]) is not None


def test_examples_are_excluded_by_default():
    all_entries = load_activations(REGISTER_PATH, include_examples=True)
    rendered = load_activations(REGISTER_PATH)
    assert all(not e.get("example", False) for e in rendered)
    assert len(rendered) == len([e for e in all_entries if not e.get("example", False)])


def test_valid_entries_pass():
    validate_activation(example_entry())
    validate_activation({**example_entry(), "example": True})
    validate_activation(no_activation_entry())
    validate_activation({**example_entry(), "discrepancies": [discrepancy()]})
    validate_activation({**example_entry(), "discrepancies": [{**discrepancy(), "value": "n/a"}]})
    validate_activation({**example_entry(), "amount_usd": 1_500_000.5})


def test_nullable_fields_accept_null():
    entry = example_entry()
    for field in ("trigger", "forecast_source", "amount_usd", "people_targeted", "sector"):
        entry[field] = None
    entry["wayback_url"] = None
    validate_activation(entry)


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_every_framework_is_accepted(framework):
    validate_activation({**example_entry(), "framework": framework})


@pytest.mark.parametrize("status", STATUSES)
def test_every_status_is_accepted(status):
    entry = example_entry() if status == "activated" else no_activation_entry()
    assert validate_activation({**entry, "status": status})["status"] == status


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda e: e.pop("trigger"), r"missing fields \['trigger'\]"),
        (lambda e: e.update(extra=1), r"unknown fields \['extra'\]"),
        (lambda e: e.update(example="yes"), "'example' must be true or false"),
        (lambda e: e.update(id=""), "'id' must be a non-empty string"),
        (lambda e: e.update(id="Bad Id"), "'id' must use lower case letters"),
        (lambda e: e.update(iso3="gtm"), "'iso3' must be three upper case letters"),
        (lambda e: e.update(iso3="GT"), "'iso3' must be three upper case letters"),
        (lambda e: e.update(iso3=320), "'iso3' must be three upper case letters"),
        (lambda e: e.update(iso3="XXX"), "'iso3' 'XXX' is not an ISO 3166-1 alpha-3 code"),
        (lambda e: e.update(country=""), "'country' must be a non-empty string"),
        (lambda e: e.update(framework="CERF"), "'framework' must be one of"),
        (lambda e: e.update(status="triggered"), "'status' must be one of"),
        (lambda e: e.update(activation_date="2026-03-05"), "must be an ISO calendar date"),
        (lambda e: e.update(activation_date=None), "must be an ISO calendar date"),
        (lambda e: e.update(trigger=""), "'trigger' must be a non-empty string"),
        (lambda e: e.update(forecast_source=""), "'forecast_source' must be a non-empty string"),
        (lambda e: e.update(sector=42), "'sector' must be a non-empty string"),
        (lambda e: e.update(amount_usd="1m"), "'amount_usd' must be a number or null"),
        (lambda e: e.update(amount_usd=True), "'amount_usd' must be a number or null"),
        (lambda e: e.update(amount_usd=-5), "'amount_usd' must not be negative"),
        (lambda e: e.update(people_targeted=12.5), "'people_targeted' must be an integer or null"),
        (lambda e: e.update(source_url="example.org"), "'source_url' must be an http\\(s\\) URL"),
        (lambda e: e.update(wayback_url="https://example.org/x"), "'wayback_url' must start with"),
        (lambda e: e.update(wayback_url=""), "'wayback_url' must be a non-empty string"),
        (lambda e: e.update(retrieved="2026-09-07"), "'retrieved' must be a UTC ISO 8601"),
        (lambda e: e.update(discrepancies=None), "'discrepancies' must be a list"),
        (lambda e: e.update(discrepancies=["text"]), r"discrepancies\[0\]: must be a mapping"),
        (
            lambda e: e.update(discrepancies=[{"statement": "s", "value": 1}]),
            r"discrepancies\[0\]: missing fields \['source_url'\]",
        ),
        (
            lambda e: e.update(discrepancies=[{**discrepancy(), "page": 3}]),
            r"discrepancies\[0\]: unknown fields \['page'\]",
        ),
        (
            lambda e: e.update(discrepancies=[{**discrepancy(), "statement": ""}]),
            r"discrepancies\[0\]: 'statement' must be a non-empty string",
        ),
        (
            lambda e: e.update(discrepancies=[{**discrepancy(), "value": None}]),
            r"discrepancies\[0\]: 'value' must be a number or a non-empty string",
        ),
        (
            lambda e: e.update(discrepancies=[{**discrepancy(), "source_url": "companion.pdf"}]),
            r"discrepancies\[0\]: 'source_url' must be an http\(s\) URL",
        ),
    ],
)
def test_invalid_entries_raise(mutation, message):
    entry = example_entry()
    mutation(entry)
    with pytest.raises(ValueError, match=message):
        validate_activation(entry)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("activation_date", date(2026, 3, 5)),
        ("amount_usd", 0),
        ("people_targeted", 100),
    ],
)
def test_no_activation_entries_carry_no_activation_figures(field, value):
    entry = {**no_activation_entry(), field: value}
    with pytest.raises(ValueError, match=f"'{field}' must be null when 'status' is"):
        validate_activation(entry)


def test_non_mapping_entry_raises():
    with pytest.raises(ValueError, match="entry must be a mapping"):
        validate_activation(["not", "a", "mapping"])


def write_register(path, entries: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump({"activations": entries}, fh, sort_keys=False)


def test_loader_rejects_duplicate_ids(tmp_path):
    register = tmp_path / "activations.yaml"
    write_register(register, [example_entry(), example_entry()])
    with pytest.raises(ValueError, match=r"duplicate ids \['example_gtm_cerf_aa'\]"):
        load_activations(register)


def test_loader_round_trips_dates_and_examples(tmp_path):
    register = tmp_path / "activations.yaml"
    write_register(register, [example_entry(), {**no_activation_entry(), "example": True}])
    rendered = load_activations(register)
    assert [e["id"] for e in rendered] == ["example_gtm_cerf_aa"]
    assert rendered[0]["activation_date"] == date(2026, 3, 5)
    assert len(load_activations(register, include_examples=True)) == 2


def test_loader_rejects_missing_top_level_list(tmp_path):
    register = tmp_path / "activations.yaml"
    register.write_text("entries: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected a top-level 'activations' list"):
        load_activations(register)
