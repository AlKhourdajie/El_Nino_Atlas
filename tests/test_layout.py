"""Tests for the layout package: captions and page builders."""

from pathlib import Path

from src.layout import captions

DESIGN = Path(__file__).resolve().parent.parent / "docs" / "DESIGN.md"


def design_captions() -> list[str]:
    """The blockquotes of the caption guardrails section, each joined into one line."""
    text = DESIGN.read_text(encoding="utf-8")
    section = text.split("## Caption guardrails", 1)[1].split("\n## ", 1)[0]
    quotes: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        if line.startswith("> "):
            current.append(line[2:].strip())
        elif current:
            quotes.append(" ".join(current))
            current = []
    if current:
        quotes.append(" ".join(current))
    return quotes


def test_captions_are_verbatim_from_the_design_notes():
    assert list(captions.CAPTIONS) == design_captions()
    assert captions.CAPTIONS == (
        captions.GROWTH,
        captions.PRICE_TRANSMISSION,
        captions.TEMPERATURE_CONTRIBUTION,
    )
