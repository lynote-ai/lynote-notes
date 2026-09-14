import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lynote_notes import Workspace  # noqa: E402

SAMPLE_TEXT = """Lynote Notes is a source-grounded note taker. Every bullet keeps a citation
back to the exact chunk it came from.

The project is MIT licensed and works offline by default. It supports PDF,
DOCX, web pages, YouTube captions and media transcripts.

How does retrieval work? It uses a small BM25 implementation with no
third-party dependencies.

The roadmap includes embeddings, a web UI and Anki export improvements.
"""


@pytest.fixture()
def workspace(tmp_path):
    ws = Workspace(tmp_path / "ws")
    yield ws
    ws.close()


@pytest.fixture()
def sample_file(tmp_path):
    path = tmp_path / "sample.md"
    path.write_text(SAMPLE_TEXT, encoding="utf-8")
    return path


@pytest.fixture()
def sample_text():
    return SAMPLE_TEXT
