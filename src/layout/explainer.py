"""The explainer every panel shows with its figure.

A panel module exposes ``build_figure(...)`` and ``explainer() ->
Explainer``. The layout renders the record in two parts around the
figure. The card header carries the title, the first sentence of the
"what" block as a one-line lede, the source line with its licence badge
and retrieval stamp, and a "Source and method" disclosure holding the
"how" block with its one link. The card body, beneath the figure,
carries the rest of the "what" block, the "why" block, the "what it does
not show" block and the panel's captions, in the contract order. The
copy rules for the text live in CLAUDE.md.

A block is plain text. It may carry one link written ``[label](url)``,
which is rendered as an anchor; the copy rules reserve that for the
"how" block, which links the source's own description.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dash import html

BLOCKS: tuple[tuple[str, str], ...] = (
    ("what", "What this shows"),
    ("how", "How it is measured"),
    ("why", "Why it matters for El Niño"),
    ("not_shown", "What it does not show"),
)
METHOD_SUMMARY = "Source and method"

_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def _with_links(text: str) -> list:
    """``text`` split into strings and anchors, one anchor per ``[label](url)``."""
    parts: list = []
    last = 0
    for match in _LINK_RE.finditer(text):
        if match.start() > last:
            parts.append(text[last : match.start()])
        parts.append(html.A(match.group(1), href=match.group(2)))
        last = match.end()
    if last < len(text):
        parts.append(text[last:])
    return parts


def split_lede(text: str) -> tuple[str, str]:
    """``text`` as its first sentence and the remainder.

    The remainder is ``""`` when the block is one sentence. The two parts
    joined by one space give ``text`` back unchanged.
    """
    match = _SENTENCE_END_RE.search(text)
    if match is None:
        return text, ""
    return text[: match.start()], text[match.end() :]


@dataclass(frozen=True)
class Explainer:
    """The text a panel shows with its figure."""

    title: str
    what: str
    how: str
    why: str
    not_shown: str
    source_name: str
    source_url: str
    licence_label: str
    captions: tuple[str, ...] = ()


def lede(explainer: Explainer) -> str:
    """The one sentence on what the panel shows: the first of the "what" block."""
    return split_lede(explainer.what)[0]


def source_line(explainer: Explainer, retrieved_at: str | None = None) -> html.P:
    """The source line: the name linked, the licence as a badge, the retrieval stamp.

    Reads "Source: <name>, <licence_label>, retrieved <retrieved_at>", with
    the licence label set in a badge. The retrieved clause is omitted when
    ``retrieved_at`` is ``None``.
    """
    children: list = [
        "Source: ",
        html.A(explainer.source_name, href=explainer.source_url),
        ", ",
        html.Span(explainer.licence_label, className="badge"),
    ]
    if retrieved_at is not None:
        children.append(", ")
        children.append(html.Span(f"retrieved {retrieved_at}", className="stamp"))
    return html.P(children, className="card__source")


def method_disclosure(explainer: Explainer) -> html.Details:
    """The "Source and method" disclosure: the "how" block, labelled, with its link."""
    return html.Details(
        [
            html.Summary(METHOD_SUMMARY),
            html.H3(BLOCKS[1][1], className="card__how-label"),
            html.P(_with_links(explainer.how), className="card__how"),
        ],
        className="card__method",
    )


def explainer_header(explainer: Explainer, retrieved_at: str | None = None) -> list:
    """The header parts after the title: lede, source line, method disclosure."""
    return [
        html.P(lede(explainer), className="card__lede"),
        source_line(explainer, retrieved_at),
        method_disclosure(explainer),
    ]


def explainer_body(explainer: Explainer) -> html.Div:
    """The blocks beneath the figure, in the contract order, then the captions.

    The "how" block is not repeated here: it sits in the header's
    disclosure, between the "what" lede and these blocks.
    """
    what_rest = split_lede(explainer.what)[1]
    blocks: list = []
    if what_rest:
        blocks.append(html.H3(BLOCKS[0][1]))
        blocks.append(html.P(_with_links(what_rest)))
    for field, label in BLOCKS[2:]:
        blocks.append(html.H3(label))
        blocks.append(html.P(_with_links(getattr(explainer, field))))
    for caption in explainer.captions:
        blocks.append(html.P(caption, className="caption"))
    return html.Div(blocks, className="card__body")


def render_explainer(explainer: Explainer, retrieved_at: str | None = None) -> html.Div:
    """The explainer in full: the header parts, then the body.

    The layout places the figure between the two; this helper renders
    them together for tests and for callers without a figure.
    """
    return html.Div(
        [*explainer_header(explainer, retrieved_at), explainer_body(explainer)],
        className="explainer",
    )
