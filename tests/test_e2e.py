"""End-to-end: ingest -> note -> ask -> export, across two sources."""

from pathlib import Path

from lynote_notes import Workspace


def test_full_workflow(tmp_path, sample_file):
    with Workspace(tmp_path / "ws") as ws:
        first = ws.add(str(sample_file), title="Design notes")
        second = ws.add_text(
            "Interview notes: the team wants a web UI next quarter. "
            "Embeddings are planned after the MVP. The budget is twenty thousand dollars.",
            "Interview",
        )

        note = ws.make_note("Research summary")
        assert note.source_ids == sorted([first.id, second.id])
        headings = [section.heading for section in note.sections]
        assert "Overview" in headings
        assert "Key points" in headings

        answer = ws.ask("What is planned next quarter?")
        assert "web UI" in answer.text
        assert answer.citations
        assert answer.citations[0].source_title == "Interview"

        markdown = ws.export_note(note, "md")
        assert "# Research summary" in markdown
        assert "## References" in markdown

        tsv = ws.export_note(note, "anki")
        assert tsv.startswith("#separator:tab")

        # persisted across sessions
        reopened = Workspace(tmp_path / "ws")
        try:
            assert [s.id for s in reopened.list_sources()] == [first.id, second.id]
            assert reopened.store.get_note(note.id) is not None
        finally:
            reopened.close()


def test_workspace_export_to_file(tmp_path, sample_file):
    with Workspace(tmp_path / "ws") as ws:
        ws.add(str(sample_file))
        note = ws.make_note("Summary")
        out = Path(tmp_path / "note.md")
        ws.export_note(note, "md", out=str(out))
        assert out.read_text(encoding="utf-8").startswith("# Summary")
