"""OpenAI-compatible provider (works with OpenAI, Ollama, vLLM, ...).

Uses only the standard library, so ``pip install lynote-notes`` stays
dependency-free; point it at any ``/v1/chat/completions`` endpoint via
environment variables.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, List, Sequence

from ..models import Chunk
from .base import AnswerDraft, BulletDraft, SectionDraft
from .heuristic import HeuristicProvider

_SYSTEM = (
    "You are Lynote Notes, a careful note-taking assistant. "
    "Use ONLY the provided context. Every bullet must cite the exact chunk id "
    "it came from, written as [ck_xxxx]. Never invent chunk ids or facts."
)

_SUMMARY_PROMPT = """Create structured notes titled "{title}" from the context below.

Return STRICT JSON with this shape:
{{"sections": [{{"heading": "Overview", "bullets": [{{"text": "...", "chunk_id": "ck_..."}}]}}]}}

Rules:
- 3 to 5 sections, 2 to 6 bullets each.
- Each bullet is one clear sentence; keep numbers, names and quotes exact.
- chunk_id must be one of the ids in square brackets below.

Context:
{context}
"""

_ANSWER_PROMPT = """Answer the question using ONLY the context below.

Return STRICT JSON: {{"text": "concise answer", "chunk_ids": ["ck_...", "..."]}}

Question: {question}

Context:
{context}
"""


class LLMError(RuntimeError):
    pass


def _format_context(chunks: Sequence[Chunk], limit: int = 20) -> str:
    blocks: List[str] = []
    for chunk in list(chunks)[:limit]:
        blocks.append(f"[{chunk.id}] {chunk.text}")
    return "\n\n".join(blocks)


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise LLMError(f"No JSON object in model output: {text[:200]!r}")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"Invalid JSON from model: {exc}") from exc


class OpenAICompatProvider:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
        model: str = "llama3.1",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.name = f"openai-compat:{model}"

    def _chat(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                data = json.loads(response.read())
        except urllib.error.HTTPError as exc:  # pragma: no cover - network path
            raise LLMError(f"LLM HTTP error {exc.code}: {exc.read()[:200]!r}") from exc
        except Exception as exc:  # pragma: no cover - network path
            raise LLMError(f"LLM request failed: {exc}") from exc
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response: {str(data)[:200]}") from exc

    def summarize(self, title: str, chunks: Sequence[Chunk]) -> List[SectionDraft]:
        raw = self._chat(_SUMMARY_PROMPT.format(title=title, context=_format_context(chunks)))
        payload = _extract_json(raw)
        valid_ids = {chunk.id for chunk in chunks}
        sections: List[SectionDraft] = []
        for section in payload.get("sections", []):
            bullets = []
            for bullet in section.get("bullets", []):
                chunk_id = str(bullet.get("chunk_id", ""))
                if chunk_id not in valid_ids:
                    continue  # drop hallucinated citations
                bullets.append(BulletDraft(text=str(bullet.get("text", "")).strip(), chunk_id=chunk_id))
            if bullets:
                sections.append(SectionDraft(heading=str(section.get("heading", "Notes")), bullets=bullets))
        if not sections:
            raise LLMError("Model returned no valid sections")
        return sections

    def answer(self, question: str, chunks: Sequence[Chunk]) -> AnswerDraft:
        raw = self._chat(_ANSWER_PROMPT.format(question=question, context=_format_context(chunks)))
        payload = _extract_json(raw)
        valid_ids = {chunk.id for chunk in chunks}
        chunk_ids = [cid for cid in payload.get("chunk_ids", []) if cid in valid_ids]
        return AnswerDraft(text=str(payload.get("text", "")).strip(), chunk_ids=chunk_ids)


def with_fallback(provider, fallback=None):
    """Wrap a provider so LLM failures fall back to the offline extractor."""
    fallback = fallback or HeuristicProvider()

    class _Fallback:
        name = provider.name

        def summarize(self, title, chunks):
            try:
                return provider.summarize(title, chunks)
            except LLMError:
                return fallback.summarize(title, chunks)

        def answer(self, question, chunks):
            try:
                return provider.answer(question, chunks)
            except LLMError:
                return fallback.answer(question, chunks)

    return _Fallback()
