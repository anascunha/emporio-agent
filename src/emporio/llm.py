"""LLM backends behind one small interface.

Each backend keeps the conversation history in its provider's native format (Anthropic
content blocks, Ollama chat messages), so nothing provider-specific leaks into the agent
loop. Adding a provider means implementing the four methods of `ChatSession`.
"""

from __future__ import annotations

import json
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Turn:
    """One model response: text for the customer and/or tool calls to run."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class ChatSession(ABC):
    @abstractmethod
    def add_user_message(self, text: str) -> None: ...

    @abstractmethod
    def complete(self) -> Turn:
        """Ask the model for its next turn and record it in the history."""

    @abstractmethod
    def add_tool_results(self, results: list[tuple[ToolCall, str]]) -> None: ...

    @abstractmethod
    def message_count(self) -> int: ...


# ----- Anthropic -----------------------------------------------------------------------


class AnthropicSession(ChatSession):
    def __init__(self, model: str, system: str, tools: list[dict], effort: str = "low", client=None):
        import anthropic

        self.client = client or anthropic.Anthropic()
        self.model = model
        self.effort = effort
        # System prompt and tools never change during a conversation: cache them.
        self.system = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        self.tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
            for t in tools
        ]
        self.messages: list[dict] = []

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def complete(self) -> Turn:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=self.system,
            tools=self.tools,
            messages=self.messages,
            output_config={"effort": self.effort},
            cache_control={"type": "ephemeral"},  # also cache the growing history
        )
        # Keep the full content (thinking and tool_use blocks) exactly as returned.
        self.messages.append({"role": "assistant", "content": response.content})
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        calls = [
            ToolCall(b.id, b.name, dict(b.input)) for b in response.content if b.type == "tool_use"
        ]
        if response.stop_reason == "refusal" and not text:
            text = "Desculpe, não consigo ajudar com isso. Posso ajudar com instrumentos ou pedidos?"
        return Turn(text, calls)

    def add_tool_results(self, results: list[tuple[ToolCall, str]]) -> None:
        # All results of one turn go back in a single user message.
        self.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": output,
                        "is_error": _is_error(output),
                    }
                    for call, output in results
                ],
            }
        )

    def message_count(self) -> int:
        return len(self.messages)


def _is_error(output: str) -> bool:
    try:
        return "error" in json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return False


# ----- Ollama --------------------------------------------------------------------------

_JSON_CALL = re.compile(r"\{.*\}", re.DOTALL)


class OllamaSession(ChatSession):
    def __init__(self, model: str, system: str, tools: list[dict], host: str, client=None):
        import ollama

        self.client = client or ollama.Client(host=host)
        self.model = model
        self.tools = [{"type": "function", "function": t} for t in tools]
        self.tool_names = {t["name"] for t in tools}
        self.messages: list[dict] = [{"role": "system", "content": system}]

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def complete(self) -> Turn:
        response = self.client.chat(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            options={"temperature": 0.2, "num_ctx": 8192},
        )
        message = response.message
        text = (message.content or "").strip()
        calls = [
            ToolCall(uuid.uuid4().hex[:8], c.function.name, dict(c.function.arguments or {}))
            for c in (message.tool_calls or [])
        ]
        if not calls:
            # Small models sometimes write the tool call as JSON in the text.
            calls = self._calls_from_text(text)
            if calls:
                text = ""
        self.messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {"function": {"name": c.name, "arguments": c.arguments}} for c in calls
                ],
            }
        )
        return Turn(text, calls)

    def _calls_from_text(self, text: str) -> list[ToolCall]:
        match = _JSON_CALL.search(text)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
        name = data.get("name") if isinstance(data, dict) else None
        if name not in self.tool_names:
            return []
        args = data.get("arguments") or data.get("parameters") or {}
        return [ToolCall(uuid.uuid4().hex[:8], name, args if isinstance(args, dict) else {})]

    def add_tool_results(self, results: list[tuple[ToolCall, str]]) -> None:
        for call, output in results:
            self.messages.append({"role": "tool", "tool_name": call.name, "content": output})

    def message_count(self) -> int:
        return len(self.messages) - 1
