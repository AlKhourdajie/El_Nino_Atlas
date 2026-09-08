"""Layout builders for the El Niño Atlas page.

``app.py`` assembles the page from these builders along the forecast,
action, impact spine. The page is a skip link, a slim sticky navigation
bar, the hero (title, opening line, reading line, scope line), the main
column and the footer, which names the maintainer. Each panel is one card
with a fixed header grammar: the stage as an overline, the title, one
sentence on what the panel shows, the source line with its licence
badge and retrieval stamp, a "Source and method" disclosure holding the
metric definition in the source's own words, and a discrepancy note
where the register carries one. The figure follows, then the rest of
the explainer. A panel whose snapshot is missing keeps its explainer
and shows a visible notice in place of the figure; a panel whose data
failed to load shows an error banner naming the source and the error.
The page copy lives here; the copy rules are in CLAUDE.md. Class names
map to ``assets/atlas.css``; the colour and type tokens come from
``assets/tokens.css``, generated from ``design/tokens.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import plotly.graph_objects as go
from dash import dcc, html

from src import theme
from src.enso_events import Event
from src.layout.explainer import (
    Explainer,
    explainer_body,
    explainer_header,
    lede,
    source_line,
)

TITLE = "El Niño Atlas"

OPENING = (
    "An El Niño is under way in the tropical Pacific and is forecast to become very strong "
    "by late 2026, on top of the warmest global background on record. This atlas follows "
    "what was forecast, what was done in anticipation, and what has happened."
)

# The first two sentences of the README section "Why an event-resolved atlas",
# verbatim; tests/test_layout.py checks them against README.md.
ABOUT: tuple[str, ...] = (
    "Hazard catalogues, forecast dashboards and response dashboards each cover one stage "
    "of an event and keep their records apart.",
    "The atlas takes the 2026-27 El Niño as its unit and organises the three records "
    "around it, so that every entry is tied to this event with a stated basis and the "
    "stages sit on one page.",
)

# One sentence on what the atlas is, from the README, shown beneath the
# reading line; tests/test_layout.py checks it against README.md.
SCOPE = "The atlas is a research tool in development."

UNAVAILABLE_NOTICE = "Data snapshot not yet available"
ERROR_PREFIX = "Data load failed"

# The footer links. The ORCID identifier and the repository are the ones in
# CITATION.cff; tests/test_layout.py checks them against it.
MAINTAINER = "Alaa Al Khourdajie"
MAINTAINER_URL = "https://sites.google.com/site/akhourdajie/"
ORCID = "0000-0003-1376-7529"
ORCID_URL = f"https://orcid.org/{ORCID}"
REPOSITORY_URL = "https://github.com/AlKhourdajie/El_Nino_Atlas"
ISSUES_URL = f"{REPOSITORY_URL}/issues"
CONCEPT_DOI = "10.5281/zenodo.22644790"
CITATION_URL = f"https://doi.org/{CONCEPT_DOI}"

# The navigation anchors, in page order.
NAV_ITEMS: tuple[tuple[str, str], ...] = (
    ("Forecast", "#panel-index"),
    ("Realised impacts", "#panel-commodities"),
    ("Anticipatory action", "#panel-activations"),
    ("Sources and methods", "#sources"),
    ("Cite", "#cite"),
)
SOURCES_TITLE = "Sources and methods"

# Interaction copy: control labels, not claims.
TIME_RANGE_LABEL = "Time range"
EVENT_SELECT_LABEL = "ENSO event"
EVENT_SELECT_PLACEHOLDER = "Choose an event"
BANDS_LABEL = "Phase bands"
DOWNLOAD_LABELS: dict[str, str] = {"csv": "CSV", "png": "PNG", "svg": "SVG"}
DOWNLOAD_GROUP_LABEL = "Download"
COPY_CITATION_LABEL = "Copy citation"
REPORT_LABEL = "Report a discrepancy"
THEME_TOGGLE_LABEL = "Colour scheme"
SKIP_LINK_LABEL = "Skip to content"

PHASE_NAMES: dict[str, str] = {"el_nino": "El Niño", "la_nina": "La Niña"}

# Figures resize with their column. The mode bar keeps zoom, pan and
# reset only; downloads have their own buttons. Scroll zoom stays off so
# the page scrolls past a figure instead of into it.
GRAPH_CONFIG: dict = {
    "responsive": True,
    "displayModeBar": True,
    "displaylogo": False,
    # plotly.js 4 shows a "Share chart" button by default; it would send
    # the figure to Plotly's cloud, so it stays off.
    "showSendToCloud": False,
    "scrollZoom": False,
    "doubleClick": "reset",
    "modeBarButtonsToRemove": [
        "select2d",
        "lasso2d",
        "zoomIn2d",
        "zoomOut2d",
        "autoScale2d",
        "toggleSpikelines",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "toImage",
        "sendChartToCloud",
        "sendDataToCloud",
    ],
}
# The map is a static natural-earth view; it needs no mode bar.
MAP_CONFIG: dict = {
    "responsive": True,
    "displayModeBar": False,
    "showSendToCloud": False,
    "scrollZoom": False,
}

# Every graph container takes the height the figures are authored at.
# Dash otherwise gives the container the height of its column.
FIGURE_HEIGHT: int = theme.RESPONSIVE_LAYOUT["height"]

# A table column of prose keeps at least this width inside the table's
# scrolling container, so its rows keep a normal height on narrow screens.
TEXT_COLUMN_MIN_WIDTH = "20rem"

# Panel keys: the two time-series panels share theirs with the URL grammar
# in ``src.layout.viewstate``; every control and download id carries one.
GRAPH_IDS: dict[str, str] = {
    "index": "graph-index",
    "prices": "graph-commodities",
    "activations": "activations-map",
}


@dataclass(frozen=True)
class BuildInfo:
    """The commit and time the running page was built from."""

    sha: str
    built_at: str

    @property
    def short(self) -> str:
        return self.sha[:7]


@dataclass(frozen=True)
class SourceEntry:
    """One line of the sources section: a panel and its source."""

    panel_id: str
    explainer: Explainer
    retrieved_at: str | None = None


def map_config(topojson_url: str) -> dict:
    """The map configuration with the topojson served from ``topojson_url``."""
    return {**MAP_CONFIG, "topojsonURL": topojson_url}


def skip_link() -> html.A:
    return html.A(SKIP_LINK_LABEL, href="#main", className="skip-link", id="skip-link")


def theme_toggle() -> html.Button:
    """The scheme toggle: the visible label names the scheme the click switches to.

    The stylesheet shows one of the two spans per scheme, so the button's
    accessible name is its visible text.
    """
    return html.Button(
        [
            html.Span("Dark", className="when-light"),
            html.Span("Light", className="when-dark"),
        ],
        id="theme-toggle",
        className="btn btn--ghost site-nav__toggle",
        type="button",
        title=THEME_TOGGLE_LABEL,
    )


def nav() -> html.Nav:
    """The slim sticky navigation with anchors in page order."""
    items = [
        html.Li(html.A(label, href=href, className="site-nav__link")) for label, href in NAV_ITEMS
    ]
    return html.Nav(
        html.Div(
            [
                html.A(TITLE, href="#header", className="site-nav__brand"),
                html.Ul(items, className="site-nav__list"),
                theme_toggle(),
            ],
            className="site-nav__inner",
        ),
        id="site-nav",
        className="site-nav",
        **{"aria-label": "Sections"},
    )


def section(title: str, *children, id: str | None = None) -> html.Section:
    """A titled page section."""
    kwargs = {"id": id} if id else {}
    return html.Section(
        [html.H2(title, className="section__title"), *children], className="section", **kwargs
    )


def opening(reading: str | None = None) -> html.Header:
    """The hero: title, opening line, reading line, scope line.

    ``reading`` is the one-line summary of the latest season that
    ``src.layers.enso_index.latest_reading`` builds. It is ``None`` when
    no index snapshot exists, and the line is then omitted. The
    maintainer is named in the footer only.
    """
    children: list = [
        html.H1(TITLE, className="hero__title"),
        html.P(OPENING, className="hero__lead", id="opening"),
    ]
    if reading is not None:
        children.append(html.P(reading, id="latest-reading", className="hero__reading"))
    children.append(html.P(SCOPE, id="scope", className="hero__scope"))
    return html.Header(children, id="header", className="hero")


def about() -> html.Section:
    """Two sentences on the event-resolved logic of the atlas, shared with the README."""
    return section("About", html.P(" ".join(ABOUT), className="prose"), id="about")


def _shift_months(day: date, months: int) -> date:
    year, month_index = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, month_index + 1, 1)


def event_label(event: Event) -> str:
    """'El Niño, MAM 1997 to MAM 1998', with 'provisional' appended for a provisional run."""
    label = f"{PHASE_NAMES[event.phase]}, {event.seasons[0]} to {event.seasons[-1]}"
    if event.provisional:
        label += ", provisional"
    return label


def event_window(event: Event, until: date, context_months: int = 12) -> tuple[str, str]:
    """ISO bounds of the view that shows ``event`` with a year of context either side.

    The window starts one month before the onset season's centre month
    (the season's first month) less the context, and ends two months
    after the last season's centre month plus the context. An event with
    no end runs to ``until``.
    """
    start = _shift_months(event.onset, -1 - context_months)
    end = until if event.end is None else _shift_months(event.end, 2)
    end = _shift_months(end, context_months)
    return start.isoformat(), end.isoformat()


def event_options(
    events: list[Event], until: date, not_before: date | None = None
) -> list[dict[str, str]]:
    """The select options for the ENSO events in the data, in date order.

    ``not_before`` drops events that ended before a panel's record starts,
    so a panel never offers a window with nothing in it.
    """
    options = []
    for event in events:
        if not_before is not None and event.end is not None and event.end < not_before:
            continue
        start, end = event_window(event, until)
        options.append({"label": event_label(event), "value": f"{start},{end}"})
    return options


def range_buttons(first_year: int) -> tuple[dict, ...]:
    """The three range presets for a record starting in ``first_year``.

    The same shape as ``src.layers.enso_index.RANGE_BUTTONS``: the whole
    record, the last 30 years and the last 5 years.
    """
    return (
        {"label": f"From {first_year}", "step": "all"},
        {"label": "30 years", "count": 30, "step": "year", "stepmode": "backward"},
        {"label": "5 years", "count": 5, "step": "year", "stepmode": "backward"},
    )


def range_toolbar(key: str, buttons: tuple[dict, ...], events: list[dict[str, str]]) -> html.Div:
    """One panel's time-range controls: the record presets, the event select, the band toggle.

    ``key`` is the panel's URL key (``index`` or ``prices``) and suffixes
    every id: ``range-all-<key>``, ``range-30-<key>``, ``range-5-<key>``,
    ``event-select-<key>`` and ``bands-toggle-<key>``. ``buttons`` are the
    three preset records and ``events`` are ``event_options``. The native
    select reports through ``assets/atlas.js``, which writes its value to
    the store ``event-select-store-<key>``; the band toggle is a button
    whose ``aria-pressed`` attribute is ``"true"`` while the bands show.
    """
    ids = (f"range-all-{key}", f"range-30-{key}", f"range-5-{key}")
    presets = [
        html.Button(button["label"], id=button_id, className="btn", type="button")
        for button, button_id in zip(buttons, ids, strict=True)
    ]
    select = html.Select(
        [html.Option(EVENT_SELECT_PLACEHOLDER, value="")]
        + [html.Option(option["label"], value=option["value"]) for option in events],
        id=f"event-select-{key}",
        className="select",
    )
    return html.Div(
        [
            html.Span(TIME_RANGE_LABEL, className="card__toolbar-label"),
            html.Div(presets, className="controls__group", role="group"),
            html.Label(
                [html.Span(EVENT_SELECT_LABEL, className="visually-hidden"), select],
                className="controls__select",
            ),
            html.Button(
                [html.Span(className="check", **{"aria-hidden": "true"}), BANDS_LABEL],
                id=f"bands-toggle-{key}",
                className="btn btn--ghost controls__check",
                type="button",
                **{"aria-pressed": "true"},
            ),
        ],
        id=f"time-controls-{key}",
        className="card__toolbar card__toolbar--range",
        role="group",
        **{"aria-label": TIME_RANGE_LABEL},
    )


def toolbars(*rows) -> html.Div:
    """The toolbar rows of a card, in order."""
    return html.Div(list(rows), className="card__toolbars")


def graph(
    figure: go.Figure,
    *,
    id: str | None = None,
    height: int | None = FIGURE_HEIGHT,
    config: dict | None = None,
) -> dcc.Graph:
    """A panel figure in a container of fixed height.

    ``height`` is in pixels and defaults to ``FIGURE_HEIGHT``; ``None``
    leaves the container's height to Dash. ``config`` defaults to
    ``GRAPH_CONFIG``.
    """
    kwargs: dict = {"id": id} if id else {}
    if height is not None:
        kwargs["style"] = {"height": f"{height}px"}
    return dcc.Graph(figure=figure, config=config or GRAPH_CONFIG, **kwargs)


def figure_block(content, caption: str, *, id: str) -> html.Figure:
    """The figure with one screen-reader sentence, taken from its caption."""
    return html.Figure(
        [content, html.Figcaption(caption, className="visually-hidden", id=f"{id}-caption")],
        className="card__figure",
        id=f"{id}-figure",
        **{"aria-describedby": f"{id}-caption"},
    )


def download_toolbar(key: str, *, csv: bool = True, image: bool = True) -> html.Div:
    """The per-panel download buttons: CSV of the plotted data, PNG and SVG of the figure."""
    buttons: list = []
    if csv:
        buttons.append(
            html.Button(DOWNLOAD_LABELS["csv"], id=f"csv-{key}", className="btn", type="button")
        )
    if image:
        for fmt in ("png", "svg"):
            buttons.append(
                html.Button(DOWNLOAD_LABELS[fmt], id=f"{fmt}-{key}", className="btn", type="button")
            )
    return html.Div(
        [
            html.Span(DOWNLOAD_GROUP_LABEL, className="card__toolbar-label"),
            *buttons,
            html.Span(
                id=f"export-sink-{key}", className="visually-hidden", **{"aria-live": "polite"}
            ),
        ],
        className="card__toolbar",
        role="group",
        **{"aria-label": DOWNLOAD_GROUP_LABEL},
    )


def error_banner(source: str, error: str) -> html.Div:
    """A visible banner naming the source and the error of a failed data load."""
    return html.Div(
        [html.Strong(f"{ERROR_PREFIX}: "), html.Span(source), ". ", html.Code(error)],
        className="banner banner--error",
        role="alert",
    )


def unavailable_notice() -> html.P:
    """The notice a panel shows in place of its figure when its snapshot is missing."""
    return html.P(UNAVAILABLE_NOTICE, className="notice", role="status")


def card(
    stage: str | None,
    explainer: Explainer,
    content,
    *,
    id: str,
    retrieved_at: str | None = None,
    toolbar: html.Div | None = None,
    note=None,
    beneath: tuple = (),
) -> html.Section:
    """One panel as a card: header, toolbar, content, explainer body, then ``beneath``.

    ``content`` is the figure block, the notice or the error banner.
    ``note`` is placed under the disclosure, for the discrepancy note.
    ``beneath`` components follow the body at the card's full width.
    """
    header: list = []
    if stage:
        header.append(html.P(stage, className="card__stage"))
    header.append(html.H2(explainer.title, className="card__title", id=f"{id}-title"))
    header.extend(explainer_header(explainer, retrieved_at))
    if note is not None:
        header.append(note)
    children: list = [html.Header(header, className="card__header")]
    if toolbar is not None:
        children.append(toolbar)
    children.append(content)
    children.append(explainer_body(explainer))
    children.extend(beneath)
    return html.Section(children, id=id, className="card", **{"aria-labelledby": f"{id}-title"})


def panel(
    stage: str,
    explainer: Explainer,
    figure: go.Figure,
    retrieved_at: str,
    *,
    id: str,
    graph_id: str | None = None,
    toolbar: html.Div | None = None,
) -> html.Section:
    """One panel: the card with the figure in the figure block."""
    content = figure_block(graph(figure, id=graph_id), lede(explainer), id=id)
    return card(stage, explainer, content, id=id, retrieved_at=retrieved_at, toolbar=toolbar)


def composite_panel(
    stage: str | None,
    explainer: Explainer,
    column,
    *,
    id: str,
    retrieved_at: str | None = None,
    toolbar: html.Div | None = None,
    note=None,
    beneath: tuple = (),
) -> html.Section:
    """A panel whose content is ``column``, the components the caller assembled.

    The activation panel stacks the three-state legend and the map there
    and passes its entry table as ``beneath``. ``retrieved_at`` is omitted
    when the content is not a snapshot.
    """
    content = figure_block(column, lede(explainer), id=id)
    return card(
        stage,
        explainer,
        content,
        id=id,
        retrieved_at=retrieved_at,
        toolbar=toolbar,
        note=note,
        beneath=beneath,
    )


def unavailable_panel(stage: str, explainer: Explainer, *, id: str) -> html.Section:
    """A panel whose snapshot is missing: the notice in place of the figure."""
    return card(stage, explainer, unavailable_notice(), id=id)


def error_panel(
    stage: str | None, explainer: Explainer, *, id: str, source: str, error: str
) -> html.Section:
    """A panel whose data failed to load: the banner in place of the figure."""
    return card(stage, explainer, error_banner(source, error), id=id)


def container(id: str) -> html.Div:
    """An empty container another layer fills."""
    return html.Div(id=id)


def legend_item(state: str) -> html.Div:
    """One legend entry: the swatch in the state's mark style, then its label."""
    mark = theme.STATE_MARKS[state]
    return html.Div(
        [
            html.Span(
                className=f"legend__swatch legend__swatch--{mark}",
                **{"aria-hidden": "true", "data-state": state},
            ),
            html.Span(theme.STATE_LABELS[state]),
        ],
        className="legend__item",
        id=f"legend-{state}",
        role="listitem",
    )


def legend() -> html.Div:
    """The three-state legend used by every layer."""
    return html.Div(
        [legend_item(s) for s in ("alert", "no_alert", "not_assessed")],
        id="legend",
        className="legend",
        role="list",
    )


def sources_section(entries: list[SourceEntry]) -> html.Section:
    """The sources and methods list: each panel's source line, linked to its card."""
    items = []
    for entry in entries:
        items.append(
            html.Li(
                [
                    html.A(entry.explainer.title, href=f"#{entry.panel_id}"),
                    source_line(entry.explainer, entry.retrieved_at),
                ]
            )
        )
    return section(SOURCES_TITLE, html.Ul(items, className="sources__list"), id="sources")


def citation_text(cff: dict) -> str:
    """A one-line citation from the fields of CITATION.cff."""
    (author,) = cff["authors"]
    initials = " ".join(f"{part[0]}." for part in author["given-names"].split())
    year = str(cff["date-released"])[:4]
    return (
        f"{author['family-names']}, {initials} ({year}). {cff['title']} "
        f"(version {cff['version']}). https://doi.org/{cff['doi']}"
    )


def footer(build: BuildInfo | None = None) -> html.Footer:
    """The cite block, the maintainer, licence and cite lines, the report link, the build."""
    cite = html.Div(
        [
            html.A(
                [
                    html.Span("DOI", className="doi-badge__label"),
                    html.Span(CONCEPT_DOI, className="doi-badge__value"),
                ],
                href=CITATION_URL,
                className="doi-badge",
            ),
            html.Button(COPY_CITATION_LABEL, id="copy-citation", className="btn", type="button"),
            html.Span(id="copy-status", className="footer__status", **{"aria-live": "polite"}),
        ],
        id="cite",
        className="footer__cite",
    )
    maintainer = html.P(
        [
            "El Niño Atlas is maintained by ",
            html.A(MAINTAINER, href=MAINTAINER_URL),
            ". ORCID: ",
            html.A(ORCID_URL, href=ORCID_URL),
        ],
        className="footer__line",
    )
    licence = html.P(
        [
            "Code: MIT licence, on ",
            html.A("GitHub", href=REPOSITORY_URL),
            ". Data: licence stated with each panel.",
        ],
        className="footer__line",
    )
    cite_line = html.P(
        ["Cite: ", html.A(CITATION_URL, href=CITATION_URL)], className="footer__line"
    )
    report = html.P(html.A(REPORT_LABEL, href=ISSUES_URL), className="footer__line footer__report")
    children: list = [cite, maintainer, licence, cite_line, report]
    if build is not None:
        children.append(
            html.P(
                [
                    "Build ",
                    html.Code(build.short, title=build.sha),
                    f", {build.built_at}",
                ],
                id="build-info",
                className="footer__line footer__build",
            )
        )
    return html.Footer(children, id="footer", className="footer")


def page(*children, main: tuple = ()) -> html.Div:
    """The served page: ``children`` before the main column, ``main`` inside it.

    ``children`` hold the stores, the skip link, the navigation and the
    hero; ``main`` holds the sections and cards. The footer follows.
    """
    return html.Div(
        [*children, html.Main(list(main), id="main", className="main", tabIndex="-1")],
        className="atlas-page",
        id="atlas-page",
    )
