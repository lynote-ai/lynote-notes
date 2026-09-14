"""Dependency-free retrieval (BM25-lite).

A small lexical retriever is enough for "ask my notes" over a handful of
documents, works offline, and keeps the core installable with zero
dependencies. Embeddings can be plugged in later without changing the API.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List, Sequence, Tuple

from .models import Chunk

_WORD = re.compile(r"[a-z0-9]+")
_CJK = re.compile(r"[\u4e00-\u9fff]")

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "as",
    "at", "by", "from", "we", "you", "they", "he", "she", "i", "not", "but",
    "what", "which", "who", "how", "why", "when", "where", "can", "could",
    "should", "would", "will", "do", "does", "did", "has", "have", "had",
}


def tokenize(text: str) -> List[str]:
    """Latin words plus CJK unigrams/bigrams (CJK has no spaces).

    Numeric tokens are kept even when short ("5" in "GPT 5", "42" in
    "topic 42") because they are often the most specific part of a query.
    """
    text = text.lower()
    tokens = [
        t
        for t in _WORD.findall(text)
        if t.isdigit() or (t not in _STOPWORDS and len(t) > 1)
    ]
    cjk_chars = _CJK.findall(text)
    tokens.extend(cjk_chars)
    tokens.extend(a + b for a, b in zip(cjk_chars, cjk_chars[1:]))
    return tokens


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def score(self, query: str, chunks: Sequence[Chunk], top_k: int = 4) -> List[Tuple[Chunk, float]]:
        if not chunks:
            return []
        docs = [tokenize(c.text) for c in chunks]
        lengths = [len(d) for d in docs]
        avgdl = sum(lengths) / len(lengths) if lengths else 0.0
        df: Counter = Counter()
        for doc in docs:
            df.update(set(doc))

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        n = len(docs)
        scored: List[Tuple[Chunk, float]] = []
        for chunk, doc, dl in zip(chunks, docs, lengths):
            tf = Counter(doc)
            score = 0.0
            for term in set(q_tokens):
                if term not in tf:
                    continue
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                denom = tf[term] + self.k1 * (1 - self.b + self.b * (dl / avgdl if avgdl else 0))
                score += idf * (tf[term] * (self.k1 + 1)) / (denom or 1)
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda pair: (-pair[1], pair[0].source_id, pair[0].seq))
        return scored[:top_k]


def retrieve(query: str, chunks: Iterable[Chunk], top_k: int = 4) -> List[Tuple[Chunk, float]]:
    return BM25().score(query, list(chunks), top_k=top_k)
