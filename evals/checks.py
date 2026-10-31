"""Deterministic checks for one conversation turn."""

from __future__ import annotations

from emporio.agent import Reply
from emporio.text import fold, tokens

PT_WORDS = {"voce", "nao", "para", "com", "uma", "que", "esta", "temos", "loja", "seu", "sua", "por", "pode", "tem"}
EN_WORDS = {"you", "the", "and", "for", "with", "can", "is", "your", "we", "have", "store", "it", "this", "of"}


def detect_language(text: str) -> str:
    words = tokens(text)
    pt = sum(w in PT_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    return "en" if en > pt else "pt"


def check_turn(spec: dict, reply: Reply) -> list[dict]:
    """Return one {check, kind, passed, detail} entry per expectation in the spec.

    kind is "tool" (did it use the right tools?) or "content" (is the answer right?).
    Text comparisons ignore case and accents.
    """
    called = [e.name for e in reply.tool_events]
    text = fold(reply.text)
    results = []

    def add(check, kind, passed, detail=""):
        results.append({"check": check, "kind": kind, "passed": bool(passed), "detail": detail})

    for tool in spec.get("expect_tools", []):
        add(f"calls {tool}", "tool", tool in called, f"called: {called}")
    for tool in spec.get("forbid_tools", []):
        add(f"does not call {tool}", "tool", tool not in called, f"called: {called}")
    for term in spec.get("contains_all", []):
        add(f"mentions '{term}'", "content", fold(term) in text)
    if spec.get("contains_any"):
        needed = spec.get("min_any", 1)
        found = [t for t in spec["contains_any"] if fold(t) in text]
        add(f"mentions {needed}+ of {len(spec['contains_any'])} expected terms", "content",
            len(found) >= needed, f"found: {found}")
    for term in spec.get("not_contains", []):
        add(f"does not mention '{term}'", "content", fold(term) not in text)
    if "language" in spec:
        lang = detect_language(reply.text)
        add(f"answers in {spec['language']}", "content", lang == spec["language"], f"detected: {lang}")
    return results
