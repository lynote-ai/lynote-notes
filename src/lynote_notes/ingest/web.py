"""Web page ingestion: fetch + readable-text extraction, stdlib only.

The HTML parser is intentionally simple: it drops script/style/nav noise and
keeps visible text plus headings, which is what note generation needs. The
``fetch`` hook makes it testable without network access.
"""

from __future__ import annotations

import urllib.request
from html.parser import HTMLParser
from typing import Callable, List, Optional
from urllib.parse import urlparse

from .base import IngestResult

_SKIP = {"script", "style", "noscript", "template", "svg", "nav", "footer", "header", "form"}
_BLOCK = {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.title = ""
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in _SKIP:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag in _SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._in_title:
            self.title += data.strip()
        elif not self._skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> tuple:
    """Return (title, text) for an HTML document."""
    parser = _TextExtractor()
    parser.feed(html)
    lines = [line.strip() for line in "".join(parser.parts).splitlines()]
    text = "\n".join(line for line in lines if line)
    return parser.title.strip(), text


def fetch_url(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "lynote-notes/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (user-supplied URL is the point)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def ingest_web(url: str, fetch: Optional[Callable[[str], str]] = None) -> IngestResult:
    html = (fetch or fetch_url)(url)
    title, text = html_to_text(html)
    if not title:
        title = urlparse(url).netloc or url
    return IngestResult(title=title, blocks=[{"text": text}], meta={"url": url})
