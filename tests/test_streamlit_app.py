"""Smoke tests for the Streamlit chat UI with a fake agent (no network, no LLM)."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from chat_ui.skins import SKINS
from chat_ui.state import md_escape
from emporio.agent import Reply, ToolEvent


class FakeAgent:
    def __init__(self, fail=False):
        self.received, self.fail = [], fail
        self.session = SimpleNamespace(usage={"input": 10, "output": 5, "cache_read": 0})

    def reply(self, message):
        if self.fail:
            raise RuntimeError("credit balance is too low")
        self.received.append(message)
        return Reply(
            "**Oi!** Temos opções de R$ 1.000 e R$ 2.000.",
            [ToolEvent("search_products", {"query": "violão"}, {"products": []})],
        )


@pytest.fixture
def agents(monkeypatch):
    created = []

    def factory(*args, **kwargs):
        agent = FakeAgent(fail=getattr(factory, "fail", False))
        created.append(agent)
        return agent

    monkeypatch.setattr("emporio.agent.create_agent", factory)
    factory.created = created
    return factory


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=15).run()


def markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_loads_on_messenger_without_errors(agents):
    at = app()
    assert not at.exception
    assert at.chat_input(key="msgr-input")
    assert agents.created == []  # the agent is only created on the first message


def test_sending_a_message_shows_the_reply(agents):
    at = app()
    at.chat_input(key="msgr-input").set_value("oi").run()
    assert not at.exception
    assert agents.created[0].received == ["oi"]
    assert "Oi!" in markdown_text(at)
    assert r"R\$ 1.000" in markdown_text(at)  # "$" escaped, so no LaTeX


def test_website_channel_has_greeting_and_quick_replies(agents):
    at = app()
    at.sidebar.segmented_control(key="channel").set_value("website").run()
    assert not at.exception
    assert "assistente virtual" in markdown_text(at)
    assert at.button(key="web-chip-0")


def test_quick_reply_sends_its_label(agents):
    at = app()
    at.sidebar.segmented_control(key="channel").set_value("website").run()
    at.button(key="web-chip-2").click().run()
    assert agents.created[0].received == ["Horário da loja"]


def test_channels_keep_separate_conversations(agents):
    at = app()
    at.chat_input(key="msgr-input").set_value("pedido 8").run()
    at.sidebar.segmented_control(key="channel").set_value("website").run()
    assert "pedido 8" not in markdown_text(at)


def test_tool_viewer_only_when_toggle_is_on(agents):
    at = app()
    at.chat_input(key="msgr-input").set_value("violões").run()
    assert len(at.expander) == 0
    at.sidebar.toggle[0].set_value(True).run()
    assert len(at.expander) == 1


def test_agent_errors_become_a_chat_notice(agents):
    agents.fail = True
    at = app()
    at.chat_input(key="msgr-input").set_value("oi").run()
    assert not at.exception
    assert any("Não foi possível responder" in h.value for h in at.get("html"))


def test_md_escape_and_no_trademark_in_skins():
    assert md_escape("R$ 1 e R$ 2") == r"R\$ 1 e R\$ 2"
    for skin in SKINS.values():
        assert "whatsapp" not in repr(skin).lower()
