"""Rendering helpers shared by both skins.

Model text only ever goes through st.markdown (which escapes HTML); st.html only
receives strings built here from trusted values, escaped with html.escape.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from .i18n import TEXT
from .skins import Skin
from .state import ChatTurn, Conversation, md_escape

STYLES_DIR = Path(__file__).parent / "styles"

TYPING_HTML = '<div class="typing" aria-label="typing"><span></span><span></span><span></span></div>'


def is_dark(theme_choice: str) -> bool:
    """theme_choice: 'light', 'dark' or 'auto' (follow the browser/Streamlit theme)."""
    if theme_choice in ("light", "dark"):
        return theme_choice == "dark"
    return getattr(st.context.theme, "type", None) == "dark"


def inject_css(skin: Skin, dark: bool) -> None:
    """One style-only st.html call: palette variables + base CSS + the skin's CSS."""
    palette = skin.palette_dark if dark else skin.palette_light
    variables = ";".join(f"--{name}:{value}" for name, value in palette.items())
    css = (STYLES_DIR / "base.css").read_text(encoding="utf-8")
    css += (STYLES_DIR / skin.css_file).read_text(encoding="utf-8")
    st.html(f"<style>:root{{{variables}}}\n{css}</style>")


def header_html(skin: Skin, lang: str, typing: bool) -> str:
    text = TEXT[lang][skin.key]
    status = text["status_typing"] if typing else text["status_idle"]
    statusbar = (
        '<div class="msgr-statusbar"><span>9:41</span><span>5G ▮▮▮ 87%</span></div>' if skin.key == "msgr" else ""
    )
    return statusbar + (
        f'<div class="chat-header {skin.key}-header">'
        f'<div class="avatar">{html.escape(skin.avatar)}</div>'
        f'<div class="who"><div class="name">{html.escape(text["title"])}</div>'
        f'<div class="status{" typing-status" if typing else ""}">{html.escape(status)}</div></div>'
        "</div>"
    )


def _meta_html(skin: Skin, time: str | None, read: bool | None) -> str:
    ticks = ""
    if skin.ticks and read is not None:
        ticks = f' <span class="tick{" read" if read else ""}">✓✓</span>'
    return f'<div class="msg-meta">{html.escape(time or "")}{ticks}</div>'


def bubble(skin: Skin, role: str, key: str, text: str, time: str | None, read: bool | None = None) -> None:
    with st.container(key=f"{skin.key}-bubble-{role}-{key}", width="content", gap=None):
        st.markdown(md_escape(text))
        st.html(_meta_html(skin, time, read))


def notice(skin: Skin, text: str) -> None:
    st.html(f'<div class="chat-notice {skin.key}-notice">{html.escape(text)}</div>')


def tool_viewer(skin: Skin, key: str, turn: ChatTurn) -> None:
    events = turn.reply.tool_events if turn.reply else []
    names = ", ".join(dict.fromkeys(e.name for e in events)) or "no tools"
    seconds = f" · {turn.seconds:.1f}s" if turn.seconds is not None else ""
    with st.expander(f"🔧 {len(events)} tool call(s) · {names}{seconds}", key=f"{skin.key}-tools-{key}"):
        if not events:
            st.caption("Mel answered without calling a tool.")
        for event in events:
            st.markdown(f"**`{event.name}`** `{json.dumps(event.arguments, ensure_ascii=False)}`")
            st.json(event.result, expanded=False)


def render_history(skin: Skin, lang: str, conv: Conversation, show_tools: bool, in_flight: bool) -> None:
    """Draw the whole conversation. The last turn may still be waiting for its reply."""
    if skin.greets:
        with st.container(key=f"{skin.key}-row-bot-greeting", gap="xxsmall"):
            bubble(skin, "bot", "greeting", TEXT[lang]["greeting"], None)
    for i, turn in enumerate(conv.turns):
        waiting = in_flight and i == len(conv.turns) - 1
        answered = turn.reply is not None
        with st.container(key=f"{skin.key}-row-user-{i}", horizontal=True, horizontal_alignment="right"):
            bubble(skin, "user", str(i), turn.user, turn.sent_at, read=answered or waiting)
        if answered:
            with st.container(key=f"{skin.key}-row-bot-{i}", gap="xxsmall"):
                bubble(skin, "bot", str(i), turn.reply.text, turn.replied_at)
                if show_tools:
                    tool_viewer(skin, str(i), turn)
        elif turn.error:
            notice(skin, TEXT[lang]["error"])
            if show_tools:
                st.caption(f"Developer detail: {turn.error}")
        elif not waiting:
            notice(skin, TEXT[lang]["unanswered"])


def quick_replies(skin: Skin, lang: str, channel: str, on_click, disabled: bool) -> None:
    for n, label in enumerate(TEXT[lang]["quick_replies"]):
        st.button(
            md_escape(label),
            key=f"{skin.key}-chip-{n}",
            on_click=on_click,
            args=(channel, label),
            disabled=disabled,
        )
