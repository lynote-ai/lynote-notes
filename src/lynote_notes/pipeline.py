"""Workspace: the one object that ties ingest, notes, Q&A and export together."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .chunking import build_chunks
from .export import note_to_anki_tsv, note_to_markdown
from .ingest import detect_kind, ingest
from .llm import get_provider
from .llm.base import NoteProvider
from .models import Answer, Note, Source
from .notes import build_note
from .qa import answer_question
from .store import Store

DEFAULT_ROOT = "lynote-workspace"


class Workspace:
    def __init__(
        self,
        root: str = DEFAULT_ROOT,
        provider: Optional[NoteProvider] = None,
        max_chars: int = 800,
        overlap: int = 100,
    ) -> None:
        self.root = Path(root)
        self.store = Store(self.root / "workspace.db")
        self.provider = provider or get_provider()
        self.max_chars = max_chars
        self.overlap = overlap

    # -- ingest ------------------------------------------------------------
    def add(self, path_or_url: str, title: str = "", kind: str = "") -> Source:
        kind = kind or detect_kind(path_or_url)
        result = ingest(path_or_url, kind)
        source = self.store.add_source(
            title=title or result.title,
            kind=kind,
            origin=path_or_url,
            meta=result.meta,
        )
        chunks = build_chunks(source.id, result.blocks, self.max_chars, self.overlap)
        self.store.add_chunks(chunks)
        return source

    def add_text(self, text: str, title: str, kind: str = "text", origin: str = "inline") -> Source:
        source = self.store.add_source(title=title, kind=kind, origin=origin)
        chunks = build_chunks(source.id, [{"text": text}], self.max_chars, self.overlap)
        self.store.add_chunks(chunks)
        return source

    # -- notes -------------------------------------------------------------
    def make_note(self, title: str, source_ids: Optional[Sequence[str]] = None) -> Note:
        chunks = self.store.get_chunks(list(source_ids) if source_ids else None)
        note = build_note(self.provider, title, chunks, self.store)
        self.store.save_note(note)
        return note

    # -- Q&A ---------------------------------------------------------------
    def ask(self, question: str, source_ids: Optional[Sequence[str]] = None, top_k: int = 4) -> Answer:
        return answer_question(self.provider, self.store, question, source_ids, top_k)

    # -- export ------------------------------------------------------------
    def export_note(self, note: Note, fmt: str = "md", out: str = "") -> str:
        sources: Dict[str, Source] = {s.id: s for s in self.store.list_sources()}
        if fmt == "md":
            content = note_to_markdown(note, sources)
        elif fmt == "anki":
            content = note_to_anki_tsv(note)
        else:
            raise ValueError(f"Unknown export format: {fmt}")
        if out:
            Path(out).write_text(content, encoding="utf-8")
        return content

    def list_sources(self) -> List[Source]:
        return self.store.list_sources()

    def list_notes(self) -> List[Note]:
        return self.store.list_notes()

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
