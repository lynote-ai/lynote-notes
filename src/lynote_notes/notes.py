"""Note building: provider drafts -> cited, storable notes."""

from __future__ import annotations

from typing import Dict, List, Sequence

from .llm.base import NoteProvider
from .models import Chunk, Citation, Note, Section, format_timestamp
from .store import Store, new_id, utcnow


def make_citation(chunk: Chunk, source_title: str) -> Citation:
    locator = format_timestamp(chunk.start_ts) if chunk.start_ts is not None else f"chunk {chunk.seq + 1}"
    snippet = chunk.text.strip().replace("\n", " ")
    if len(snippet) > 140:
        snippet = snippet[:137] + "..."
    return Citation(
        chunk_id=chunk.id,
        source_id=chunk.source_id,
        source_title=source_title,
        locator=locator,
        snippet=snippet,
    )


def build_note(
    provider: NoteProvider,
    title: str,
    chunks: Sequence[Chunk],
    store: Store,
) -> Note:
    """Generate a note and resolve every bullet to a real citation."""
    chunks = list(chunks)
    chunk_by_id: Dict[str, Chunk] = {c.id: c for c in chunks}
    source_titles: Dict[str, str] = {}
    for source in store.list_sources():
        source_titles[source.id] = source.title

    sections: List[Section] = []
    for draft in provider.summarize(title, chunks):
        bullets: List[str] = []
        citations: List[Citation] = []
        seen_chunks = set()
        for bullet in draft.bullets:
            chunk = chunk_by_id.get(bullet.chunk_id)
            if chunk is None:
                continue
            bullets.append(bullet.text)
            if chunk.id not in seen_chunks:
                citations.append(make_citation(chunk, source_titles.get(chunk.source_id, chunk.source_id)))
                seen_chunks.add(chunk.id)
        if bullets:
            sections.append(Section(heading=draft.heading, bullets=bullets, citations=citations))

    return Note(
        id=new_id("note"),
        title=title,
        sections=sections,
        created_at=utcnow(),
        source_ids=sorted({c.source_id for c in chunks}),
    )
