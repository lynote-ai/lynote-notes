"""Paragraph-aware chunking with overlap.

Chunks are the unit of retrieval and citation, so they aim to be
self-contained: split on blank lines first, then on sentence boundaries when a
paragraph is too long, and carry a small overlap so answers are not cut in
half.
"""

from __future__ import annotations

import re
from typing import List

from .models import Chunk
from .store import new_id

_SENTENCE_SPLIT = re.compile(r"(?:(?<=[。！？；])\s*|(?<=[.!?;])\s+)")
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*")
_MD_BULLET = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+")
_MD_QUOTE = re.compile(r"^\s{0,3}>\s?")
_SOFT_WRAP = re.compile(r"(?<!\n)\n(?!\n)")


def normalize_text(text: str) -> str:
    """Strip Markdown noise and join soft-wrapped lines for sentence splitting.

    Stored chunks keep the original text; normalisation only affects how
    sentences are extracted for notes and answers.
    """
    lines = []
    for line in text.splitlines():
        line = _MD_HEADING.sub("", line)
        line = _MD_BULLET.sub("", line)
        line = _MD_QUOTE.sub("", line)
        lines.append(line.rstrip())
    return _SOFT_WRAP.sub(" ", "\n".join(lines)).strip()


def split_sentences(text: str) -> List[str]:
    """Split into sentences, treating paragraph breaks as boundaries."""
    normalized = normalize_text(text)
    out: List[str] = []
    for paragraph in re.split(r"\n\s*\n", normalized):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        out.extend(p.strip() for p in _SENTENCE_SPLIT.split(paragraph) if p.strip())
    return out


def _hard_split(text: str, max_chars: int) -> List[str]:
    """Last-resort split on word boundaries for unpunctuated text."""
    out: List[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            out.append(current)
            current = word
        else:
            current = candidate
    if current:
        out.append(current)
    if not out:  # single token longer than max_chars
        out = [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
    return out


def _split_long(text: str, max_chars: int) -> List[str]:
    """Split an oversized paragraph on sentence boundaries, then words."""
    out: List[str] = []
    for sentence in split_sentences(text):
        if len(sentence) > max_chars:
            out.extend(_hard_split(sentence, max_chars))
        else:
            out.append(sentence)
    return out


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping, paragraph-aware chunks."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be >= 0 and < max_chars")

    paragraphs: List[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if len(block) <= max_chars:
            paragraphs.append(block)
        else:
            paragraphs.extend(_split_long(block, max_chars))

    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if current and len(candidate) > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            if tail and len(tail) + len(paragraph) + 2 <= max_chars:
                current = f"{tail}\n\n{paragraph}".strip()
            else:
                current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def build_chunks(
    source_id: str,
    blocks: List[dict],
    max_chars: int = 800,
    overlap: int = 100,
) -> List[Chunk]:
    """Turn ingest blocks into persisted-ready chunks.

    ``blocks`` items look like ``{"text": str, "start_ts": float|None,
    "end_ts": float|None}`` — timestamps only appear for media sources.
    """
    chunks: List[Chunk] = []
    seq = 0
    for block in blocks:
        text = (block.get("text") or "").strip()
        if not text:
            continue
        for piece in chunk_text(text, max_chars=max_chars, overlap=overlap):
            chunks.append(
                Chunk(
                    id=new_id("ck"),
                    source_id=source_id,
                    seq=seq,
                    text=piece,
                    start_ts=block.get("start_ts"),
                    end_ts=block.get("end_ts"),
                )
            )
            seq += 1
    return chunks
