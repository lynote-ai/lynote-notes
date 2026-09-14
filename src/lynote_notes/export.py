"""Exporters: Markdown (reading) and Anki TSV (memorising)."""

from __future__ import annotations

from typing import Dict, List

from .models import Answer, Note, Source

ANKI_HEADER = "#separator:tab\n#html:false\n#tags column:3"


def note_to_markdown(note: Note, sources: Dict[str, Source] = None) -> str:
    sources = sources or {}
    lines: List[str] = [f"# {note.title}", ""]
    for source_id in note.source_ids:
        source = sources.get(source_id)
        if source:
            lines.append(f"> Source: {source.title} ({source.origin})")
    if note.source_ids:
        lines.append("")

    reference_ids: List[str] = []
    for section in note.sections:
        lines.append(f"## {section.heading}")
        lines.append("")
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        if section.citations:
            lines.append("")
            refs = []
            for citation in section.citations:
                if citation.chunk_id not in reference_ids:
                    reference_ids.append(citation.chunk_id)
                refs.append(str(reference_ids.index(citation.chunk_id) + 1))
            lines.append(f"  _Sources: {', '.join('[' + r + ']' for r in refs)}_")
        lines.append("")

    citation_by_chunk = {
        citation.chunk_id: citation
        for section in note.sections
        for citation in section.citations
    }
    if reference_ids:
        lines.append("## References")
        lines.append("")
        for index, chunk_id in enumerate(reference_ids, start=1):
            citation = citation_by_chunk[chunk_id]
            lines.append(
                f"{index}. **{citation.source_title}** · {citation.locator} — {citation.snippet}"
            )
    return "\n".join(lines).strip() + "\n"


def note_to_anki_tsv(note: Note) -> str:
    """TSV importable by Anki (File > Import)."""
    rows = [ANKI_HEADER]
    for section in note.sections:
        for bullet, citation in zip(section.bullets, _bullets_to_citations(section)):
            front = _tsv_escape(bullet)
            back = _tsv_escape(f"Source: {citation.source_title} ({citation.locator})\n\n{citation.snippet}")
            rows.append(f"{front}\t{back}\tlynote::{section.heading.lower().replace(' ', '-')}")
    return "\n".join(rows) + "\n"


def _bullets_to_citations(section):
    """Pair bullets with citations, repeating the section citation list as needed."""
    citations = section.citations or []
    if not citations:
        return [None] * len(section.bullets)
    if len(citations) == len(section.bullets):
        return citations
    # Sections cite fewer chunks than bullets; cycle through what we have.
    return [citations[i % len(citations)] for i in range(len(section.bullets))]


def _tsv_escape(text: str) -> str:
    return text.replace("\t", " ").replace("\n", " ")


def format_answer(answer: Answer) -> str:
    lines = [answer.text, ""]
    for index, citation in enumerate(answer.citations, start=1):
        lines.append(f"[{index}] {citation.source_title} · {citation.locator} — {citation.snippet}")
    return "\n".join(lines).strip() + "\n"
