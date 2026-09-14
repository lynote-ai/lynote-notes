import pytest

from lynote_notes.ingest import detect_kind, ingest
from lynote_notes.ingest.base import OptionalDependencyError
from lynote_notes.ingest.web import html_to_text, ingest_web
from lynote_notes.ingest.youtube import parse_vtt

VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
Welcome to the lecture.

00:00:04.500 --> 00:00:08.000
<c>Today we cover source-grounded notes.</c>

00:00:08.000 --> 00:00:12.000
And why citations matter.
"""


def test_detect_kind():
    assert detect_kind("notes.md") == "text"
    assert detect_kind("paper.pdf") == "pdf"
    assert detect_kind("report.docx") == "docx"
    assert detect_kind("talk.mp3") == "audio"
    assert detect_kind("demo.mp4") == "video"
    assert detect_kind("https://youtu.be/abc123") == "youtube"
    assert detect_kind("https://example.com/post") == "web"


def test_ingest_text_file(sample_file):
    result = ingest(str(sample_file))
    assert result.title == "sample"
    assert "source-grounded" in result.blocks[0]["text"]


def test_ingest_unknown_kind_raises(sample_file):
    with pytest.raises(ValueError):
        ingest(str(sample_file), kind="banana")


def test_html_to_text_extracts_title_and_drops_scripts():
    html = """
    <html><head><title>Hello Page</title>
    <script>var x = 1;</script><style>.a{}</style></head>
    <body><h1>Heading</h1><p>First paragraph.</p><p>Second paragraph.</p>
    <nav>Navigation noise</nav></body></html>
    """
    title, text = html_to_text(html)
    assert title == "Hello Page"
    assert "First paragraph." in text
    assert "Second paragraph." in text
    assert "var x" not in text
    assert "Navigation noise" not in text


def test_ingest_web_uses_injected_fetch():
    html = "<html><head><title>Doc</title></head><body><p>Body text.</p></body></html>"
    result = ingest_web("https://example.com", fetch=lambda url: html)
    assert result.title == "Doc"
    assert "Body text." in result.blocks[0]["text"]


def test_parse_vtt_with_timestamps():
    blocks = parse_vtt(VTT)
    assert len(blocks) == 3
    assert blocks[0]["text"] == "Welcome to the lecture."
    assert blocks[0]["start_ts"] == 1.0
    assert blocks[1]["text"] == "Today we cover source-grounded notes."
    assert blocks[2]["end_ts"] == 12.0


def _missing(package: str) -> bool:
    try:
        __import__(package)
        return False
    except ImportError:
        return True


@pytest.mark.skipif(not _missing("pypdf"), reason="pypdf installed")
def test_pdf_without_extra_gives_helpful_error(tmp_path):
    path = tmp_path / "file.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    with pytest.raises(OptionalDependencyError) as excinfo:
        ingest(str(path))
    assert "lynote-notes[pdf]" in str(excinfo.value)
