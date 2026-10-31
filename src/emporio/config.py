"""Runtime configuration, read from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# The latest order in the dataset is from 2026-03-22, so "today" defaults to the
# following day. See docs/decisions.md (#9).
DEFAULT_TODAY = date(2026, 3, 23)


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    anthropic_model: str
    anthropic_effort: str
    ollama_host: str
    ollama_model: str
    today: date
    data_dir: Path


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    today_raw = os.getenv("EMPORIO_TODAY", "").strip()
    if not today_raw:
        today = DEFAULT_TODAY
    elif today_raw.lower() == "real":
        today = date.today()
    else:
        today = date.fromisoformat(today_raw)
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic").strip().lower(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        anthropic_effort=os.getenv("ANTHROPIC_EFFORT", "low"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        today=today,
        data_dir=Path(os.getenv("EMPORIO_DATA_DIR", DATA_DIR)),
    )
