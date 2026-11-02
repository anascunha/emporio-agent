"""Look of the website chat widget: palette tokens (light / dark) and its stylesheet.

Brand: dark navy as the base, orange as the accent, neutrals biased toward the navy.
"""

from __future__ import annotations

from dataclasses import dataclass

# Shared brand tokens (light / dark).
BRAND_LIGHT = {
    "navy": "#13294B", "navy-2": "#1F3D6B", "orange": "#F26B1D", "orange-deep": "#C4500B",
    "orange-soft": "#FFE6D3", "ink": "#1A2233", "muted": "#5F6B80", "line": "#DDE2EA",
    "paper": "#F5F6F8", "surface": "#FFFFFF",
}
BRAND_DARK = {
    "navy": "#0B1A33", "navy-2": "#1A3359", "orange": "#FF8A3D", "orange-deep": "#E06A1F",
    "orange-soft": "#4A2A16", "ink": "#E7EBF2", "muted": "#97A3B9", "line": "#26324A",
    "paper": "#0E1524", "surface": "#162036",
}


@dataclass(frozen=True)
class Skin:
    key: str  # CSS class / widget key prefix; also the key of its texts in i18n.TEXT
    avatar: str
    css_file: str
    palette_light: dict[str, str]
    palette_dark: dict[str, str]


WEBSITE = Skin(
    key="web",
    avatar="🎵",
    css_file="website.css",
    palette_light={
        **BRAND_LIGHT,
        "in-bg": "#EEF1F6", "in-text": "#1A2233", "out-bg": "#13294B", "out-text": "#FFFFFF",
        "meta": "#6B7588", "field-bg": "#F5F6F8", "chip": "#1F3D6B", "chip-hover-text": "#FFFFFF",
    },
    palette_dark={
        **BRAND_DARK,
        "in-bg": "#1F2C47", "in-text": "#E7EBF2", "out-bg": "#2B4F86", "out-text": "#FFFFFF",
        "meta": "#97A3B9", "field-bg": "#0E1524", "chip": "#FF8A3D", "chip-hover-text": "#1A1006",
    },
)
