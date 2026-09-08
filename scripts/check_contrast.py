"""Print WCAG 2.1 contrast ratios for the design tokens in both schemes.

Text tokens must reach 4.5:1 (success criterion 1.4.3, AA) against the
paper and the surface of their scheme. Marks, meaning the three-state
fills, the series lines, the index lines and the outline colour, must
reach 3:1 (1.4.11, non-text contrast) against the surface they are drawn
on. The ENSO phase hues appear only as low-opacity bands behind the
lines; their meaning is carried by the legend label, the outline style
and the hover text, so the check on them is that the composited band
stays perceptible against the surface (at least 1.15:1). The ratios of
the full-strength phase hues are printed for information.

``tests/test_tokens.py`` applies the same thresholds; this script prints
every ratio for the report. Exit status 1 when any check fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_tokens import load_tokens, scheme_data  # noqa: E402

TEXT_MINIMUM = 4.5
MARK_MINIMUM = 3.0
BAND_MINIMUM = 1.15
TEXT_KEYS = ("ink", "ink_muted", "accent", "error")


def _linear(channel: int) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    value = hex_colour.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def composite(foreground: str, background: str, alpha: float) -> str:
    """``foreground`` at ``alpha`` over ``background`` as a hex colour."""
    fg = foreground.lstrip("#")
    bg = background.lstrip("#")
    parts = []
    for i in (0, 2, 4):
        value = int(fg[i : i + 2], 16) * alpha + int(bg[i : i + 2], 16) * (1 - alpha)
        parts.append(f"{round(value):02X}")
    return "#" + "".join(parts)


Row = tuple[str, str, str, float, float]


def checks(tokens: dict) -> list[Row]:
    """``(scheme, foreground, background, ratio, minimum)`` for every rule.

    A minimum of 0 marks a ratio printed for information only.
    """
    rows: list[Row] = []
    for scheme_name, scheme in tokens["scheme"].items():
        data = scheme_data(tokens, scheme_name)
        for background in ("paper", "surface"):
            surface = scheme[background]
            for key in TEXT_KEYS:
                rows.append(
                    (scheme_name, key, background, contrast(scheme[key], surface), TEXT_MINIMUM)
                )
            marks = {f"state.{k}": v for k, v in data["state"].items()}
            marks.update({f"series.{i}": v for i, v in enumerate(data["series"], start=1)})
            marks["index.primary"] = data["index"]["primary"]
            marks["index.secondary"] = data["index"]["secondary"]
            marks["threshold"] = data["threshold"]
            for key, colour in marks.items():
                rows.append((scheme_name, key, background, contrast(colour, surface), MARK_MINIMUM))
            for phase, alpha in data["phase_opacity"].items():
                hue = data["phase"][phase]
                band = composite(hue, surface, alpha)
                rows.append(
                    (
                        scheme_name,
                        f"band.{phase}",
                        background,
                        contrast(band, surface),
                        BAND_MINIMUM,
                    )
                )
                rows.append(
                    (scheme_name, f"phase.{phase} (hue)", background, contrast(hue, surface), 0.0)
                )
        rows.append(
            (
                scheme_name,
                "accent_ink",
                "accent",
                contrast(scheme["accent_ink"], scheme["accent"]),
                TEXT_MINIMUM,
            )
        )
        rows.append(
            (
                scheme_name,
                "error",
                "error_surface",
                contrast(scheme["error"], scheme["error_surface"]),
                TEXT_MINIMUM,
            )
        )
    return rows


def failures(tokens: dict) -> list[Row]:
    return [row for row in checks(tokens) if row[3] < row[4]]


def main() -> int:
    tokens = load_tokens()
    rows = checks(tokens)
    current = None
    for scheme, key, background, ratio, minimum in rows:
        if scheme != current:
            print(f"== {scheme} scheme")
            current = scheme
        if minimum == 0:
            verdict = "info"
        else:
            verdict = "ok" if ratio >= minimum else "FAIL"
        print(f"  {key:22s} on {background:14s} {ratio:6.2f}  (min {minimum:.2f})  {verdict}")
    failed = failures(tokens)
    counted = [row for row in rows if row[4] > 0]
    print(f"{len(counted) - len(failed)} of {len(counted)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
