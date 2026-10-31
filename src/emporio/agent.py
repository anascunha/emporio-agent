"""The agent: a function-calling loop on top of any ChatSession."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .config import Settings, load_settings
from .llm import AnthropicSession, ChatSession, OllamaSession
from .policies import PolicyManual
from .prompts import build_system_prompt
from .store import Store
from .tools import ToolExecutor

# Upper bound on tool rounds per customer message, so a confused model cannot loop forever.
MAX_TOOL_ROUNDS = 6

FALLBACK_REPLY = (
    "Desculpe, tive um problema para consultar essa informação agora. "
    "Você pode tentar de novo ou falar com a nossa equipe pelo WhatsApp (67) 3321-4500."
)


@dataclass
class ToolEvent:
    name: str
    arguments: dict
    result: dict


@dataclass
class Reply:
    text: str
    tool_events: list[ToolEvent] = field(default_factory=list)


class Agent:
    def __init__(self, session: ChatSession, tools: ToolExecutor):
        self.session = session
        self.tools = tools

    def reply(self, message: str) -> Reply:
        self.session.add_user_message(message)
        events: list[ToolEvent] = []
        for _ in range(MAX_TOOL_ROUNDS):
            turn = self.session.complete()
            if not turn.tool_calls:
                return Reply(turn.text or FALLBACK_REPLY, events)
            results = []
            for call in turn.tool_calls:
                output = self.tools.execute(call.name, call.arguments)
                events.append(ToolEvent(call.name, call.arguments, json.loads(output)))
                results.append((call, output))
            self.session.add_tool_results(results)
        return Reply(FALLBACK_REPLY, events)


def create_agent(
    settings: Settings | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> Agent:
    """Build a ready-to-use agent for one conversation."""
    settings = settings or load_settings()
    store = Store(settings.data_dir, settings.today)
    manual = PolicyManual(settings.data_dir / "politicas_da_loja.md")
    tools = ToolExecutor(store, manual, settings.data_dir / "runtime")
    system = build_system_prompt(settings.today)

    provider = provider or settings.llm_provider
    if provider == "anthropic":
        session: ChatSession = AnthropicSession(
            model or settings.anthropic_model, system, tools.schemas, settings.anthropic_effort
        )
    elif provider == "ollama":
        session = OllamaSession(
            model or settings.ollama_model, system, tools.schemas, settings.ollama_host
        )
    else:
        raise ValueError(f"Unknown LLM provider {provider!r} (use 'anthropic' or 'ollama').")
    return Agent(session, tools)
