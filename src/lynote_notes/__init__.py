"""Lynote Notes — source-grounded, bilingual, local-first AI note taker."""

from .models import Answer, Chunk, Citation, Note, Section, Source
from .pipeline import Workspace

__version__ = "0.1.0"

__all__ = [
    "Answer",
    "Chunk",
    "Citation",
    "Note",
    "Section",
    "Source",
    "Workspace",
    "__version__",
]
