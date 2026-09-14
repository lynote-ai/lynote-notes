"""LLM provider interface.

Providers are deliberately small: they turn chunks into *drafts* that carry
chunk ids. The citation layer (see ``notes.py`` / ``qa.py``) resolves those ids
into human-readable citations, so every provider — including the offline
heuristic one — produces traceable output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol, Sequence

from ..models import Chunk


@dataclass
class BulletDraft:
    text: str
    chunk_id: str


@dataclass
class SectionDraft:
    heading: str
    bullets: List[BulletDraft] = field(default_factory=list)


@dataclass
class AnswerDraft:
    text: str
    chunk_ids: List[str] = field(default_factory=list)


class NoteProvider(Protocol):
    name: str

    def summarize(self, title: str, chunks: Sequence[Chunk]) -> List[SectionDraft]:
        ...

    def answer(self, question: str, chunks: Sequence[Chunk]) -> AnswerDraft:
        ...
