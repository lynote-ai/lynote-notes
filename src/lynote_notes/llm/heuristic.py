"""Offline extractive provider.

No model, no network, no randomness: sentences are scored by term
informativeness, position and length, then grouped into a structured note.
This is the default provider, the fallback when an LLM call fails, and what
the test-suite exercises.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Sequence, Tuple

from ..chunking import split_sentences
from ..models import Chunk
from ..retrieval import tokenize
from .base import AnswerDraft, BulletDraft, SectionDraft

_QUESTION = re.compile(r"[?？]")
_TERMINAL = re.compile(r"[.!?。！？]['\")]?$")


def _normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _similar(a: str, b: str) -> bool:
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta or not tb:
        return _normalize(a) == _normalize(b)
    return len(ta & tb) / len(ta | tb) > 0.7


def _sentence_candidates(chunks: Sequence[Chunk]) -> List[Tuple[str, Chunk, int]]:
    out: List[Tuple[str, Chunk, int]] = []
    for index, chunk in enumerate(chunks):
        for sentence in split_sentences(chunk.text):
            if len(sentence) >= 20:
                out.append((sentence, chunk, index))
    return out


def _score_sentences(candidates: List[Tuple[str, Chunk, int]]) -> List[Tuple[float, str, Chunk]]:
    if not candidates:
        return []
    df: Counter = Counter()
    for sentence, _, _ in candidates:
        df.update(set(tokenize(sentence)))
    n = len(candidates)
    scored: List[Tuple[float, str, Chunk]] = []
    for sentence, chunk, index in candidates:
        tokens = tokenize(sentence)
        if not tokens:
            continue
        score = sum(
            (1.0 + (n / (1 + df[t]))) for t in set(tokens)
        ) / (1 + len(tokens) ** 0.5)
        score += 0.5 / (1 + index)  # slight preference for earlier material
        if len(sentence) > 400:
            score *= 0.8
        scored.append((score, sentence.strip(), chunk))
    scored.sort(key=lambda item: (-item[0], item[2].source_id, item[2].seq))
    return scored


def _dedupe(items: List[Tuple[float, str, Chunk]], limit: int) -> List[Tuple[str, Chunk]]:
    picked: List[Tuple[str, Chunk]] = []
    for _, sentence, chunk in items:
        if any(_similar(sentence, existing) for existing, _ in picked):
            continue
        picked.append((sentence, chunk))
        if len(picked) >= limit:
            break
    return picked


def _bigrams(tokens: List[str]) -> set:
    return {(a, b) for a, b in zip(tokens, tokens[1:])}


class HeuristicProvider:
    """Extractive, deterministic note provider."""

    name = "heuristic"

    def summarize(self, title: str, chunks: Sequence[Chunk]) -> List[SectionDraft]:
        chunks = list(chunks)
        candidates = _sentence_candidates(chunks)
        scored = _score_sentences(candidates)
        if not scored:
            return [SectionDraft(heading="Overview", bullets=[])]

        sections: List[SectionDraft] = []
        used: List[str] = []

        # Overview: the opening material, kept in reading order.
        opening: List[Tuple[str, Chunk]] = []
        for sentence, chunk, _ in candidates:
            if any(_similar(sentence, existing) for existing in used):
                continue
            opening.append((sentence.strip(), chunk))
            used.append(sentence)
            if len(opening) >= 2:
                break
        if not opening:
            opening = [(sentence, chunk) for _, sentence, chunk in scored[:2]]
            used.extend(sentence for sentence, _ in opening)
        sections.append(
            SectionDraft(
                heading="Overview",
                bullets=[BulletDraft(text=sentence, chunk_id=chunk.id) for sentence, chunk in opening],
            )
        )

        remaining = [
            (score, sentence, chunk)
            for score, sentence, chunk in scored
            if not _QUESTION.search(sentence)
            and not any(_similar(sentence, existing) for existing in used)
        ]
        key_points = _dedupe(remaining, limit=8)
        used.extend(sentence for sentence, _ in key_points)
        sections.append(
            SectionDraft(
                heading="Key points",
                bullets=[BulletDraft(text=sentence, chunk_id=chunk.id) for sentence, chunk in key_points],
            )
        )

        questions = [
            (score, sentence, chunk)
            for score, sentence, chunk in scored
            if _QUESTION.search(sentence)
            and not any(_similar(sentence, existing) for existing in used)
        ]
        if questions:
            follow_ups = _dedupe(questions, limit=3)
            sections.append(
                SectionDraft(
                    heading="Open questions",
                    bullets=[
                        BulletDraft(text=sentence, chunk_id=chunk.id) for sentence, chunk in follow_ups
                    ],
                )
            )
        return sections

    def answer(self, question: str, chunks: Sequence[Chunk]) -> AnswerDraft:
        q_tokens = tokenize(question)
        q_set = set(q_tokens)
        q_bigrams = _bigrams(q_tokens)
        best: List[Tuple[float, str, Chunk]] = []
        fragments: List[Tuple[float, str, Chunk]] = []
        for chunk in chunks:
            for sentence in split_sentences(chunk.text):
                s_tokens = tokenize(sentence)
                s_set = set(s_tokens)
                if not s_set:
                    continue
                overlap = len(q_set & s_set) / (1 + len(q_set))
                # Phrase bonus: "topic 42" should beat a sentence that merely
                # contains "42" somewhere else.
                overlap += 0.15 * len(q_bigrams & _bigrams(s_tokens))
                item = (overlap, sentence.strip(), chunk)
                if _TERMINAL.search(sentence.strip()) or len(sentence) >= 60:
                    best.append(item)
                else:
                    fragments.append(item)  # headings and short labels
        best = best or fragments
        best.sort(key=lambda item: (-item[0], item[2].source_id, item[2].seq))
        picked: List[Tuple[str, Chunk]] = []
        for score, sentence, chunk in best:
            if score <= 0:
                continue
            if any(_similar(sentence, existing) for existing, _ in picked):
                continue
            picked.append((sentence, chunk))
            if len(picked) >= 2:
                break
        if not picked:
            return AnswerDraft(text="", chunk_ids=[])
        text = " ".join(sentence for sentence, _ in picked)
        return AnswerDraft(text=text, chunk_ids=[chunk.id for _, chunk in picked])
