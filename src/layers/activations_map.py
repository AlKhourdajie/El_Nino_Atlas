"""Anticipatory-action activation map for the 2026-27 El Niño.

Provenance
----------
Publisher: UN Central Emergency Response Fund (CERF), run by the UN Office
    for the Coordination of Humanitarian Affairs (OCHA), with World Food
    Programme (WFP) and Food and Agriculture Organization (FAO) documents
    for the frameworks those agencies run.
Dataset: the hand-curated register ``data/curated/activations.yaml``,
    read through ``src.activations``; one entry per country per
    framework, each taken from a document the framework published.
Canonical URL: https://cerf.un.org/ (registry id
    ``ocha_cerf_anticipatory_action``).
Licence: per document, linked from each entry.
Redistribution: conditional; the register holds figures and links only.
Attribution: "Source: UN CERF anticipatory action framework documents".
Cadence: per activation. Latency: as curated.

Three states
------------
This layer reads the three-state rule as ``alert`` for a country with an
entry whose status is ``activated``, ``no_alert`` for a country whose
entries all have status ``framework_no_activation``, and
``not_assessed``, labelled "not tracked", for every other country in
pycountry. A country with any activated entry renders as activated.
Entries flagged ``example`` never render.

Colour never carries a state alone. Every country with an entry also
gets a marker at its centroid in the state's mark style, filled for an
activation and outlined for a framework with no activation, and the
legend pairs each label with the same mark; the hover text and the table
state the status in words.

Placement
---------
Every ISO 3166-1 alpha-3 code in pycountry is passed as a location.
plotly.js matches codes against the topojson the app serves from
``assets/topojson/`` and logs each code without geometry to the browser
console. ``build_figure`` logs how many codes are absent from the
country table embedded in the bundled plotly.js, which Dash serves to
the browser; a code absent from that table is never placed.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from functools import cache
from pathlib import Path

import plotly
import plotly.graph_objects as go
import pycountry
from dash import dcc, html

from src import theme
from src.layout import MAP_CONFIG, TEXT_COLUMN_MIN_WIDTH
from src.layout.explainer import Explainer

logger = logging.getLogger(__name__)

# How this layer maps register statuses onto the three states.
STATE_BY_STATUS: dict[str, str] = {
    "activated": "alert",
    "framework_no_activation": "no_alert",
}
NOT_TRACKED = "not_assessed"
STATE_ORDER: tuple[str, ...] = ("not_assessed", "no_alert", "alert")

STATE_LABELS: dict[str, str] = {
    "alert": "Activated",
    "no_alert": "Framework, no activation",
    "not_assessed": "Not tracked",
}
STATE_DEFINITIONS: dict[str, str] = {
    "alert": "money released on a forecast trigger",
    "no_alert": "a framework exists and has not activated",
    "not_assessed": "no entry in the register",
}

FRAMEWORK_LABELS: dict[str, str] = {
    "cerf_aa": "Central Emergency Response Fund (CERF) anticipatory action",
    "wfp_aa": "World Food Programme (WFP) anticipatory action",
    "ifrc_dref": (
        "International Federation of Red Cross and Red Crescent Societies (IFRC) "
        "Disaster Response Emergency Fund (DREF)"
    ),
    "other": "Other framework",
}

NOT_ASSESSED_TEXT = "not assessed"
NONE_TEXT = "none"
NO_ENTRIES_TEXT = "No entries in the register."
DISCREPANCY_PREFIX = "Companion documents differ. "

PROJECTION = "natural earth"
# plotly.js wraps a horizontal legend into columns as wide as its widest
# item; at this size the widest label takes under half of a 390 px screen,
# so the legend keeps two rows there and one row on wide screens.
LEGEND_FONT_SIZE = 12
# 50 m geometry keeps small island states, which El Niño exposes, on the map.
RESOLUTION = 50
MARKER_SIZE = 9
GRAPH_CONFIG: dict = dict(MAP_CONFIG)

TABLE_HEADERS: tuple[str, ...] = (
    "Country",
    "Framework",
    "Status",
    "Date",
    "Amount (US dollars)",
    "People targeted",
    "Trigger",
    "Source",
    "Archived copy",
    "Notes",
)
# Columns of prose keep ``TEXT_COLUMN_MIN_WIDTH`` inside the table's
# scrolling container, so rows keep a normal height on narrow screens.
PROSE_COLUMNS: frozenset[str] = frozenset({"Trigger", "Notes"})

CERF_ANTICIPATORY_ACTION_URL = "https://cerf.un.org/anticipatory-action"

_PLOTLY_JS = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_ISO3_IN_TABLE = re.compile(r'iso3:"([A-Z]{3})"')


def rendered_entries(entries: list[dict]) -> list[dict]:
    """The entries the layer may show: everything flagged ``example`` is dropped."""
    return [e for e in entries if not e.get("example", False)]


def country_states(entries: list[dict]) -> dict[str, str]:
    """State per ISO-3 code; any activated entry makes the country ``alert``."""
    states: dict[str, str] = {}
    for entry in rendered_entries(entries):
        state = STATE_BY_STATUS[entry["status"]]
        if state == "alert" or entry["iso3"] not in states:
            states[entry["iso3"]] = state
    return states


def format_date(value: date) -> str:
    return f"{value.day} {value:%B %Y}"


def format_figure(value: int | float | str) -> str:
    """A figure as the document gives it: strings as-is, numbers with separators."""
    if isinstance(value, str):
        return value
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


def _figure_or_null(value: int | float | None, entry: dict) -> str:
    if entry["status"] != "activated":
        return NONE_TEXT
    if value is None:
        return NOT_ASSESSED_TEXT
    return format_figure(value)


def entry_date(entry: dict) -> str:
    if entry["status"] != "activated":
        return NONE_TEXT
    return format_date(entry["activation_date"])


def entry_amount(entry: dict) -> str:
    return _figure_or_null(entry["amount_usd"], entry)


def entry_people(entry: dict) -> str:
    return _figure_or_null(entry["people_targeted"], entry)


def hover_text(name: str, entries: list[dict]) -> str:
    """Hover copy for one country: framework, status, date, amount and people per entry."""
    if not entries:
        return f"<b>{name}</b><br>{STATE_LABELS[NOT_TRACKED]}: {STATE_DEFINITIONS[NOT_TRACKED]}"
    blocks = []
    for entry in entries:
        state = STATE_BY_STATUS[entry["status"]]
        blocks.append(
            "<br>".join(
                [
                    FRAMEWORK_LABELS[entry["framework"]],
                    f"Status: {STATE_LABELS[state]}",
                    f"Date: {entry_date(entry)}",
                    f"Amount (US dollars): {entry_amount(entry)}",
                    f"People targeted: {entry_people(entry)}",
                ]
            )
        )
    return f"<b>{name}</b><br>" + "<br><br>".join(blocks)


@cache
def plotly_country_codes() -> frozenset[str]:
    """ISO-3 codes in the country table embedded in the bundled plotly.js.

    Dash serves this bundle to the browser. A code missing here is never
    placed; a code present can still lack geometry at the chosen
    resolution, which plotly.js reports in the browser console.
    """
    if not _PLOTLY_JS.is_file():
        raise RuntimeError(f"bundled plotly.js not found at {_PLOTLY_JS}")
    codes = frozenset(_ISO3_IN_TABLE.findall(_PLOTLY_JS.read_text(encoding="utf-8")))
    if not codes:
        raise RuntimeError(f"no country table found in {_PLOTLY_JS}")
    return codes


def state_colourscale() -> list[list]:
    """A stepped colourscale: one flat band per state in ``STATE_ORDER``."""
    n = len(STATE_ORDER)
    scale: list[list] = []
    for i, state in enumerate(STATE_ORDER):
        colour = theme.STATE_COLOURS[state]
        scale.append([i / n, colour])
        scale.append([(i + 1) / n, colour])
    return scale


def _country_name(country) -> str:
    return getattr(country, "common_name", None) or country.name


def _marker(state: str) -> dict:
    """The centroid marker for ``state``: filled for alert, outlined for no alert."""
    colour = theme.STATE_COLOURS[state]
    marker = {
        "size": MARKER_SIZE,
        "symbol": theme.STATE_MARKER_SYMBOLS[state],
        "color": colour,
        "line": {"color": theme.MAP_BORDER, "width": 1.5},
    }
    if theme.STATE_MARKS[state] == "outlined":
        marker["line"] = {"color": colour, "width": 2}
        marker["color"] = theme.MAP_BORDER
    return marker


def build_figure(entries: list[dict]) -> go.Figure:
    """Choropleth of every pycountry code in one of the three states.

    Countries with an entry also carry a centroid marker in the state's
    mark style; the three legend traces pair each label with that mark.
    """
    entries = rendered_entries(entries)
    states = country_states(entries)
    by_iso3: dict[str, list[dict]] = {}
    for entry in entries:
        by_iso3.setdefault(entry["iso3"], []).append(entry)

    countries = sorted(pycountry.countries, key=lambda c: c.alpha_3)
    codes = [c.alpha_3 for c in countries]
    z = [STATE_ORDER.index(states.get(code, NOT_TRACKED)) for code in codes]
    text = [hover_text(_country_name(c), by_iso3.get(c.alpha_3, [])) for c in countries]

    missing = sorted(set(codes) - plotly_country_codes())
    logger.info(
        "%d of %d ISO-3 codes are absent from the country table in the bundled plotly.js "
        "and cannot be placed%s",
        len(missing),
        len(codes),
        f": {', '.join(missing)}" if missing else "",
    )

    fig = go.Figure()
    fig.add_trace(
        go.Choropleth(
            name="Activations",
            locations=codes,
            locationmode="ISO-3",
            z=z,
            zmin=0,
            zmax=len(STATE_ORDER) - 1,
            colorscale=state_colourscale(),
            showscale=False,
            showlegend=False,
            text=text,
            hovertemplate="%{text}<extra></extra>",
            marker={"line": {"color": theme.MAP_BORDER, "width": 0.4}},
            meta={"role": "choropleth"},
        )
    )
    # One trace per state: its legend entry, and the centroid markers of
    # the countries in that state. Short legend labels keep the horizontal
    # legend beneath the map on a narrow screen; the definitions stay in
    # the hover text and the explainer. The not-tracked trace places no
    # marker, because its state is the absence of an entry.
    for state in reversed(STATE_ORDER):
        located = sorted(code for code, s in states.items() if s == state)
        fig.add_trace(
            go.Scattergeo(
                name=STATE_LABELS[state],
                locations=located or None,
                locationmode="ISO-3",
                lon=None if located else [None],
                lat=None if located else [None],
                mode="markers",
                marker=_marker(state),
                hoverinfo="skip",
                showlegend=True,
                meta={"role": "state", "state": state},
            )
        )
    fig.update_geos(
        projection_type=PROJECTION,
        resolution=RESOLUTION,
        showframe=False,
        showcoastlines=False,
        showcountries=False,
        showland=True,
        landcolor=theme.STATE_COLOURS[NOT_TRACKED],
        showocean=False,
        showlakes=False,
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        dragmode=False,
        height=theme.MAP_HEIGHT,
        uirevision=theme.UI_REVISION,
        margin={"l": 0, "r": 0, "t": 8, "b": 8},
        legend={
            "orientation": "h",
            "x": 0,
            "xanchor": "left",
            "y": 0,
            "yanchor": "top",
            "font": {"size": LEGEND_FONT_SIZE},
            "itemclick": False,
            "itemdoubleclick": False,
        },
    )
    return fig


def discrepancy_note(entry: dict) -> list:
    """Dash children describing figures that companion documents state differently."""
    items = entry["discrepancies"]
    if not items:
        return []
    children: list = [DISCREPANCY_PREFIX]
    for i, item in enumerate(items):
        if i:
            children.append(" ")
        children.append(f"{item['statement']}: {format_figure(item['value'])} (")
        children.append(html.A("source", href=item["source_url"], target="_blank"))
        children.append(").")
    return children


def has_discrepancies(entries: list[dict]) -> bool:
    """Whether any rendered entry carries a discrepancy record."""
    return any(entry["discrepancies"] for entry in rendered_entries(entries))


def _link(label: str, url: str | None) -> object:
    if url is None:
        return NONE_TEXT
    return html.A(label, href=url, target="_blank")


def _cell(column: str, children, cell=html.Td):
    """A table cell; prose columns carry the minimum width."""
    if column in PROSE_COLUMNS:
        return cell(children, style={"minWidth": TEXT_COLUMN_MIN_WIDTH})
    return cell(children)


def table_row(entry: dict) -> html.Tr:
    state = STATE_BY_STATUS[entry["status"]]
    trigger = entry["trigger"] if entry["trigger"] is not None else NOT_ASSESSED_TEXT
    values = [
        entry["country"],
        FRAMEWORK_LABELS[entry["framework"]],
        STATE_LABELS[state],
        entry_date(entry),
        entry_amount(entry),
        entry_people(entry),
        trigger,
        _link("document", entry["source_url"]),
        _link("archived", entry["wayback_url"]),
        discrepancy_note(entry),
    ]
    cells = [_cell(column, value) for column, value in zip(TABLE_HEADERS, values, strict=True)]
    return html.Tr(cells, id=f"activation-{entry['id']}")


def build_table(entries: list[dict]) -> html.Div:
    """Every rendered entry with its source and archived links and any discrepancy note.

    The table sits in a scrolling wrapper so that its ten columns never
    widen the page.
    """
    entries = rendered_entries(entries)
    if entries:
        rows = [table_row(e) for e in entries]
    else:
        rows = [html.Tr(html.Td(NO_ENTRIES_TEXT, colSpan=len(TABLE_HEADERS)))]
    table = html.Table(
        [
            html.Thead(html.Tr([_cell(h, h, html.Th) for h in TABLE_HEADERS])),
            html.Tbody(rows),
        ],
        className="table",
        id="activations-table",
    )
    return html.Div(table, className="table-wrap", id="activations-table-wrap")


def build_panel(entries: list[dict]) -> html.Div:
    """The map with the entry table beneath it."""
    return html.Div(
        [
            dcc.Graph(figure=build_figure(entries), config=GRAPH_CONFIG, id="activations-map"),
            build_table(entries),
        ]
    )


def explainer() -> Explainer:
    return Explainer(
        title="Anticipatory-action activations",
        what=(
            "Where an anticipatory-action framework released money on a forecast trigger "
            "linked to the 2026-27 El Niño. Each country shows one of three states: "
            "activated, framework with no activation, or not tracked, which means the "
            "register holds no entry for it. A country with any activation shows as "
            "activated. Where companion documents give different figures, both are shown "
            "as they stand."
        ),
        how=(
            f"In the words of [its own page]({CERF_ANTICIPATORY_ACTION_URL}), the Central "
            'Emergency Response Fund (CERF) "provides funding for OCHA-facilitated '
            'anticipatory action pilots", where OCHA is the UN Office for the '
            "Coordination of Humanitarian Affairs. The pilots act on a predicted shock "
            "through anticipatory actions identified in advance, on a trigger agreed "
            "before the season. Each entry on this map is read from a document the "
            "framework published and quotes its figures with the page or paragraph they "
            "come from."
        ),
        why=(
            "Because El Niño is forecast months before the rainfall it disturbs arrives or "
            "fails, anticipatory-action frameworks can release money before the hazard, on "
            "a forecast trigger agreed in advance. The map records where that happened "
            "during this event and where a framework existed without activating. Both "
            "outcomes are recorded, and activations are shown in the same way whether the "
            "forecast hazard later arrived or failed to."
        ),
        not_shown=(
            "An activation records money released on a forecast trigger. Whether the "
            "hazard occurred, whether the forecast verified, how the money was spent and "
            "what happened to the people targeted lie outside this panel. A country shown "
            "as not tracked has no entry in the register, and a framework or a hazard may "
            "still exist there. Amounts are as the source document states them, and where "
            "companion documents differ the table lists both figures."
        ),
        source_name=(
            "UN Office for the Coordination of Humanitarian Affairs (OCHA), World Food "
            "Programme (WFP) and Food and Agriculture Organization (FAO) documents"
        ),
        source_url="https://cerf.un.org/",
        licence_label="per document, linked",
    )
