"""The two channel skins: everything that differs between them is data here + CSS.

Brand: dark navy as the base, orange as the accent, neutrals biased toward the navy.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote


def staff_lines(color: str) -> str:
    """CSS url() of a music-staff wallpaper tile (five lines), percent-encoded.

    Encoded on purpose: a literal less-than sign would make the HTML sanitizer drop
    the whole style block.
    """
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='40' height='112'>"
        f"<path d='M0 24.5H40M0 32.5H40M0 40.5H40M0 48.5H40M0 56.5H40' stroke='{color}' stroke-width='1'/>"
        "</svg>"
    )
    return f'url("data:image/svg+xml,{quote(svg)}")'


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
    key: str  # CSS class / widget key prefix
    label: str  # shown in the developer sidebar
    title: str
    status_idle: str
    status_typing: str
    avatar: str
    placeholder: str
    ticks: bool
    greeting: str | None
    quick_replies: tuple[str, ...]
    css_file: str
    palette_light: dict[str, str]
    palette_dark: dict[str, str]


MESSENGER = Skin(
    key="msgr",
    label="📱 Mobile messenger",
    title="Empório da Música",
    status_idle="online",
    status_typing="digitando…",
    avatar="EM",
    placeholder="Mensagem",
    ticks=True,
    greeting=None,  # on a messaging app the customer starts the conversation
    quick_replies=(),
    css_file="messenger.css",
    palette_light={
        **BRAND_LIGHT,
        "wall": "#F3EEE8", "staff": staff_lines("rgba(19,41,75,0.08)"),
        "in-bg": "#FFFFFF", "in-text": "#1A2233", "out-bg": "#FFE3CC", "out-text": "#2B1608",
        "meta": "#7A8496", "tick-read": "#F26B1D", "field-bg": "#FFFFFF", "bar": "#ECE7E1",
        "frame": "#0B1A33", "chip-bg": "#FFFFFF",
    },
    palette_dark={
        **BRAND_DARK,
        "wall": "#0F1726", "staff": staff_lines("rgba(231,235,242,0.06)"),
        "in-bg": "#1C2A45", "in-text": "#E7EBF2", "out-bg": "#9A4512", "out-text": "#FFF3EA",
        "meta": "#97A3B9", "tick-read": "#FF8A3D", "field-bg": "#1C2A45", "bar": "#121C30",
        "frame": "#000000", "chip-bg": "#1C2A45",
    },
)

WEBSITE = Skin(
    key="web",
    label="💻 Website chat",
    title="Fale com a Mel",
    status_idle="Online agora",
    status_typing="Mel está digitando…",
    avatar="🎵",
    placeholder="Escreva sua mensagem…",
    ticks=False,
    greeting=(
        "Oi! Eu sou a **Mel**, assistente virtual da Empório da Música 🎸\n\n"
        "Posso te ajudar a encontrar um instrumento, ver o status de um pedido ou tirar "
        "dúvidas sobre a loja. Como posso ajudar?"
    ),
    quick_replies=(
        "Ver violões até R$ 1.000",
        "Status do meu pedido",
        "Horário da loja",
        "Trocas e devoluções",
    ),
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

SKINS = {"messenger": MESSENGER, "website": WEBSITE}
