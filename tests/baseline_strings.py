"""The inventory of public strings that the design pass must leave byte-identical.

``baseline_strings`` maps a stable key to each caption, legend, hero
and footer string the page shows, read from the modules that own them.
``tests/test_baseline_strings.py`` hashes the inventory and compares it
with the record written before the design pass; the same inventory
wrote that record, so any drift in a string fails the test and names
the key.

The generated reading line is included as the line the committed index
snapshot yields, so a change in the snapshot changes that one hash and
nothing else.
"""

from __future__ import annotations

import hashlib

from src import theme
from src.layers import activations_map, commodities, enso_index, teleconnections
from src.layout import captions
from src.layout import explainer as explainer_module

HASH_LINE = "{digest}  {key}\n"


def _explainer_strings(prefix: str, panel) -> dict[str, str]:
    record = panel.explainer()
    strings = {
        f"{prefix}.title": record.title,
        f"{prefix}.what": record.what,
        f"{prefix}.how": record.how,
        f"{prefix}.why": record.why,
        f"{prefix}.not_shown": record.not_shown,
        f"{prefix}.source_name": record.source_name,
        f"{prefix}.licence_label": record.licence_label,
    }
    for index, caption in enumerate(record.captions):
        strings[f"{prefix}.caption.{index}"] = caption
    return strings


def baseline_strings(reading: str | None = None) -> dict[str, str]:
    """Every string in the inventory, keyed for the hash record.

    ``reading`` is the generated latest-reading line; it is recorded
    under ``hero.reading`` when given.
    """
    # Imported here so that the inventory follows the current layout
    # module whatever it is called after the pass.
    from src import layout

    strings: dict[str, str] = {
        "hero.title": layout.TITLE,
        "hero.opening": layout.OPENING,
        "hero.maintainer": "Maintained by Alaa Al Khourdajie, Imperial College London.",
        "about.0": layout.ABOUT[0],
        "about.1": layout.ABOUT[1],
        "notice.unavailable": layout.UNAVAILABLE_NOTICE,
        "footer.maintainer": (
            "El Niño Atlas is maintained by Alaa Al Khourdajie, Imperial College London. "
            "ORCID: https://orcid.org/0000-0003-1376-7529"
        ),
        "footer.licence": "Code: MIT licence, on GitHub. Data: licence stated with each panel.",
        "footer.cite": "Cite: https://doi.org/10.5281/zenodo.22644790",
        "caption.growth": captions.GROWTH,
        "caption.price_transmission": captions.PRICE_TRANSMISSION,
        "caption.temperature_contribution": captions.TEMPERATURE_CONTRIBUTION,
        "caption.rebase": commodities.REBASE_CAPTION,
        "legend.phase.el_nino": theme.PHASE_LABELS["el_nino"],
        "legend.phase.la_nina": theme.PHASE_LABELS["la_nina"],
        "legend.state.alert": theme.STATE_LABELS["alert"],
        "legend.state.no_alert": theme.STATE_LABELS["no_alert"],
        "legend.state.not_assessed": theme.STATE_LABELS["not_assessed"],
        "legend.map.alert": activations_map.STATE_LABELS["alert"],
        "legend.map.no_alert": activations_map.STATE_LABELS["no_alert"],
        "legend.map.not_assessed": activations_map.STATE_LABELS["not_assessed"],
        "legend.map.definition.alert": activations_map.STATE_DEFINITIONS["alert"],
        "legend.map.definition.no_alert": activations_map.STATE_DEFINITIONS["no_alert"],
        "legend.map.definition.not_assessed": activations_map.STATE_DEFINITIONS["not_assessed"],
        "legend.map.no_entries": activations_map.NO_ENTRIES_TEXT,
        "legend.map.not_assessed_text": activations_map.NOT_ASSESSED_TEXT,
        "legend.map.none_text": activations_map.NONE_TEXT,
        "legend.map.discrepancy_prefix": "Companion documents differ. ",
        "legend.index.provisional": "provisional",
        "legend.index.threshold": "±0.5 °C",
        "axis.index.y": "Anomaly (°C)",
        "axis.commodities.y": "Index (January 2010 = 100)",
        "explainer.block.what": explainer_module.BLOCKS[0][1],
        "explainer.block.how": explainer_module.BLOCKS[1][1],
        "explainer.block.why": explainer_module.BLOCKS[2][1],
        "explainer.block.not_shown": explainer_module.BLOCKS[3][1],
        "reading.prefix": enso_index.READING_PREFIX,
        "reading.not_assessed": enso_index.NOT_ASSESSED_TEXT,
        "teleconnections.panel_title": teleconnections.PANEL_TITLE,
        "teleconnections.figure_title": teleconnections.TITLE,
        "teleconnections.legend_title": teleconnections.LEGEND_TITLE,
        "teleconnections.image_alt": teleconnections.IMAGE_ALT,
        "teleconnections.source_link_label": teleconnections.SOURCE_LINK_LABEL,
    }
    for signal, label in teleconnections.SIGNAL_LABELS.items():
        strings[f"teleconnections.signal.{signal}"] = label
    for index, header in enumerate(activations_map.TABLE_HEADERS):
        strings[f"table.header.{index}"] = header
    for framework, label in activations_map.FRAMEWORK_LABELS.items():
        strings[f"table.framework.{framework}"] = label
    for index, button in enumerate(enso_index.RANGE_BUTTONS):
        strings[f"range.button.{index}"] = button["label"]
    for series_id, label in commodities.DEFAULT_SERIES:
        strings[f"series.{series_id}"] = label
    strings.update(_explainer_strings("panel.index", enso_index))
    strings.update(_explainer_strings("panel.commodities", commodities))
    strings.update(_explainer_strings("panel.activations", activations_map))
    strings.update(_explainer_strings("panel.teleconnections", teleconnections))
    if reading is not None:
        strings["hero.reading"] = reading
    return strings


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_record(strings: dict[str, str]) -> str:
    """The record text: one ``<sha256>  <key>`` line per string, keys sorted."""
    return "".join(
        HASH_LINE.format(digest=digest(strings[key]), key=key) for key in sorted(strings)
    )


def parse_record(text: str) -> dict[str, str]:
    """``hash_record`` read back: key to digest."""
    record: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        digest_hex, key = line.split("  ", 1)
        record[key] = digest_hex
    return record
