"""Record a conversation and export it as Markdown (used by the CLI and the examples)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .agent import Reply


@dataclass
class Transcript:
    title: str
    model: str
    turns: list[tuple[str, Reply]] = field(default_factory=list)

    def add(self, message: str, reply: Reply) -> None:
        self.turns.append((message, reply))

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"_Model: `{self.model}`_", ""]
        for message, reply in self.turns:
            lines += [f"**Customer:** {message}", ""]
            for event in reply.tool_events:
                args = json.dumps(event.arguments, ensure_ascii=False)
                lines.append(f"> 🔧 `{event.name}({args})`")
            if reply.tool_events:
                lines.append("")
            lines += [f"**Mel:** {reply.text}", "", "---", ""]
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")
