"""Live HTTP tests: real urllib fetch against a local server."""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError

import pytest

from lynote_notes import Workspace
from lynote_notes.ingest.web import fetch_url, ingest_web

PAGE = """<!doctype html>
<html><head><title>Live Page</title><script>ignore()</script></head>
<body><h1>Heading</h1><p>Hello from the server.</p></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/ok":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture()
def http_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_fetch_url_and_ingest_web(http_server):
    html = fetch_url(f"{http_server}/ok")
    assert "Hello from the server." in html

    result = ingest_web(f"{http_server}/ok")
    assert result.title == "Live Page"
    assert "Hello from the server." in result.blocks[0]["text"]
    assert "ignore()" not in result.blocks[0]["text"]
    assert result.meta["url"].endswith("/ok")


def test_fetch_url_http_error(http_server):
    with pytest.raises(HTTPError) as excinfo:
        fetch_url(f"{http_server}/missing")
    assert excinfo.value.code == 404


def test_workspace_add_web_url(http_server):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        with Workspace(tmp) as ws:
            source = ws.add(f"{http_server}/ok")
            assert source.kind == "web"
            assert source.title == "Live Page"
            answer = ws.ask("What does the server say?")
            assert "Hello from the server" in answer.text
            assert answer.citations
