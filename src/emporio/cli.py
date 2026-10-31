"""Terminal chat with Mel: `python -m emporio`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import create_agent
from .config import load_settings
from .transcript import Transcript

EXIT_COMMANDS = {"/sair", "/exit", "/quit"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Chat with Mel, Empório da Música's assistant.")
    parser.add_argument("--provider", choices=["anthropic", "ollama"], help="overrides LLM_PROVIDER")
    parser.add_argument("--model", help="overrides ANTHROPIC_MODEL / OLLAMA_MODEL")
    parser.add_argument("--debug", action="store_true", help="show the tools the agent calls")
    parser.add_argument("--transcript", type=Path, help="save the conversation to this .md file")
    args = parser.parse_args(argv)

    settings = load_settings()
    provider = args.provider or settings.llm_provider
    model = args.model or (settings.anthropic_model if provider == "anthropic" else settings.ollama_model)
    agent = create_agent(settings, provider, model)
    transcript = Transcript("Conversation with Mel", f"{provider}/{model}")

    print(f"🎸 Empório da Música — Mel ({provider}/{model}). Type /sair to quit, /novo to restart.\n")
    while True:
        try:
            message = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message.lower() in EXIT_COMMANDS:
            break
        if message.lower() == "/novo":
            agent = create_agent(settings, provider, model)
            print("(new conversation)\n")
            continue
        try:
            reply = agent.reply(message)
        except Exception as exc:  # network, auth or model errors: keep the chat alive
            print(f"[error] {type(exc).__name__}: {exc}\n")
            continue
        if args.debug:
            for event in reply.tool_events:
                print(f"  🔧 {event.name}({json.dumps(event.arguments, ensure_ascii=False)})")
        print(f"Mel: {reply.text}\n")
        transcript.add(message, reply)

    if args.transcript and transcript.turns:
        transcript.save(args.transcript)
        print(f"Conversation saved to {args.transcript}")


if __name__ == "__main__":
    main()
