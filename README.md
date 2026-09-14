# Lynote Notes

**Source-grounded, bilingual, local-first AI note taker.** Turn documents, web
pages, recordings, videos and YouTube links into structured notes where every
bullet cites the exact source chunk it came from — so you can verify, edit and
reuse notes instead of trusting a black box.

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-58%20passed-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-92%25-green)](tests/)

```bash
pip install -e .
lynote-notes add lecture.md
lynote-notes note --title "Week 3: Retrieval"
lynote-notes ask "What is BM25 used for?"
lynote-notes export --note note_xxx --format anki --out cards.tsv
```

## Why

AI note tools usually give you a summary you cannot check. Lynote Notes is
built around **traceability**: notes are generated from your sources, and every
claim links back to a chunk — including a timestamp for audio and video. It
runs with **zero dependencies** by default (stdlib only), works offline with an
extractive provider, and can use any OpenAI-compatible LLM (Ollama, vLLM,
OpenAI, ...) when you want richer prose.

## Features

- **Ingest**: text/Markdown, PDF, DOCX, web pages, YouTube captions, audio and
  video (via optional extras) — each source becomes retrievable chunks.
- **Cited notes**: structured sections (Overview / Key points / Open questions)
  where every bullet carries a source citation.
- **Source-grounded Q&A**: ask questions, get answers with references to the
  chunks that support them, not just a generated paragraph.
- **Local-first**: one SQLite file per workspace; no server, no account.
- **Bilingual**: tokenizer and sentence splitting handle English and Chinese
  (CJK unigrams + bigrams).
- **Exports**: Markdown for reading, Anki TSV for memorising.
- **Pluggable providers**: offline extractive provider by default; any
  OpenAI-compatible endpoint via environment variables.

## Install

```bash
git clone https://github.com/lynote-ai/lynote-notes.git
cd lynote-notes
pip install -e .
```

Optional extras for more source types:

```bash
pip install -e ".[pdf]"        # PDF ingestion (pypdf)
pip install -e ".[docx]"       # Word documents (python-docx)
pip install -e ".[media]"      # audio/video transcription (faster-whisper)
pip install -e ".[youtube]"    # YouTube captions (yt-dlp)
pip install -e ".[all]"        # everything
```

## Quickstart (CLI)

```bash
# 1. Add sources
lynote-notes add notes.md
lynote-notes add paper.pdf                 # needs [pdf]
lynote-notes add https://example.com/post
lynote-notes add talk.mp3                  # needs [media]
lynote-notes add https://youtu.be/xxxx     # needs [youtube]

# 2. See what is in the workspace
lynote-notes list

# 3. Generate a cited note
lynote-notes note --title "Weekly reading"
# or limit to specific sources
lynote-notes note --title "Just the paper" --source src_ab12cd34ef

# 4. Ask questions grounded in your sources
lynote-notes ask "What did we decide about pricing?"

# 5. Export
lynote-notes export --note note_1234567890 --format md   --out note.md
lynote-notes export --note note_1234567890 --format anki --out cards.tsv
```

The workspace directory defaults to `./lynote-workspace`; override with
`--workspace DIR` or `LNOTE_WORKSPACE`.

## Quickstart (Python)

```python
from lynote_notes import Workspace

with Workspace("my-workspace") as ws:
    ws.add("lecture-notes.md")
    ws.add_text("Interview: the team wants a web UI next quarter.", "Interview")

    note = ws.make_note("Research summary")
    print(note.sections[0].bullets)

    answer = ws.ask("What is planned next quarter?")
    print(answer.text)
    for citation in answer.citations:
        print(citation.source_title, citation.locator, "—", citation.snippet)
```

## Using an LLM (optional)

By default Lynote Notes uses the built-in extractive provider — deterministic,
offline, no model required. For generative notes, point it at any
OpenAI-compatible endpoint:

```bash
export LNOTE_PROVIDER=openai
export LNOTE_LLM_BASE_URL=http://localhost:11434/v1   # Ollama default
export LNOTE_LLM_API_KEY=ollama
export LNOTE_LLM_MODEL=llama3.1

lynote-notes note --title "Generative notes"
```

If the model call fails, the provider automatically falls back to the offline
extractor, and citations are still validated against real chunks.

## Architecture

```
                ingest/                    core                      llm/
  ┌───────────────────────────┐   ┌───────────────────┐   ┌─────────────────────┐
  │ text  pdf  docx  web      │   │ chunking          │   │ HeuristicProvider   │
  │ youtube  audio  video     │──▶│ retrieval (BM25)  │──▶│ OpenAICompatProvider│
  └───────────────────────────┘   │ notes (citations) │   └─────────────────────┘
                                  │ qa                │
                                  │ export (md/anki)  │
                                  └─────────┬─────────┘
                                            ▼
                                   SQLite workspace.db
```

Full design notes: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## How it compares

The open-source note space is crowded; these are the closest projects
(stars as of September 2026):

| Project | Stars | Focus | Lynote Notes difference |
|---|---|---|---|
| [open-notebook](https://github.com/lfnovo/open-notebook) | 38.7k | NotebookLM-style research | Notes + Q&A are citation-first; zero-dependency core |
| [meetily](https://github.com/Zackriya-Solutions/meeting-minutes) | 30.7k | Live meeting capture | Upload-based study/reading workflow, not live capture |
| [SurfSense](https://github.com/MODSetter/SurfSense) | 16.1k | Research with live web data | Local-first, offline-capable, no external services |
| [anarlog](https://github.com/fastrepl/anarlog) | 9.3k | Granola alternative | Documents + media + web in one workspace |
| [BiliNote](https://github.com/JefferyHcool/BiliNote) | 7.3k | Chinese video → notes | Multi-source workspace + source-grounded Q&A + Anki export |

None of them ship **citations on every bullet** as the default contract, and
few are bilingual by design.

## Limitations

- The default provider is **extractive**: it selects and organises sentences
  from your sources rather than rewriting them. Use an LLM provider for more
  fluent notes.
- Transcription quality depends on `faster-whisper` model size and audio
  quality; unclear audio can produce wrong text.
- Notes can still miss context or nuance — always check important facts,
  numbers and quotes against the cited source.
- No live meeting capture by design: export the recording and upload it.
- Embedding-based retrieval is on the roadmap; today's BM25 retriever is
  lexical (strong for keyword-ish questions, weaker for pure paraphrase).

## Roadmap

- [x] Ingest pipeline with citations, CLI, Markdown/Anki export
- [x] Offline extractive provider + OpenAI-compatible provider
- [ ] Embedding retrieval (`sqlite-vec`) with hybrid scoring
- [ ] Flashcard quality pass (cloze cards, better Anki metadata)
- [ ] Web UI (FastAPI + minimal frontend) and HF Space demo
- [ ] Optional AI-content flags on sources (via Lynote's open detector)

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE). Built by [Lynote](https://lynote.ai).
