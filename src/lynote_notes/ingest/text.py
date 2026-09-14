"""Plain text and Markdown ingestion."""

from __future__ import annotations

from pathlib import Path

from .base import IngestResult


def ingest_text(path: str) -> IngestResult:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return IngestResult(title=p.stem, blocks=[{"text": text}], meta={"path": str(p)})
