"""The explainer every panel shows beside its figure.

A panel module exposes ``build_figure(...)`` and ``explainer() ->
Explainer``. ``render_explainer`` turns the record into one card with
four labelled blocks, a source line and the panel's captions, so every
panel explains itself in the same shape. The copy rules for the text
live in CLAUDE.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import dash_bootstrap_components as dbc
from dash import html

BLOCKS: tuple[tuple[str, str], ...] = (
    ("what", "What this shows"),
    ("how", "How it is measured"),
    ("why", "Why it matters for El Niño"),
    ("not_shown", "What it does not show"),
)


@dataclass(frozen=True)
class Explainer:
    """The text a panel shows beside its figure."""

    title: str
    what: str
    how: str
    why: str
    not_shown: str
    source_name: str
    source_url: str
    licence_label: str
    captions: tuple[str, ...] = ()


def render_explainer(explainer: Explainer, retrieved_at: str | None = None) -> dbc.Card:
    """One card: the four labelled blocks, the source line, then each caption.

    The source line reads "Source: <name>, <licence_label>, retrieved
    <retrieved_at>" with the name linked to ``source_url``. The retrieved
    clause is omitted when ``retrieved_at`` is ``None``.
    """
    body: list = []
    for position, (field, label) in enumerate(BLOCKS):
        heading_class = "h6 mb-1" if position == 0 else "h6 mt-3 mb-1"
        body.append(html.H3(label, className=heading_class))
        body.append(html.P(getattr(explainer, field), className="mb-0"))

    source: list = [
        "Source: ",
        html.A(explainer.source_name, href=explainer.source_url),
        f", {explainer.licence_label}",
    ]
    if retrieved_at is not None:
        source.append(f", retrieved {retrieved_at}")
    body.append(html.P(source, className="text-muted small mt-3 mb-0"))

    for caption in explainer.captions:
        body.append(html.P(caption, className="small mt-3 mb-0"))

    return dbc.Card(
        [dbc.CardHeader(explainer.title), dbc.CardBody(body)],
        className="mb-3 explainer",
    )
