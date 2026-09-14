import pytest

from lynote_notes.chunking import build_chunks, chunk_text, normalize_text, split_sentences


def test_split_sentences_handles_english_and_chinese():
    text = "First sentence. Second sentence! 第三句。第四句？"
    sentences = split_sentences(text)
    assert len(sentences) == 4
    assert sentences[0] == "First sentence."
    assert sentences[-1] == "第四句？"


def test_split_sentences_separates_headings_and_joins_wrapped_lines():
    text = "## Why it matters\n\nA summariser that never looks\nanything up will invent details.\n\nNext paragraph."
    sentences = split_sentences(text)
    assert sentences[0] == "Why it matters"
    assert sentences[1] == "A summariser that never looks anything up will invent details."
    assert sentences[2] == "Next paragraph."


def test_normalize_text_strips_markdown_markers():
    text = "# Title\n\n- item one\n> quoted\n1. numbered"
    normalized = normalize_text(text)
    assert normalized == "Title\n\nitem one quoted numbered"


def test_chunk_text_respects_max_chars():
    paragraph = "word " * 300
    chunks = chunk_text(paragraph, max_chars=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 400 + 60 for chunk in chunks)


def test_chunk_text_keeps_paragraphs_together():
    text = "Short paragraph one.\n\nShort paragraph two."
    chunks = chunk_text(text, max_chars=200, overlap=20)
    assert chunks == ["Short paragraph one.\n\nShort paragraph two."]


def test_chunk_text_validates_arguments():
    with pytest.raises(ValueError):
        chunk_text("text", max_chars=0)
    with pytest.raises(ValueError):
        chunk_text("text", max_chars=100, overlap=100)


def test_build_chunks_assigns_sequence_and_timestamps():
    blocks = [
        {"text": "First block of text.", "start_ts": 0.0, "end_ts": 3.5},
        {"text": "Second block of text.", "start_ts": 3.5, "end_ts": 7.0},
    ]
    chunks = build_chunks("src_1", blocks, max_chars=200, overlap=20)
    assert [c.seq for c in chunks] == [0, 1]
    assert chunks[0].start_ts == 0.0
    assert chunks[1].end_ts == 7.0
    assert all(c.source_id == "src_1" for c in chunks)


def test_build_chunks_skips_empty_blocks():
    chunks = build_chunks("src_1", [{"text": "   "}, {"text": "Real text."}])
    assert len(chunks) == 1
    assert chunks[0].text == "Real text."
