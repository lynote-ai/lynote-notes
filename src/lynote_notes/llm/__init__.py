"""Provider factory.

Environment variables:
    LNOTE_PROVIDER      heuristic (default) | openai
    LNOTE_LLM_BASE_URL  default http://localhost:11434/v1 (Ollama)
    LNOTE_LLM_API_KEY   default "ollama"
    LNOTE_LLM_MODEL     default "llama3.1"
"""

from __future__ import annotations

import os

from .base import AnswerDraft, BulletDraft, NoteProvider, SectionDraft
from .heuristic import HeuristicProvider
from .openai_compat import LLMError, OpenAICompatProvider, with_fallback

__all__ = [
    "AnswerDraft",
    "BulletDraft",
    "NoteProvider",
    "SectionDraft",
    "HeuristicProvider",
    "OpenAICompatProvider",
    "LLMError",
    "with_fallback",
    "get_provider",
]


def get_provider(name: str = "") -> NoteProvider:
    name = (name or os.environ.get("LNOTE_PROVIDER", "heuristic")).lower()
    if name == "openai":
        provider = OpenAICompatProvider(
            base_url=os.environ.get("LNOTE_LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.environ.get("LNOTE_LLM_API_KEY", "ollama"),
            model=os.environ.get("LNOTE_LLM_MODEL", "llama3.1"),
        )
        return with_fallback(provider)  # type: ignore[return-value]
    return HeuristicProvider()
