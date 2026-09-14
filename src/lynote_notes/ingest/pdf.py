"""PDF ingestion via pypdf (optional extra)."""

from __future__ import annotations

from pathlib import Path

from .base import IngestResult, OptionalDependencyError


def ingest_pdf(path: str) -> IngestResult:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise OptionalDependencyError("PDF ingestion", "pypdf", "pdf") from exc

    p = Path(path)
    reader = PdfReader(str(p))
    blocks = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            blocks.append({"text": text, "meta": {"page": str(page_number)}})
    return IngestResult(title=p.stem, blocks=blocks, meta={"path": str(p), "pages": str(len(reader.pages))})
