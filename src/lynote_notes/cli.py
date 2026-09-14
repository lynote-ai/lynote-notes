"""Command line interface.

Examples:
    lynote-notes add notes.md
    lynote-notes add https://example.com/article
    lynote-notes note --title "Weekly reading"
    lynote-notes ask "What did we decide about pricing?"
    lynote-notes export --note note_123 --format anki --out cards.tsv
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import __version__
from .export import format_answer
from .ingest.base import OptionalDependencyError
from .pipeline import DEFAULT_ROOT, Workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lynote-notes",
        description="Source-grounded, local-first AI note taker.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--workspace",
        default=os.environ.get("LNOTE_WORKSPACE", DEFAULT_ROOT),
        help=f"workspace directory (default: {DEFAULT_ROOT})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="ingest a file or URL into the workspace")
    add.add_argument("source", help="file path or URL")
    add.add_argument("--title", default="", help="override the source title")
    add.add_argument("--kind", default="", help="force source kind (text/pdf/docx/web/youtube/audio/video)")

    listing = sub.add_parser("list", help="list sources or notes")
    listing.add_argument("--notes", action="store_true", help="list notes instead of sources")

    note = sub.add_parser("note", help="generate a cited note")
    note.add_argument("--title", required=True)
    note.add_argument("--source", action="append", default=[], help="limit to a source id (repeatable)")

    ask = sub.add_parser("ask", help="ask a question grounded in your sources")
    ask.add_argument("question")
    ask.add_argument("--source", action="append", default=[])
    ask.add_argument("-k", "--top-k", type=int, default=4)

    export = sub.add_parser("export", help="export a note as markdown or Anki TSV")
    export.add_argument("--note", required=True, help="note id")
    export.add_argument("--format", choices=["md", "anki"], default="md")
    export.add_argument("--out", default="", help="output path (default: stdout)")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    with Workspace(args.workspace) as workspace:
        try:
            if args.command == "add":
                source = workspace.add(args.source, title=args.title, kind=args.kind)
                print(f"Added {source.id}: {source.title} ({source.kind})")
                return 0

            if args.command == "list":
                if args.notes:
                    for note in workspace.list_notes():
                        print(f"{note.id}\t{note.title}\t{len(note.sections)} sections")
                else:
                    for source in workspace.list_sources():
                        print(f"{source.id}\t{source.kind}\t{source.title}")
                return 0

            if args.command == "note":
                note = workspace.make_note(args.title, args.source)
                print(workspace.export_note(note, "md"), end="")
                print(f"\n(note id: {note.id})", file=sys.stderr)
                return 0

            if args.command == "ask":
                answer = workspace.ask(args.question, args.source, args.top_k)
                print(format_answer(answer), end="")
                return 0

            if args.command == "export":
                note = workspace.store.get_note(args.note)
                if note is None:
                    print(f"Note not found: {args.note}", file=sys.stderr)
                    return 1
                content = workspace.export_note(note, args.format, args.out)
                if not args.out:
                    print(content, end="")
                else:
                    print(f"Wrote {args.out}")
                return 0
        except OptionalDependencyError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
