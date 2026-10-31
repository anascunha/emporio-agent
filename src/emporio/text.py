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


def stem(word: str) -> str:
    """Very light Portuguese/English plural stemmer for matching: 'violões' -> 'violao'.

    Expects a folded word (no accents). Not linguistically complete, just enough for
    instrument names: ões/ães/ãos -> ão, ns -> m, trailing s.
    """
    for plural, singular in (("oes", "ao"), ("aes", "ao"), ("aos", "ao"), ("ns", "m")):
        if word.endswith(plural) and len(word) > len(plural) + 2:
            return word[: -len(plural)] + singular
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


PT_WORDS = {"voce", "nao", "para", "com", "uma", "que", "esta", "temos", "loja", "seu", "sua",
            "por", "pode", "tem", "quero", "qual", "quanto", "custa", "meu", "minha", "oi", "ola", "obrigado"}
EN_WORDS = {"you", "the", "and", "for", "with", "can", "is", "your", "we", "have", "store", "it",
            "this", "of", "how", "much", "what", "my", "i", "hi", "hello", "do", "does", "thanks"}


def detect_language(text: str) -> str | None:
    """'pt', 'en', or None when the text gives no clear signal (e.g. 'ok', an e-mail)."""
    words = tokens(text)
    pt = sum(w in PT_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    if pt == en:
        return None
    return "en" if en > pt else "pt"


def digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def brl(value: float) -> str:
    """Format a number as Brazilian currency: 1234.5 -> 'R$ 1.234,50'."""
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"
