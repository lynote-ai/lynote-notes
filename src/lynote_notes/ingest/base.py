"""Ingest layer: turn any supported input into timestamped text blocks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IngestResult:
    title: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, str] = field(default_factory=dict)


class OptionalDependencyError(RuntimeError):
    """Raised when a feature needs an optional extra that is not installed."""

    def __init__(self, feature: str, package: str, extra: str) -> None:
        super().__init__(
            f"{feature} requires the optional dependency '{package}'. "
            f"Install it with: pip install 'lynote-notes[{extra}]'"
        )
        self.feature = feature
        self.package = package
        self.extra = extra
