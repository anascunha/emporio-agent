"""Topic-based access to the store policy manual.

The manual is short (8 pages), so instead of embeddings and chunking each topic maps
to whole sections. A rule and its exceptions always travel together, and what the
agent read is easy to audit. Where the manual contradicts itself, a clarification
note is appended so the agent applies the same interpretation every time.
"""

from __future__ import annotations

import re
from pathlib import Path

# topic -> (manual sections, short description shown to the LLM)
TOPICS: dict[str, tuple[list[str], str]] = {
    "store_info": (["1"], "about the store, address, phone, e-mail, what it sells"),
    "opening_hours": (["2"], "opening hours, holidays, special dates"),
    "payment": (["3"], "payment methods, PIX discount, installments, combined payment"),
    "returns_exchanges": (["4"], "regret/returns, defective items, preference exchanges, non-eligible items"),
    "shipping": (["5"], "delivery fees, delivery times, carriers, tracking codes"),
    "promotions": (["6"], "promotion calendar and promotion rules"),
    "warranty": (["8"], "legal and manufacturer warranty, what is not covered"),
    "privacy": (["9"], "personal data, LGPD, data deletion"),
    "customer_service": (["7", "10"], "service channels, scope of service, complaints"),
}

# Interpretations of ambiguous or contradictory passages (see docs/decisions.md).
NOTES: dict[str, str] = {
    "store_info": (
        "Clarification: the manual lists two numbers. (67) 3341-4444 is the store phone "
        "(section 1.2); (67) 3321-4500 is the WhatsApp customer-service channel (section 7). "
        "Give both, each with its purpose. The e-mail is contato@emporiodamusica.com.br "
        "(the accented spelling in 1.2 is a typo; the cover page has no accent). "
        "The manual mentions wind and orchestral string instruments, but the current "
        "system catalog has none listed: say so and offer to forward the request to the team."
    ),
    "payment": (
        "Clarification: the table says 'minimum installment R$ 100', but item 3.1 is more "
        "specific and prevails: up to 3x needs installments of at least R$ 50; 4x-6x at "
        "least R$ 80; 7x-12x at least R$ 100. Never compute installments yourself: use "
        "the product tools, which already apply these rules."
    ),
    "returns_exchanges": (
        "Clarification: orders have no recorded delivery date, so the estimated delivery "
        "date is used as the receipt date. Tell the customer it is an estimate and that "
        "the team confirms the final decision. Defects after 30 days are still covered by "
        "the 90-day legal warranty (section 8.1) counted from receipt."
    ),
    "customer_service": (
        "Clarification: this assistant cannot open a chat with a human by itself; it "
        "registers the case with the escalation tool and the team replies within 24 "
        "business hours."
    ),
}

_SECTION_RE = re.compile(r"^## (\d+)\. ", re.MULTILINE)


class PolicyManual:
    def __init__(self, path: Path):
        text = path.read_text(encoding="utf-8")
        self.sections: dict[str, str] = {}
        matches = list(_SECTION_RE.finditer(text))
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            self.sections[match.group(1)] = text[match.start():end].strip()

    def get(self, topic: str) -> str:
        if topic not in TOPICS:
            raise KeyError(f"unknown topic {topic!r}; valid topics: {', '.join(TOPICS)}")
        sections, _ = TOPICS[topic]
        parts = [self.sections[number] for number in sections]
        if topic in NOTES:
            parts.append(NOTES[topic])
        return "\n\n".join(parts)
