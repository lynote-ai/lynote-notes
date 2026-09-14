"""Source-grounded Q&A: retrieve, answer, cite."""

from __future__ import annotations

from typing import List, Optional, Sequence

from .llm.base import NoteProvider
from .models import Answer, Chunk
from .notes import make_citation
from .retrieval import retrieve
from .store import Store

NO_MATERIAL = "No relevant material found in this workspace for that question."


def answer_question(
    provider: NoteProvider,
    store: Store,
    question: str,
    source_ids: Optional[Sequence[str]] = None,
    top_k: int = 4,
) -> Answer:
    chunks = store.get_chunks(list(source_ids) if source_ids else None)
    hits = retrieve(question, chunks, top_k=top_k)
    if not hits:
        return Answer(question=question, text=NO_MATERIAL, citations=[])

    context = [chunk for chunk, _ in hits]
    draft = provider.answer(question, context)

    chunk_by_id = {chunk.id: chunk for chunk in context}
    cited_ids = [cid for cid in draft.chunk_ids if cid in chunk_by_id]
    if not cited_ids:
        cited_ids = [chunk.id for chunk in context[:2]]

    source_titles = {source.id: source.title for source in store.list_sources()}
    citations = []
    seen = set()
    for chunk_id in cited_ids:
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        chunk = chunk_by_id[chunk_id]
        citations.append(make_citation(chunk, source_titles.get(chunk.source_id, chunk.source_id)))

    text = draft.text or context[0].text.strip()
    return Answer(question=question, text=text, citations=citations)
