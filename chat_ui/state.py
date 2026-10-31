"""Per-channel conversation state kept in st.session_state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from emporio.agent import Agent, Reply

CHANNELS = ("messenger", "website")


@dataclass
class ChatTurn:
    user: str
    sent_at: str
    reply: Reply | None = None
    replied_at: str | None = None
    seconds: float | None = None
    error: str | None = None


@dataclass
class Conversation:
    """One customer session: its own agent (history + tool state) and its turns."""

    agent: Agent | None = None  # created on the first message
    turns: list[ChatTurn] = field(default_factory=list)


def get_conversation(channel: str) -> Conversation:
    chats = st.session_state.setdefault("chats", {c: Conversation() for c in CHANNELS})
    return chats[channel]


def reset_conversation(channel: str) -> None:
    get_conversation(channel)  # make sure the dict exists
    st.session_state.chats[channel] = Conversation()


def reset_all() -> None:
    st.session_state.chats = {c: Conversation() for c in CHANNELS}


def queue(channel: str, text: str) -> None:
    """Button callback (runs before the script): send `text` on the next run."""
    st.session_state.queued = (channel, text)


def pop_queued(channel: str) -> str | None:
    queued = st.session_state.pop("queued", None)
    return queued[1] if queued and queued[0] == channel else None


def now_hhmm() -> str:
    try:
        tz = ZoneInfo(st.context.timezone) if st.context.timezone else None
    except Exception:  # unknown zone or missing tzdata
        tz = None
    return datetime.now(tz).strftime("%H:%M")


def md_escape(text: str) -> str:
    """Escape '$' so prices like 'R$ 1.000 ... R$ 2.000' are not rendered as LaTeX."""
    return text.replace("$", r"\$")
