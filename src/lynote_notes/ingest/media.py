"""Audio/video ingestion via faster-whisper (optional extra)."""

from __future__ import annotations

from pathlib import Path

from .base import IngestResult, OptionalDependencyError


def transcribe(path: str, model_size: str = "base", language: str = "") -> IngestResult:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise OptionalDependencyError("Audio/video transcription", "faster-whisper", "media") from exc

    p = Path(path)
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, info = model.transcribe(str(p), language=language or None)
    blocks = [
        {
            "text": segment.text.strip(),
            "start_ts": float(segment.start),
            "end_ts": float(segment.end),
        }
        for segment in segments
        if segment.text.strip()
    ]
    return IngestResult(
        title=p.stem,
        blocks=blocks,
        meta={"path": str(p), "language": getattr(info, "language", "") or ""},
    )
