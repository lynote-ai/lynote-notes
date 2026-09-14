from lynote_notes.llm.heuristic import HeuristicProvider
from lynote_notes.models import Chunk
from lynote_notes.notes import build_note, make_citation


def test_make_citation_uses_timestamp_for_media():
    chunk = Chunk(id="ck_1", source_id="src_1", seq=3, text="hello world", start_ts=754.0)
    citation = make_citation(chunk, "Interview")
    assert citation.locator == "12:34"
    assert citation.source_title == "Interview"


def test_make_citation_uses_chunk_number_for_text():
    chunk = Chunk(id="ck_2", source_id="src_1", seq=4, text="hello world")
    assert make_citation(chunk, "Doc").locator == "chunk 5"


def test_build_note_produces_cited_sections(workspace, sample_text):
    workspace.add_text(sample_text, "Design notes")
    chunks = workspace.store.get_chunks()
    note = build_note(HeuristicProvider(), "Summary", chunks, workspace.store)

    headings = [s.heading for s in note.sections]
    assert headings[:2] == ["Overview", "Key points"]
    assert "Open questions" in headings

    chunk_ids = {c.id for c in chunks}
    for section in note.sections:
        assert section.bullets
        assert section.citations
        assert all(citation.chunk_id in chunk_ids for citation in section.citations)


def test_overview_keeps_reading_order(workspace, sample_text):
    workspace.add_text(sample_text, "Design notes")
    chunks = workspace.store.get_chunks()
    note = build_note(HeuristicProvider(), "Summary", chunks, workspace.store)
    overview = next(s for s in note.sections if s.heading == "Overview")
    assert overview.bullets[0].startswith("Lynote Notes is a source-grounded")


def test_sections_do_not_repeat_bullets(workspace, sample_text):
    workspace.add_text(sample_text, "Design notes")
    chunks = workspace.store.get_chunks()
    note = build_note(HeuristicProvider(), "Summary", chunks, workspace.store)
    all_bullets = [b for s in note.sections for b in s.bullets]
    assert len(all_bullets) == len(set(all_bullets))


def test_empty_chunks_produce_empty_note(workspace):
    note = build_note(HeuristicProvider(), "Nothing", [], workspace.store)
    assert note.sections == []
