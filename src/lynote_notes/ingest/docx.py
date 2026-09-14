"""DOCX ingestion via python-docx (optional extra)."""

from __future__ import annotations

from pathlib import Path

from .base import IngestResult, OptionalDependencyError


def ingest_docx(path: str) -> IngestResult:
    try:
        import docx  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise OptionalDependencyError("DOCX ingestion", "python-docx", "docx") from exc

    p = Path(path)
    document = docx.Document(str(p))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    return IngestResult(title=p.stem, blocks=[{"text": text}], meta={"path": str(p)})
