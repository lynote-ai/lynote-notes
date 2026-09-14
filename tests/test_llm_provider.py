"""Tests for the OpenAI-compatible provider using a local mock server.

These cover the HTTP path, JSON parsing, citation validation and the fallback
behaviour — all without network access or a real model.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from lynote_notes.llm.heuristic import HeuristicProvider
from lynote_notes.llm.openai_compat import (
    LLMError,
    OpenAICompatProvider,
    _extract_json,
    with_fallback,
)
from lynote_notes.models import Chunk


class _Handler(BaseHTTPRequestHandler):
    responses = []
    requests = []

    def do_POST(self):  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        type(self).requests.append(body)
        status, payload = type(self).responses.pop(0)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *args):  # keep test output clean
        pass


@pytest.fixture()
def llm_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    _Handler.responses = []
    _Handler.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, _Handler
    server.shutdown()


def _chat_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def _provider(server) -> OpenAICompatProvider:
    return OpenAICompatProvider(base_url=f"http://127.0.0.1:{server.server_port}/v1", model="test-model")


CHUNKS = [
    Chunk(id="ck_a", source_id="src_1", seq=0, text="BM25 is a lexical retrieval algorithm."),
    Chunk(id="ck_b", source_id="src_1", seq=1, text="Embeddings capture semantic similarity."),
]


def test_summarize_parses_sections_and_drops_hallucinated_ids(llm_server):
    server, handler = llm_server
    handler.responses.append(
        (
            200,
            _chat_response(
                json.dumps(
                    {
                        "sections": [
                            {
                                "heading": "Key points",
                                "bullets": [
                                    {"text": "BM25 is lexical.", "chunk_id": "ck_a"},
                                    {"text": "Invented fact.", "chunk_id": "ck_hallucinated"},
                                ],
                            }
                        ]
                    }
                )
            ),
        )
    )
    sections = _provider(server).summarize("Title", CHUNKS)
    assert len(sections) == 1
    assert [b.chunk_id for b in sections[0].bullets] == ["ck_a"]
    # request carries the model and context with chunk ids
    request = handler.requests[0]
    assert request["model"] == "test-model"
    assert "ck_a" in request["messages"][1]["content"]


def test_summarize_accepts_fenced_json(llm_server):
    server, handler = llm_server
    fenced = "```json\n" + json.dumps(
        {"sections": [{"heading": "H", "bullets": [{"text": "T", "chunk_id": "ck_a"}]}]}
    ) + "\n```"
    handler.responses.append((200, _chat_response(fenced)))
    sections = _provider(server).summarize("Title", CHUNKS)
    assert sections[0].bullets[0].text == "T"


def test_answer_parses_and_validates_chunk_ids(llm_server):
    server, handler = llm_server
    handler.responses.append(
        (
            200,
            _chat_response(json.dumps({"text": "It is lexical.", "chunk_ids": ["ck_a", "ck_bad"]})),
        )
    )
    answer = _provider(server).answer("What is BM25?", CHUNKS)
    assert answer.text == "It is lexical."
    assert answer.chunk_ids == ["ck_a"]


def test_http_error_raises_llm_error(llm_server):
    server, handler = llm_server
    handler.responses.append((500, {"error": "boom"}))
    with pytest.raises(LLMError):
        _provider(server).summarize("Title", CHUNKS)


def test_malformed_json_raises_llm_error(llm_server):
    server, handler = llm_server
    handler.responses.append((200, _chat_response("no json here")))
    with pytest.raises(LLMError):
        _provider(server).answer("q", CHUNKS)


def test_unexpected_response_shape_raises_llm_error(llm_server):
    server, handler = llm_server
    handler.responses.append((200, {"unexpected": True}))
    with pytest.raises(LLMError):
        _provider(server).summarize("Title", CHUNKS)


def test_with_fallback_uses_heuristic_on_failure(llm_server):
    server, handler = llm_server
    handler.responses.append((500, {"error": "down"}))
    provider = with_fallback(_provider(server), HeuristicProvider())
    sections = provider.summarize("Title", CHUNKS)
    assert sections
    assert all(b.chunk_id in {"ck_a", "ck_b"} for s in sections for b in s.bullets)


def test_with_fallback_passes_through_success(llm_server):
    server, handler = llm_server
    handler.responses.append(
        (
            200,
            _chat_response(
                json.dumps(
                    {"sections": [{"heading": "LLM", "bullets": [{"text": "T", "chunk_id": "ck_b"}]}]}
                )
            ),
        )
    )
    provider = with_fallback(_provider(server), HeuristicProvider())
    sections = provider.summarize("Title", CHUNKS)
    assert sections[0].heading == "LLM"


def test_extract_json_variants():
    assert _extract_json('{"a": 1}') == {"a": 1}
    assert _extract_json('prefix {"a": 2} suffix') == {"a": 2}
    with pytest.raises(LLMError):
        _extract_json("no braces")
    with pytest.raises(LLMError):
        _extract_json("{broken json")


def test_get_provider_env(monkeypatch):
    from lynote_notes.llm import get_provider

    monkeypatch.delenv("LNOTE_PROVIDER", raising=False)
    assert get_provider().name == "heuristic"

    monkeypatch.setenv("LNOTE_PROVIDER", "openai")
    monkeypatch.setenv("LNOTE_LLM_MODEL", "mistral")
    provider = get_provider()
    assert provider.name == "openai-compat:mistral"
