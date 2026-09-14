from lynote_notes.export import ANKI_HEADER, format_answer, note_to_anki_tsv, note_to_markdown
from lynote_notes.models import Answer, Citation, Note, Section


def make_note():
    citation = Citation(
        chunk_id="ck_1",
        source_id="src_1",
        source_title="Design notes",
        locator="chunk 1",
        snippet="The project is MIT licensed.",
    )
    return Note(
        id="note_1",
        title="Summary",
        created_at="2026-01-01T00:00:00+00:00",
        source_ids=["src_1"],
        sections=[Section(heading="Key points", bullets=["It is MIT licensed."], citations=[citation])],
    )


def test_markdown_export_contains_sections_and_references():
    from lynote_notes.models import Source

    sources = {"src_1": Source(id="src_1", title="Design notes", kind="text", origin="notes.md", created_at="x")}
    markdown = note_to_markdown(make_note(), sources)
    assert "# Summary" in markdown
    assert "## Key points" in markdown
    assert "- It is MIT licensed." in markdown
    assert "## References" in markdown
    assert "Design notes" in markdown
    assert "[1]" in markdown


def test_anki_export_is_tab_separated():
    tsv = note_to_anki_tsv(make_note())
    lines = tsv.strip().splitlines()
    assert lines[0] == ANKI_HEADER.splitlines()[0]
    assert lines[-1].count("\t") == 2
    assert lines[-1].split("\t")[0] == "It is MIT licensed."


def test_format_answer_lists_citations():
    answer = Answer(
        question="q",
        text="The answer.",
        citations=[Citation(chunk_id="ck_1", source_id="s", source_title="Doc", locator="chunk 1", snippet="snip")],
    )
    rendered = format_answer(answer)
    assert "The answer." in rendered
    assert "[1] Doc · chunk 1" in rendered
