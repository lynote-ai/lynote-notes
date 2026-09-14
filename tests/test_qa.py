from lynote_notes.llm.heuristic import HeuristicProvider
from lynote_notes.qa import NO_MATERIAL, answer_question


def test_answer_is_grounded_and_cited(workspace, sample_text):
    workspace.add_text(sample_text, "Design notes")
    answer = answer_question(HeuristicProvider(), workspace.store, "What license is the project under?")
    assert "MIT" in answer.text
    assert answer.citations
    assert answer.citations[0].source_title == "Design notes"


def test_answer_returns_placeholder_when_nothing_matches(workspace, sample_text):
    workspace.add_text(sample_text, "Design notes")
    answer = answer_question(HeuristicProvider(), workspace.store, "zzzqqq unrelated gibberish")
    assert answer.text == NO_MATERIAL
    assert answer.citations == []


def test_answer_can_limit_sources(workspace, sample_text):
    first = workspace.add_text(sample_text, "Design notes")
    workspace.add_text("The pricing is ten dollars per seat.", "Pricing")
    answer = answer_question(HeuristicProvider(), workspace.store, "pricing per seat", [first.id])
    assert "ten dollars" not in answer.text


def test_answer_chinese_query(workspace):
    workspace.add_text("该项目的许可证是 MIT，支持离线使用。检索使用 BM25 算法。", "中文说明")
    answer = answer_question(HeuristicProvider(), workspace.store, "许可证是什么？")
    assert "MIT" in answer.text
    assert answer.citations
