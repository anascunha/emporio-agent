"""Experiment: does Portuguese tool output make a model answer English speakers in Portuguese?

Hypothesis (from evaluation case 16): smaller models drift into Portuguese when the
context fills with Portuguese text returned by tools, especially long policy-manual
sections. Each English question is asked N times in a fresh conversation, with the
current prompt and with an extra language reminder, and we count wrong-language answers.

    python -m evals.language_probe --model claude-haiku-5-5 --runs 5
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from emporio.agent import create_agent
from emporio.config import load_settings
from emporio.prompts import build_system_prompt

from .checks import detect_language

QUESTIONS = {
    "catalog (short PT product data)": "Hi! How much is the Yamaha F310?",
    "policy (long PT manual text)": "Hi! What payment methods do you accept, and can I pay in installments?",
    "catalog + policy": "Hi! How much is the Yamaha F310, and can I pay in installments?",
}

REMINDER = (
    "\nLanguage reminder: tool results and the manual are in Portuguese, but always reply "
    "in the language of the customer's latest message. If the customer writes in English, "
    "the whole reply must be in English.\n"
)


def run(model: str, runs: int, with_reminder: bool) -> dict[str, dict]:
    settings = load_settings()
    stats: dict[str, dict] = defaultdict(lambda: {"wrong": 0, "runs": 0, "policy_calls": 0})
    for label, question in QUESTIONS.items():
        for _ in range(runs):
            agent = create_agent(settings, "anthropic", model)
            if with_reminder:
                agent.session.system[0]["text"] = build_system_prompt(settings.today) + REMINDER
            reply = agent.reply(question)
            s = stats[label]
            s["runs"] += 1
            s["wrong"] += detect_language(reply.text) != "en"
            s["policy_calls"] += any(e.name == "get_policy" for e in reply.tool_events)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-haiku-5-5")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    print(f"Model: {args.model}, {args.runs} runs per question\n")
    print("| Question type | Variant | Answered in Portuguese | Called get_policy |")
    print("|---|---|---|---|")
    for with_reminder in (False, True):
        variant = "prompt + language reminder" if with_reminder else "current prompt"
        for label, s in run(args.model, args.runs, with_reminder).items():
            print(f"| {label} | {variant} | {s['wrong']}/{s['runs']} | {s['policy_calls']}/{s['runs']} |")


if __name__ == "__main__":
    main()
