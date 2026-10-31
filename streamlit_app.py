"""Web chat with Mel: `streamlit run streamlit_app.py`."""

from __future__ import annotations

import json

import streamlit as st

from emporio.agent import create_agent
from emporio.config import load_settings

MODELS = {
    "anthropic": ["claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"],
    "ollama": ["qwen2.5:3b", "llama3.2"],
}

st.set_page_config(page_title="Empório da Música — Mel", page_icon="🎸")
settings = load_settings()

with st.sidebar:
    st.header("⚙️ Settings")
    providers = list(MODELS)
    provider = st.selectbox("Provider", providers, index=providers.index(settings.llm_provider))
    default_model = settings.anthropic_model if provider == "anthropic" else settings.ollama_model
    options = MODELS[provider] if default_model in MODELS[provider] else [default_model, *MODELS[provider]]
    model = st.selectbox("Model", options, index=options.index(default_model))
    show_tools = st.toggle("Show tool calls", value=True)
    restart = st.button("🔄 New conversation", width="stretch")
    st.caption(f"Reference date (\"today\"): {settings.today:%d/%m/%Y}")

config = (provider, model)
if restart or st.session_state.get("config") != config:
    st.session_state.config = config
    st.session_state.agent = create_agent(settings, provider, model)
    st.session_state.history = []  # (role, text, tool_events)

st.title("🎸 Empório da Música")
st.caption("Chat with **Mel**, the store's virtual assistant · Sua música começa aqui.")


def render_tools(events) -> None:
    if show_tools and events:
        with st.expander(f"🔧 {len(events)} tool call(s)"):
            for event in events:
                st.markdown(f"**`{event.name}`** `{json.dumps(event.arguments, ensure_ascii=False)}`")
                st.json(event.result, expanded=False)


for role, text, events in st.session_state.history:
    with st.chat_message(role, avatar="🎵" if role == "assistant" else None):
        if role == "assistant":
            render_tools(events)
        st.markdown(text)

if message := st.chat_input("Escreva sua mensagem… / Type your message…"):
    st.session_state.history.append(("user", message, []))
    with st.chat_message("user"):
        st.markdown(message)
    with st.chat_message("assistant", avatar="🎵"):
        try:
            with st.spinner("Mel está digitando…"):
                reply = st.session_state.agent.reply(message)
        except Exception as exc:  # network, auth or model errors
            st.error(f"{type(exc).__name__}: {exc}")
            st.stop()
        render_tools(reply.tool_events)
        st.markdown(reply.text)
    st.session_state.history.append(("assistant", reply.text, reply.tool_events))
