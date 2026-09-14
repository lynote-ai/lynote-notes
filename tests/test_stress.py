"""Stress and robustness checks: large inputs, unicode, timing sanity."""

import time

from lynote_notes import Workspace


def _big_document(paragraphs: int = 300) -> str:
    return "\n\n".join(
        f"Section {i} explains topic {i}. The key metric for topic {i} is {i * 7} percent, "
        f"and the recommended action is to review item {i} before publishing."
        for i in range(paragraphs)
    )


def test_large_document_pipeline(tmp_path):
    text = _big_document()
    with Workspace(tmp_path / "ws") as ws:
        source = ws.add_text(text, "Large doc")
        chunks = ws.store.get_chunks([source.id])
        assert len(chunks) > 40

        started = time.time()
        note = ws.make_note("Large summary")
        elapsed = time.time() - started
        assert elapsed < 10.0, f"note generation too slow: {elapsed:.2f}s"
        assert note.sections

        chunk_ids = {c.id for c in chunks}
        for section in note.sections:
            for citation in section.citations:
                assert citation.chunk_id in chunk_ids

        answer = ws.ask("What is the key metric for topic 42?")
        assert "294" in answer.text  # 42 * 7
        assert answer.citations


def test_chinese_document_end_to_end(tmp_path):
    text = (
        "第一段：Lynote Notes 是一个可溯源的笔记工具，每个要点都会引用原文片段。\n\n"
        "第二段：检索使用 BM25 算法，支持中文单字和双字分词，无需下载模型。\n\n"
        "第三段：导出支持 Markdown 和 Anki，方便复习和记忆。"
    )
    with Workspace(tmp_path / "ws") as ws:
        ws.add_text(text, "中文说明")
        note = ws.make_note("中文笔记")
        assert note.sections
        answer = ws.ask("检索使用什么算法？")
        assert "BM25" in answer.text


def test_unicode_and_emoji_roundtrip(tmp_path):
    text = "Note with emoji 🚀 and accents: café, naïve. Numbers: 1,234.56."
    with Workspace(tmp_path / "ws") as ws:
        ws.add_text(text, "Unicode")
        answer = ws.ask("emoji")
        assert "🚀" in answer.text


def test_many_sources_retrieval(tmp_path):
    with Workspace(tmp_path / "ws") as ws:
        for i in range(30):
            ws.add_text(f"Source {i} discusses subject {i} in detail.", f"Source {i}")
        answer = ws.ask("subject 17")
        assert answer.text
        assert answer.citations[0].source_title == "Source 17"


def test_empty_and_whitespace_inputs(tmp_path):
    with Workspace(tmp_path / "ws") as ws:
        ws.add_text("   \n\n   ", "Blank")
        assert ws.store.get_chunks() == []
        note = ws.make_note("Empty note")
        assert note.sections == []
        answer = ws.ask("anything")
        assert "No relevant material" in answer.text
