# Lynote Notes — Architecture

Status: v0.1 (MVP) · License: MIT

## 1. Goals and non-goals

**Goals**

1. Turn heterogeneous sources (docs, web, media) into notes whose every claim is
   traceable to a chunk of the original material.
2. Run with zero third-party dependencies in the default configuration
   (offline, deterministic, easy to audit).
3. Keep providers pluggable: the same pipeline must work with an extractive
   algorithm, a local Ollama model, or a hosted API.
4. Stay local-first: one workspace == one SQLite file, no server or account.

**Non-goals (for the MVP)**

- Live meeting capture / calendar bots.
- Real-time collaboration or sync.
- Perfect transcription or summarisation quality — the product contract is
  traceability plus editability, not magic.

## 2. Module map

```
src/lynote_notes/
├── models.py        dataclasses: Source, Chunk, Citation, Section, Note, Answer
├── store.py         SQLite persistence (sources / chunks / notes)
├── chunking.py      paragraph- and sentence-aware splitting, media timestamps
├── retrieval.py     BM25-lite lexical retrieval + bilingual tokenizer
├── notes.py         provider drafts -> Note with resolved citations
├── qa.py            retrieve -> answer -> cite
├── export.py        Markdown and Anki TSV exporters
├── pipeline.py      Workspace: the façade that ties everything together
├── cli.py           argparse CLI (add / list / note / ask / export)
├── ingest/
│   ├── __init__.py  registry: detect_kind + lazy ingest dispatch
│   ├── base.py      IngestResult, OptionalDependencyError
│   ├── text.py      .txt/.md/...
│   ├── web.py       stdlib HTML -> text extraction (injectable fetch)
│   ├── pdf.py       pypdf (extra)
│   ├── docx.py      python-docx (extra)
│   ├── youtube.py   yt-dlp captions + WebVTT parser (extra)
│   └── media.py     faster-whisper transcription (extra)
└── llm/
    ├── base.py      NoteProvider protocol, *Draft dataclasses
    ├── heuristic.py offline extractive provider (default)
    ├── openai_compat.py  /v1/chat/completions client + fallback wrapper
    └── __init__.py  get_provider() factory (env-driven)
```

## 3. Data flow

```
 file / URL
    │
    ▼
 ingest() ──────────────► IngestResult{ title, blocks[{text, start_ts, end_ts}] }
    │
    ▼
 build_chunks() ────────► Chunk[] (paragraph-aware, overlap, timestamps kept)
    │
    ▼
 Store.add_source/add_chunks ──► workspace.db
    │
    ▼
 provider.summarize() ──► SectionDraft[BulletDraft{text, chunk_id}]
    │                          (heuristic | openai-compat w/ fallback)
    ▼
 build_note() ──────────► Note{sections with Citation[]} ──► Store.save_note()
    │
    ▼
 export: Markdown (reading) / Anki TSV (memorising)

 question ──► retrieve(BM25) ──► provider.answer() ──► Answer{text, citations}
```

Key invariant: **providers never produce final citation objects.** They return
chunk ids; `notes.py` / `qa.py` resolve ids against the store and drop anything
that does not exist. A hallucinated citation cannot leak into a note.

## 4. Data model

| Entity | Fields | Notes |
|---|---|---|
| `Source` | id, title, kind, origin, created_at, meta | `kind`: text/pdf/docx/web/youtube/audio/video |
| `Chunk` | id, source_id, seq, text, start_ts, end_ts, meta | retrieval + citation unit |
| `Citation` | chunk_id, source_id, source_title, locator, snippet | locator = `HH:MM:SS` for media, `chunk N` for text |
| `Section` | heading, bullets, citations | one note section |
| `Note` | id, title, sections, created_at, source_ids | persisted as JSON |
| `Answer` | question, text, citations | Q&A result |

## 5. Design decisions

1. **stdlib-first core.** Default install has no dependencies. Optional source
   types live behind extras (`[pdf]`, `[docx]`, `[media]`, `[youtube]`) and are
   imported lazily, raising `OptionalDependencyError` with the exact install
   command when missing.
2. **Citations as a contract, not a prompt trick.** The provider interface is
   chunk-id-based; validation happens in one place. Works identically for
   extractive and generative providers.
3. **BM25-lite instead of embeddings (for now).** A lexical retriever is enough
   for a personal workspace, runs offline, and keeps the core auditable.
   `retrieval.retrieve()` is the seam where hybrid/embedding scoring will land.
4. **One workspace, one SQLite file.** Trivially backup-able, inspectable with
   `sqlite3`, no server. JSON columns absorb schema evolution in the MVP.
5. **Heuristic default + automatic fallback.** The extractive provider makes the
   tool useful with zero configuration and makes tests deterministic; the
   OpenAI-compatible provider is wrapped with a fallback so a dead endpoint
   degrades instead of failing.
6. **Bilingual tokenizer.** CJK text is indexed as unigrams + bigrams alongside
   Latin word tokens; sentence splitting handles `。！？；` without requiring
   whitespace.
7. **Injectable I/O for tests.** `ingest_web(fetch=...)` and pure functions
   (`html_to_text`, `parse_vtt`) let the test-suite cover ingestion without
   network access.

## 6. Extension points

- **New source type**: add `ingest/<kind>.py` returning `IngestResult`, register
  the extension/host in `ingest/__init__.py`. No core changes.
- **New provider**: implement `summarize()` / `answer()` returning `*Draft`
  objects; register in `llm/__init__.py::get_provider`.
- **Better retrieval**: replace `BM25.score()` or make `retrieve()` hybrid.
  Citation resolution is unaffected because chunk ids stay the unit.
- **New export**: add a function in `export.py` and a branch in
  `Workspace.export_note`.

## 7. Testing strategy

- 58 tests, all offline and deterministic (92% line coverage of `src/`).
- Unit coverage per module: chunking, store, ingest (incl. VTT and HTML parsers),
  retrieval, notes, Q&A, export.
- The LLM HTTP path is tested against a local mock server, including
  hallucinated-citation rejection and fallback behaviour.
- Live HTTP ingestion is tested against a local `http.server` instance.
- Stress tests cover a 300-paragraph document, 30-source retrieval, Chinese
  end-to-end and unicode round-trips.
- CLI tests execute the real `main(argv)` against a temp workspace.
- E2E test covers ingest → note → ask → export → reopen persistence.
- Optional-dependency paths are tested for their *error* behaviour when the
  extra is not installed, and skipped when it is.

Run:

```bash
pytest
```

## 8. Roadmap phases

1. **v0.1 (done)** — pipeline, citations, CLI, exports, offline + LLM providers.
2. **v0.2** — `sqlite-vec` hybrid retrieval; cloze-style Anki cards.
3. **v0.3** — FastAPI web UI; HF Space demo; workspace import/export.
4. **v0.4** — optional AI-content flags on sources using Lynote's open detector,
   closing the loop between "notes you can trust" and "sources you can trust".
