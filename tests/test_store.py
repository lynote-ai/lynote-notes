from lynote_notes.models import Chunk, Citation, Note, Section
from lynote_notes.store import Store


def test_source_roundtrip(tmp_path):
    store = Store(tmp_path / "ws.db")
    source = store.add_source("My doc", "text", "my-doc.md", meta={"path": "my-doc.md"})
    fetched = store.get_source(source.id)
    assert fetched is not None
    assert fetched.title == "My doc"
    assert fetched.meta["path"] == "my-doc.md"
    assert [s.id for s in store.list_sources()] == [source.id]
    store.close()


def test_chunks_by_source(tmp_path):
    store = Store(tmp_path / "ws.db")
    a = store.add_source("A", "text", "a.md")
    b = store.add_source("B", "text", "b.md")
    store.add_chunks([Chunk(id="ck_1", source_id=a.id, seq=0, text="alpha")])
    store.add_chunks([Chunk(id="ck_2", source_id=b.id, seq=0, text="beta")])
    assert [c.id for c in store.get_chunks([a.id])] == ["ck_1"]
    assert len(store.get_chunks()) == 2
    assert store.get_chunk("ck_2").text == "beta"
    store.close()


def test_note_roundtrip_with_citations(tmp_path):
    store = Store(tmp_path / "ws.db")
    citation = Citation(
        chunk_id="ck_1", source_id="src_1", source_title="Doc", locator="chunk 1", snippet="hello"
    )
    note = Note(
        id="note_1",
        title="Title",
        created_at="2026-01-01T00:00:00+00:00",
        source_ids=["src_1"],
        sections=[Section(heading="Overview", bullets=["A point"], citations=[citation])],
    )
    store.save_note(note)
    loaded = store.get_note("note_1")
    assert loaded is not None
    assert loaded.sections[0].bullets == ["A point"]
    assert loaded.sections[0].citations[0].snippet == "hello"
    assert store.get_note("missing") is None
    assert [n.id for n in store.list_notes()] == ["note_1"]
    store.close()
