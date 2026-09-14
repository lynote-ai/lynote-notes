"""YouTube ingestion via yt-dlp captions (optional extra).

Prefers human captions, falls back to auto-generated ones, and parses the
WebVTT track into timestamped blocks. The VTT parser is a pure function so it
can be tested without network access.
"""

from __future__ import annotations

import re
import urllib.request
from typing import Dict, List, Optional

from .base import IngestResult, OptionalDependencyError

_TS = re.compile(
    r"^(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})\s+-->\s+(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})"
)
_TAG = re.compile(r"<[^>]+>")


def _to_seconds(hours: Optional[str], minutes: str, seconds: str, millis: str) -> float:
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000.0


def parse_vtt(vtt: str) -> List[dict]:
    """Parse WebVTT into ``{"text", "start_ts", "end_ts"}`` blocks."""
    blocks: List[dict] = []
    current: Optional[dict] = None
    for raw_line in vtt.splitlines():
        line = raw_line.strip()
        match = _TS.match(line)
        if match:
            current = {
                "text": "",
                "start_ts": _to_seconds(*match.groups()[:4]),
                "end_ts": _to_seconds(*match.groups()[4:]),
            }
            continue
        if not line or line.upper().startswith(("WEBVTT", "NOTE", "KIND:", "LANGUAGE:")):
            continue
        if current is not None and not line.isdigit():
            text = _TAG.sub("", line).strip()
            if text:
                current["text"] = f"{current['text']} {text}".strip()
                blocks.append(current)
                current = None
    # Merge blocks that are adjacent and belong to the same cue run.
    merged: List[dict] = []
    for block in blocks:
        if merged and block["text"] == merged[-1]["text"]:
            merged[-1]["end_ts"] = block["end_ts"]
        else:
            merged.append(block)
    return merged


def _pick_caption(info: dict) -> Optional[Dict[str, object]]:
    for field in ("subtitles", "automatic_captions"):
        tracks = info.get(field) or {}
        for lang in ("en", "zh-Hans", "zh-CN", "zh", "en-US"):
            if lang in tracks:
                for track in tracks[lang]:
                    if track.get("ext") == "vtt":
                        return track
        for track_list in tracks.values():
            for track in track_list:
                if track.get("ext") == "vtt":
                    return track
    return None


def ingest_youtube(url: str, language: str = "") -> IngestResult:
    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise OptionalDependencyError("YouTube ingestion", "yt-dlp", "youtube") from exc

    opts = {"skip_download": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    track = _pick_caption(info)
    if not track:
        raise RuntimeError(
            "No captions found for this video. Install the 'media' extra and ingest "
            "the downloaded audio/video file to transcribe it instead."
        )
    req = urllib.request.Request(str(track["url"]), headers={"User-Agent": "lynote-notes/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        vtt = resp.read().decode("utf-8", errors="replace")
    blocks = parse_vtt(vtt)
    return IngestResult(
        title=info.get("title") or url,
        blocks=blocks,
        meta={"url": url, "channel": str(info.get("uploader") or "")},
    )
