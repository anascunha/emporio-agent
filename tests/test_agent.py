"""Agent loop and LLM adapters, tested with scripted fake models (no network)."""

from types import SimpleNamespace

import pytest

from emporio.agent import FALLBACK_REPLY, MAX_TOOL_ROUNDS, Agent
from emporio.config import DATA_DIR
from emporio.llm import AnthropicSession, ChatSession, OllamaSession, ToolCall, Turn
from emporio.policies import PolicyManual
from emporio.tools import ToolExecutor


class ScriptedSession(ChatSession):
    """Returns pre-defined turns and records what the agent sent back."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.user_messages, self.tool_results = [], []

    def add_user_message(self, text, reply_language=None):
        self.user_messages.append((text, reply_language))

    def complete(self):
        return self.turns.pop(0)

    def add_tool_results(self, results):
        self.tool_results.append(results)

    def message_count(self):
        return 0


@pytest.fixture
def tools(store, tmp_path):
    return ToolExecutor(store, PolicyManual(DATA_DIR / "politicas_da_loja.md"), tmp_path)


def test_plain_answer_without_tools(tools):
    agent = Agent(ScriptedSession([Turn("Oi! Como posso ajudar?")]), tools)
    reply = agent.reply("oi")
    assert reply.text == "Oi! Como posso ajudar?"
    assert reply.tool_events == []


def test_tool_call_then_answer(tools):
    session = ScriptedSession(
        [
            Turn("", [ToolCall("c1", "search_products", {"query": "Takamine GD20"})]),
            Turn("O Takamine GD20 sai por R$ 2.199,00."),
        ]
    )
    reply = Agent(session, tools).reply("Quanto custa o Takamine GD20?")
    assert reply.text.endswith("R$ 2.199,00.")
    assert reply.tool_events[0].name == "search_products"
    call, output = session.tool_results[0][0]
    assert call.id == "c1" and "2.199,00" in output


def test_loop_stops_after_max_rounds(tools):
    looping = [Turn("", [ToolCall(str(i), "get_policy", {"topic": "payment"})]) for i in range(10)]
    reply = Agent(ScriptedSession(looping), tools).reply("?")
    assert reply.text == FALLBACK_REPLY
    assert len(reply.tool_events) == MAX_TOOL_ROUNDS


# ----- Anthropic adapter -------------------------------------------------------------


class FakeAnthropicMessages:
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def block(type_, **fields):
    return SimpleNamespace(type=type_, **fields)


def test_anthropic_session_round_trip():
    messages = FakeAnthropicMessages(
        [
            SimpleNamespace(
                stop_reason="tool_use",
                content=[
                    block("thinking", thinking=""),
                    block("tool_use", id="tu_1", name="get_policy", input={"topic": "payment"}),
                ],
            ),
            SimpleNamespace(stop_reason="end_turn", content=[block("text", text="Aceitamos PIX.")]),
        ]
    )
    schema = {"name": "get_policy", "description": "d", "parameters": {"type": "object"}}
    session = AnthropicSession("m", "system", [schema], client=SimpleNamespace(messages=messages))
    session.add_user_message("formas de pagamento?")
    turn = session.complete()
    assert turn.tool_calls[0].name == "get_policy"
    session.add_tool_results([(turn.tool_calls[0], '{"text": "..."}')])
    assert session.complete().text == "Aceitamos PIX."

    first = messages.requests[0]
    assert first["tools"][0]["input_schema"] == {"type": "object"}
    assert first["system"][0]["cache_control"] == {"type": "ephemeral"}
    # The assistant turn is replayed unchanged (thinking block included).
    assert messages.requests[1]["messages"][1]["content"][0].type == "thinking"
    result = messages.requests[1]["messages"][2]["content"][0]
    assert result["tool_use_id"] == "tu_1" and result["is_error"] is False


# ----- Ollama adapter ----------------------------------------------------------------


class FakeOllama:
    def __init__(self, messages):
        self.messages, self.requests = list(messages), []

    def chat(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(message=self.messages.pop(0))


def ollama_message(content="", tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


SCHEMA = {"name": "get_policy", "description": "d", "parameters": {"type": "object"}}


def test_ollama_native_tool_calls():
    call = SimpleNamespace(function=SimpleNamespace(name="get_policy", arguments={"topic": "payment"}))
    fake = FakeOllama([ollama_message(tool_calls=[call])])
    session = OllamaSession("m", "system", [SCHEMA], host="", client=fake)
    session.add_user_message("pagamento?")
    turn = session.complete()
    assert turn.tool_calls[0].arguments == {"topic": "payment"}
    session.add_tool_results([(turn.tool_calls[0], "{}")])
    assert session.messages[-1] == {"role": "tool", "tool_name": "get_policy", "content": "{}"}


def test_ollama_tool_call_written_as_text_is_recovered():
    text = 'Vou consultar: {"name": "get_policy", "arguments": {"topic": "opening_hours"}}'
    session = OllamaSession("m", "system", [SCHEMA], host="", client=FakeOllama([ollama_message(text)]))
    session.add_user_message("horário?")
    turn = session.complete()
    assert turn.text == ""
    assert turn.tool_calls[0].arguments == {"topic": "opening_hours"}


def test_ollama_ignores_json_that_is_not_a_known_tool():
    session = OllamaSession("m", "system", [SCHEMA], host="", client=FakeOllama([ollama_message('{"a": 1}')]))
    session.add_user_message("?")
    assert session.complete().tool_calls == []


def test_customer_language_is_detected_and_passed_as_hint(tools):
    session = ScriptedSession([Turn("Hi!"), Turn("Oi!"), Turn("...")])
    agent = Agent(session, tools)
    agent.reply("Hi! How much is the Yamaha F310?")
    agent.reply("anacarol.ferreira@coldmail.com")  # no signal: keeps English
    agent.reply("Oi, quanto custa o Yamaha F310?")
    assert [lang for _, lang in session.user_messages] == ["en", "en", "pt"]


def test_anthropic_language_hint_is_a_system_message_after_the_user_turn():
    messages = FakeAnthropicMessages(
        [SimpleNamespace(stop_reason="end_turn", content=[block("text", text="Hi!")])]
    )
    session = AnthropicSession("m", "system", [], client=SimpleNamespace(messages=messages))
    session.add_user_message("Hi there", "en")
    session.complete()
    sent = messages.requests[0]["messages"]
    assert sent[0] == {"role": "user", "content": "Hi there"}
    assert sent[1]["role"] == "system" and "English" in sent[1]["content"]


def test_ollama_language_hint_goes_inside_the_user_message():
    session = OllamaSession("m", "system", [SCHEMA], host="", client=FakeOllama([]))
    session.add_user_message("How much is it?", "en")
    assert [m["role"] for m in session.messages] == ["system", "user"]
    assert session.messages[-1]["content"].endswith("reply in English.)")
