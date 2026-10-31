"""Web chat with Mel: `uv run streamlit run streamlit_app.py`.

Two channel skins (mobile messenger and website widget) on the same agent. The sidebar
holds developer controls; the main area is what a customer would see.
"""

from __future__ import annotations

from time import perf_counter

import streamlit as st

from chat_ui.render import TYPING_HTML, header_html, inject_css, is_dark, quick_replies, render_history
from chat_ui.skins import SKINS
from chat_ui.state import (
    CHANNELS,
    ChatTurn,
    get_conversation,
    now_hhmm,
    pop_queued,
    queue,
    reset_all,
    reset_conversation,
)
from emporio.agent import create_agent
from emporio.config import load_settings

MODELS = {
    "anthropic": ["claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"],
    "ollama": ["qwen2.5:3b", "llama3.2"],
}

st.set_page_config(page_title="Empório da Música — Mel", page_icon="🎸", layout="wide")
settings = load_settings()

# ----- developer sidebar ---------------------------------------------------------------
THEMES = {"light": "☀️ Light", "dark": "🌙 Dark", "auto": "🖥️ Auto"}

with st.sidebar:
    st.header("⚙️ Demo controls")
    # ?channel=website opens a channel directly (handy for demo links)
    requested = st.query_params.get("channel", "messenger")
    channel = st.segmented_control(
        "Channel", CHANNELS, default=requested if requested in CHANNELS else "messenger",
        required=True, format_func=lambda c: SKINS[c].label, key="channel",
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
    if st.button("🔄 New conversation", width="stretch", help="Restart the current channel only."):
        reset_conversation(channel)
    st.caption(f"Reference date (\"today\"): {settings.today:%d/%m/%Y}")

if st.session_state.get("config") != (provider, model):
    st.session_state.config = (provider, model)
    reset_all()

skin = SKINS[channel]
conv = get_conversation(channel)
inject_css(skin, is_dark(theme))

if show_tools and conv.agent is not None:
    usage = conv.agent.session.usage
    st.sidebar.caption(
        f"Tokens this conversation: {usage.get('input', 0) + usage.get('cache_read', 0):,} in "
        f"({usage.get('cache_read', 0):,} cached) · {usage.get('output', 0):,} out"
    )

# ----- customer view -------------------------------------------------------------------
WEB_HERO = """
<div class="web-hero">
  <div class="eyebrow">Campo Grande · MS · desde 2008</div>
  <h1>Empório da Música</h1>
  <div class="tagline">Sua música começa aqui.</div>
  <div class="facts">
    <div class="fact"><b>LOJA</b><span>Rua 14 de Maio, 3200 · Centro</span></div>
    <div class="fact"><b>HORÁRIO</b><span>Seg a sex 9h às 18h · Sáb 9h às 13h</span></div>
    <div class="fact"><b>PAGAMENTO</b><span>5% off no PIX · até 12x sem juros</span></div>
    <div class="fact"><b>ENTREGA</b><span>Frete grátis acima de R$ 500 na Grande Campo Grande</span></div>
  </div>
  <div class="cta">Dúvidas sobre instrumentos, pedidos ou trocas? <strong>Fale com a Mel</strong>, nossa assistente virtual.</div>
</div>
"""

if channel == "website":
    hero_col, chat_col = st.columns([1.15, 1], gap="large", vertical_alignment="top")
    with hero_col:
        st.html(WEB_HERO)
    chat_area = chat_col
else:
    chat_area = st.container()

with chat_area, st.container(key=f"{skin.key}-frame", gap=None):
    header = st.empty()
    messages = st.container(key=f"{skin.key}-msgs", height=520, autoscroll=True, gap="small")
    chips = st.container(key=f"{skin.key}-chips", horizontal=True, wrap=True, gap="xsmall") if skin.quick_replies else None
    typed = st.chat_input(skin.placeholder, key=f"{skin.key}-input", submit_mode="disable")
    if channel == "website":
        st.html('<div class="web-powered">Atendimento virtual · respostas com base no sistema da loja</div>')

message = typed or pop_queued(channel)
busy = bool(message)
header.html(header_html(skin, typing=busy))
if chips is not None:
    with chips:
        quick_replies(skin, channel, on_click=queue, disabled=busy)
if busy:
    conv.turns.append(ChatTurn(message, now_hhmm()))

with messages:
    if channel == "messenger":
        st.html('<div class="msgr-day"><span>HOJE</span></div>')
        st.html('<div class="chat-notice msgr-notice">Atendimento virtual da Mel · peça um atendente quando quiser</div>')
    render_history(skin, conv, show_tools, in_flight=busy)

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
