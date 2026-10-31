"""Small text helpers for matching Portuguese input (accents, case, phone numbers)."""

from __future__ import annotations

import re
import unicodedata


def fold(text: str) -> str:
    """Lowercase and strip accents: 'Violão Elétrico' -> 'violao eletrico'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", fold(text))


def digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def brl(value: float) -> str:
    """Format a number as Brazilian currency: 1234.5 -> 'R$ 1.234,50'."""
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"
