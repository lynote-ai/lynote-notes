"""Core data model for Lynote Notes.

Everything that flows through the pipeline (ingest -> chunk -> note -> ask ->
export) is expressed with these small dataclasses so the core stays storage-
and provider-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Source:
    """A single ingested input: a file, a URL, a recording."""

    id: str
    title: str
    kind: str  # text | pdf | docx | web | youtube | audio | video
    origin: str  # local path or URL
    created_at: str
    meta: Dict[str, str] = field(default_factory=dict)


@dataclass
class Chunk:
    """A retrievable slice of a source, with optional media timestamps."""

    id: str
    source_id: str
    seq: int
    text: str
    start_ts: Optional[float] = None
    end_ts: Optional[float] = None
    meta: Dict[str, str] = field(default_factory=dict)


@dataclass
class Citation:
    """A pointer back to the exact source material behind a claim."""

    chunk_id: str
    source_id: str
    source_title: str
    locator: str  # human-readable, e.g. "chunk 4" or "00:12:30"
    snippet: str


@dataclass
class Section:
    heading: str
    bullets: List[str]
    citations: List[Citation] = field(default_factory=list)


@dataclass
class Note:
    id: str
    title: str
    sections: List[Section]
    created_at: str
    source_ids: List[str] = field(default_factory=list)


@dataclass
class Answer:
    question: str
    text: str
    citations: List[Citation] = field(default_factory=list)


def format_timestamp(seconds: Optional[float]) -> str:
    """Render seconds as HH:MM:SS (or MM:SS below one hour)."""
    if seconds is None:
        return ""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
