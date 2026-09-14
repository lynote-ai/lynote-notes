"""SQLite-backed workspace store.

One workspace == one database file. Sources, chunks and notes are stored as
rows with JSON payloads for the flexible parts, so the schema stays small and
the store works with zero third-party dependencies.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import Chunk, Citation, Note, Section, Source

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    origin TEXT NOT NULL,
    created_at TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_ts REAL,
    end_ts REAL,
    meta TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id, seq);
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_ids TEXT NOT NULL DEFAULT '[]',
    sections TEXT NOT NULL DEFAULT '[]'
);
"""


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- sources -----------------------------------------------------------
    def add_source(self, title: str, kind: str, origin: str, meta: Optional[Dict[str, str]] = None) -> Source:
        source = Source(
            id=new_id("src"),
            title=title,
            kind=kind,
            origin=origin,
            created_at=utcnow(),
            meta=meta or {},
        )
        self.conn.execute(
            "INSERT INTO sources (id, title, kind, origin, created_at, meta) VALUES (?,?,?,?,?,?)",
            (source.id, source.title, source.kind, source.origin, source.created_at, json.dumps(source.meta)),
        )
        self.conn.commit()
        return source

    def get_source(self, source_id: str) -> Optional[Source]:
        row = self.conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        return self._row_to_source(row) if row else None

    def list_sources(self) -> List[Source]:
        rows = self.conn.execute("SELECT * FROM sources ORDER BY rowid").fetchall()
        return [self._row_to_source(r) for r in rows]

    @staticmethod
    def _row_to_source(row: sqlite3.Row) -> Source:
        return Source(
            id=row["id"],
            title=row["title"],
            kind=row["kind"],
            origin=row["origin"],
            created_at=row["created_at"],
            meta=json.loads(row["meta"]),
        )

    # -- chunks ------------------------------------------------------------
    def add_chunks(self, chunks: List[Chunk]) -> None:
        self.conn.executemany(
            "INSERT INTO chunks (id, source_id, seq, text, start_ts, end_ts, meta) VALUES (?,?,?,?,?,?,?)",
            [
                (c.id, c.source_id, c.seq, c.text, c.start_ts, c.end_ts, json.dumps(c.meta))
                for c in chunks
            ],
        )
        self.conn.commit()

    def get_chunks(self, source_ids: Optional[List[str]] = None) -> List[Chunk]:
        if source_ids:
            placeholders = ",".join("?" for _ in source_ids)
            rows = self.conn.execute(
                f"SELECT * FROM chunks WHERE source_id IN ({placeholders}) ORDER BY rowid",
                tuple(source_ids),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM chunks ORDER BY rowid").fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        row = self.conn.execute("SELECT * FROM chunks WHERE id=?", (chunk_id,)).fetchone()
        return self._row_to_chunk(row) if row else None

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> Chunk:
        return Chunk(
            id=row["id"],
            source_id=row["source_id"],
            seq=row["seq"],
            text=row["text"],
            start_ts=row["start_ts"],
            end_ts=row["end_ts"],
            meta=json.loads(row["meta"]),
        )

    # -- notes -------------------------------------------------------------
    def save_note(self, note: Note) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO notes (id, title, created_at, source_ids, sections) VALUES (?,?,?,?,?)",
            (
                note.id,
                note.title,
                note.created_at,
                json.dumps(note.source_ids),
                json.dumps([self._section_to_dict(s) for s in note.sections]),
            ),
        )
        self.conn.commit()

    def get_note(self, note_id: str) -> Optional[Note]:
        row = self.conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if not row:
            return None
        return Note(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            source_ids=json.loads(row["source_ids"]),
            sections=[self._dict_to_section(d) for d in json.loads(row["sections"])],
        )

    def list_notes(self) -> List[Note]:
        rows = self.conn.execute("SELECT id FROM notes ORDER BY rowid").fetchall()
        return [self.get_note(r["id"]) for r in rows]  # type: ignore[misc]

    @staticmethod
    def _section_to_dict(section: Section) -> dict:
        return {
            "heading": section.heading,
            "bullets": section.bullets,
            "citations": [
                {
                    "chunk_id": c.chunk_id,
                    "source_id": c.source_id,
                    "source_title": c.source_title,
                    "locator": c.locator,
                    "snippet": c.snippet,
                }
                for c in section.citations
            ],
        }

    @staticmethod
    def _dict_to_section(data: dict) -> Section:
        return Section(
            heading=data["heading"],
            bullets=list(data["bullets"]),
            citations=[Citation(**c) for c in data.get("citations", [])],
        )
