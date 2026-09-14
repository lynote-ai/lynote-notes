# Week 3 — Retrieval and source-grounded notes

This lecture covers how a note taker should retrieve evidence before it writes.

## Why retrieval matters

A summariser that never looks anything up will happily invent details. Retrieval
grounds every claim in a specific passage, which is what makes a note checkable.
The lecture used the example of a student revising for an exam: if a note says
"BM25 is used for retrieval", the student should be able to click through to the
sentence that said it.

## How BM25 works

BM25 scores a document for a query using term frequency, inverse document
frequency and document length normalisation. It is lexical, which means it
matches words rather than meanings. For personal note collections this is often
enough, and it runs offline with no model download.

## Where lexical retrieval fails

Paraphrase is the weak spot. If a question says "cost" but the source says
"price", BM25 may miss the passage. The standard fix is hybrid retrieval:
combine BM25 with embeddings and merge the rankings.

## Citations in practice

Every bullet in a generated note carries a chunk id. The note builder resolves
that id into a human-readable citation with the source title and a locator such
as "chunk 4" or "00:12:30" for media. Hallucinated ids are dropped, so a model
cannot cite something that does not exist.

## Open questions from the lecture

How should overlapping chunks be cited when a sentence spans two chunks? Should
flashcards be generated from notes or directly from sources?
