"""Shared design tokens for the LazyDoc desktop UI.

Keep layout and styling decisions anchored here so individual widgets do not
drift into incompatible colors, spacing, or typography.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TypeStyle:
    """A named typography role used by widgets and QSS builders."""

    family: str
    size: int
    weight: int
    line_height: int


FONT_FAMILY = "Segoe UI"
CODE_FONT_FAMILY = "Consolas"

COLORS = {
    "bg": "#151821",
    "surface": "#1c202b",
    "surface_raised": "#242a36",
    "surface_subtle": "#11141c",
    "border": "#343b4a",
    "border_strong": "#4b5568",
    "text": "#eef2f8",
    "text_muted": "#a8b0c0",
    "text_subtle": "#768094",
    "primary": "#6ea8fe",
    "primary_hover": "#8bbcff",
    "primary_pressed": "#4d8ee8",
    "primary_fg": "#0d1420",
    "secondary": "#2e3645",
    "secondary_hover": "#394456",
    "secondary_pressed": "#252c39",
    "success": "#7bd88f",
    "warning": "#f2c86d",
    "danger": "#f47f9d",
    "danger_hover": "#ff9bb4",
    "danger_pressed": "#d96683",
    "focus": "#8bbcff",
    "disabled_bg": "#252b36",
    "disabled_fg": "#687386",
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
}

RADIUS = {
    "sm": 4,
    "md": 6,
    "lg": 8,
    "xl": 10,
}

TYPOGRAPHY = {
    "heading": TypeStyle(FONT_FAMILY, 18, 700, 24),
    "section": TypeStyle(FONT_FAMILY, 13, 700, 18),
    "body": TypeStyle(FONT_FAMILY, 13, 400, 20),
    "caption": TypeStyle(FONT_FAMILY, 11, 400, 16),
    "button": TypeStyle(FONT_FAMILY, 13, 700, 18),
    "code": TypeStyle(CODE_FONT_FAMILY, 12, 400, 18),
}
