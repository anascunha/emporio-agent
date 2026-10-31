"""The two channel skins: everything that differs between them is data here + CSS."""

from __future__ import annotations

from dataclasses import dataclass


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
        "header": "#008069", "header-text": "#ffffff", "bg": "#efeae2", "dots": "rgba(0,0,0,.07)",
        "in-bg": "#ffffff", "out-bg": "#d9fdd3", "text": "#111b21", "meta": "#667781",
        "tick-read": "#53bdeb", "input-bg": "#f0f2f5", "field-bg": "#ffffff", "send": "#00a884",
        "chip-bg": "#ffffff", "notice-bg": "#ffeecd", "frame": "#1f2328",
    },
    palette_dark={
        "header": "#202c33", "header-text": "#e9edef", "bg": "#0b141a", "dots": "rgba(255,255,255,.04)",
        "in-bg": "#202c33", "out-bg": "#005c4b", "text": "#e9edef", "meta": "#8696a0",
        "tick-read": "#53bdeb", "input-bg": "#202c33", "field-bg": "#2a3942", "send": "#00a884",
        "chip-bg": "#182229", "notice-bg": "#182229", "frame": "#000000",
    },
)

WEBSITE = Skin(
    key="web",
    label="💻 Website chat",
    title="Mel · Assistente virtual",
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
        "brand": "#1B4F72", "brand-2": "#2E86C1", "accent": "#E67E22", "page": "#f4f6f9",
        "bg": "#ffffff", "in-bg": "#F1F4F8", "in-text": "#1d2939", "out-bg": "#1B4F72",
        "out-text": "#ffffff", "meta": "#667085", "border": "#e4e7ec", "field-bg": "#ffffff",
    },
    palette_dark={
        "brand": "#1B4F72", "brand-2": "#2E86C1", "accent": "#E67E22", "page": "#0e1117",
        "bg": "#161b22", "in-bg": "#21262d", "in-text": "#e6edf3", "out-bg": "#2E86C1",
        "out-text": "#ffffff", "meta": "#8b949e", "border": "#30363d", "field-bg": "#0d1117",
    },
)

SKINS = {"messenger": MESSENGER, "website": WEBSITE}
