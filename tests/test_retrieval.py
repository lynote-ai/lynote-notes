from lynote_notes.models import Chunk
from lynote_notes.retrieval import BM25, retrieve, tokenize


def make_chunk(cid, text, seq=0):
    return Chunk(id=cid, source_id="src_1", seq=seq, text=text)


def test_tokenize_handles_cjk():
    tokens = tokenize("人工智能 works")
    assert "人工智能" not in tokens
    assert "人" in tokens
    assert "人工" in tokens
    assert "works" in tokens


def test_bm25_ranks_relevant_chunk_first():
    chunks = [
        make_chunk("ck_1", "The pricing plan starts at ten dollars per month."),
        make_chunk("ck_2", "Our office is in Shanghai and opens at nine."),
        make_chunk("ck_3", "Refunds are available within thirty days of purchase.", seq=1),
    ]
    hits = retrieve("How much does the pricing plan cost?", chunks, top_k=2)
    assert hits[0][0].id == "ck_1"
    assert hits[0][1] > 0


def test_bm25_empty_query_or_chunks():
    assert retrieve("", [make_chunk("ck_1", "text")]) == []
    assert retrieve("query", []) == []
    assert BM25().score("", [], top_k=3) == []


def test_bm25_top_k_limit():
    chunks = [make_chunk(f"ck_{i}", f"document number {i} about topic") for i in range(10)]
    hits = retrieve("document topic", chunks, top_k=3)
    assert len(hits) == 3
