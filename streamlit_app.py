"""Web chat with Mel: `uv run streamlit run streamlit_app.py`.

A store web page with a chat widget. The sidebar holds developer controls; the main
area is what a customer would see.
"""

from __future__ import annotations

from time import perf_counter

import streamlit as st

from chat_ui.i18n import LANGUAGES, TEXT, hero_html
from chat_ui.render import TYPING_HTML, header_html, inject_css, is_dark, quick_replies, render_history
from chat_ui.skins import WEBSITE as skin
from chat_ui.state import (
    ChatTurn,
    explain_error,
    get_conversation,
    now_hhmm,
    pop_queued,
    queue,
    reset_conversation,
)
from emporio.agent import create_agent
from emporio.config import load_settings

MODELS = {
    "anthropic": ["claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"],
    "ollama": ["qwen2.5:3b"],  # best local model in the evaluation (llama3.2 dropped, decision #62)
}
THEMES = {"light": "☀️ Light", "dark": "🌙 Dark", "auto": "🖥️ Auto"}

st.set_page_config(page_title="Empório da Música — Mel", page_icon="🎸", layout="wide")
settings = load_settings()

# ----- developer sidebar ---------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Demo controls")
    # ?lang=pt and ?theme=dark open the page directly in that state (handy for demo links)
    requested_lang = st.query_params.get("lang", "en")
    lang = st.segmented_control(
        "Interface language", list(LANGUAGES), default=requested_lang if requested_lang in LANGUAGES else "en",
        required=True, format_func=LANGUAGES.get, key="lang",
        help="Language of the chat interface. Mel always answers in the customer's language.",
    )
    requested_theme = st.query_params.get("theme", "light")
    theme = st.segmented_control(
        "Theme", list(THEMES), default=requested_theme if requested_theme in THEMES else "light", required=True,
        format_func=THEMES.get, key="theme",
    )
    providers = list(MODELS)
    provider = st.selectbox("Provider", providers, index=providers.index(settings.llm_provider))
    default_model = settings.anthropic_model if provider == "anthropic" else settings.ollama_model
    options = MODELS[provider] if default_model in MODELS[provider] else [default_model, *MODELS[provider]]
    model = st.selectbox("Model", options, index=options.index(default_model))
    show_tools = st.toggle("Show tool calls", value=False, help="Reveal which lookups Mel ran under each reply.")
    if st.button("🔄 New conversation", width="stretch"):
        reset_conversation()
    st.caption(f"Reference date (\"today\"): {settings.today:%d/%m/%Y}")

if st.session_state.get("config") != (provider, model):
    st.session_state.config = (provider, model)
    reset_conversation()

conv = get_conversation()
inject_css(skin, is_dark(theme))

if conv.turns and conv.turns[-1].error:
    st.sidebar.error(explain_error(conv.turns[-1].error), icon="⚠️")

if show_tools and conv.agent is not None:
    usage = conv.agent.session.usage
    st.sidebar.caption(
        f"Tokens this conversation: {usage.get('input', 0) + usage.get('cache_read', 0):,} in "
        f"({usage.get('cache_read', 0):,} cached) · {usage.get('output', 0):,} out"
    )

# ----- customer view -------------------------------------------------------------------
hero_col, chat_col = st.columns([1.15, 1], gap="large", vertical_alignment="top")
with hero_col:
    st.html(hero_html(lang))

with chat_col, st.container(key=f"{skin.key}-frame", gap=None):
    header = st.empty()
    messages = st.container(key=f"{skin.key}-msgs", height=520, autoscroll=True, gap="small")
    chips = st.container(key=f"{skin.key}-chips", horizontal=True, wrap=True, gap="xsmall")
    typed = st.chat_input(TEXT[lang][skin.key]["placeholder"], key=f"{skin.key}-input", submit_mode="disable")
    st.html(f'<div class="web-powered">{TEXT[lang]["powered"]}</div>')

message = typed or pop_queued()
busy = bool(message)
header.html(header_html(skin, lang, typing=busy))
with chips:
    quick_replies(skin, lang, on_click=queue, disabled=busy)
if busy:
    conv.turns.append(ChatTurn(message, now_hhmm()))

with messages:
    render_history(skin, lang, conv, show_tools, in_flight=busy)

if busy:
    with messages:
        st.html(TYPING_HTML)
    turn = conv.turns[-1]
    try:
        conv.agent = conv.agent or create_agent(settings, provider, model)
        start = perf_counter()
        turn.reply = conv.agent.reply(message)
        turn.seconds, turn.replied_at = perf_counter() - start, now_hhmm()
    except Exception as exc:  # network, auth, credits or model errors
        turn.error = f"{type(exc).__name__}: {exc}"
    st.rerun()
