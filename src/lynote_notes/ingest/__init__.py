"""Ingest registry: one entry point for files and URLs."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from .base import IngestResult, OptionalDependencyError

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".csv"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}


def detect_kind(path_or_url: str) -> str:
    parsed = urlparse(path_or_url)
    if parsed.scheme in ("http", "https"):
        return "youtube" if parsed.netloc.lower() in YOUTUBE_HOSTS else "web"
    ext = os.path.splitext(parsed.path or path_or_url)[1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "text"


def ingest(path_or_url: str, kind: str = "") -> IngestResult:
    """Ingest a local file or URL into blocks.

    Optional backends (pdf/docx/youtube/media) are imported lazily and raise a
    helpful :class:`OptionalDependencyError` when their extra is missing.
    """
    kind = kind or detect_kind(path_or_url)
    if kind == "text":
        from .text import ingest_text

        return ingest_text(path_or_url)
    if kind == "pdf":
        from .pdf import ingest_pdf

        return ingest_pdf(path_or_url)
    if kind == "docx":
        from .docx import ingest_docx

        return ingest_docx(path_or_url)
    if kind == "web":
        from .web import ingest_web

        return ingest_web(path_or_url)
    if kind == "youtube":
        from .youtube import ingest_youtube

        return ingest_youtube(path_or_url)
    if kind in ("audio", "video"):
        from .media import transcribe

        return transcribe(path_or_url)
    raise ValueError(f"Unsupported source kind: {kind}")


__all__ = [
    "IngestResult",
    "OptionalDependencyError",
    "detect_kind",
    "ingest",
]
