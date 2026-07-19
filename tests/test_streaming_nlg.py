"""Unit tests for enhanced_core.streaming_nlg.StreamingNLG.

Network access is fully stubbed by patching the ``requests`` module the
StreamingNLG methods rely on.
"""

import requests

import enhanced_core.streaming_nlg as streaming_nlg
from enhanced_core.streaming_nlg import StreamingNLG


class FakeResponse:
    def __init__(self, *, lines=None, json_data=None, raise_exc=None):
        self._lines = lines or []
        self._json = json_data
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def iter_lines(self, decode_unicode=False):
        for line in self._lines:
            yield line

    def json(self):
        return self._json


class TestInit:
    def test_sets_url_and_auth_header(self):
        nlg = StreamingNLG("https://api.example.com/chat", "secret-key")
        assert nlg.api_url == "https://api.example.com/chat"
        assert nlg.headers["Authorization"] == "Bearer secret-key"
        assert nlg.headers["Content-Type"] == "application/json"


class TestGenerateStreaming:
    def _patch_post(self, monkeypatch, response):
        # generate_streaming references the bare name ``requests``; make sure it
        # resolves to the real module, then stub out ``post``.
        monkeypatch.setattr(streaming_nlg, "requests", requests, raising=False)
        monkeypatch.setattr(requests, "post", lambda *a, **k: response)

    def test_yields_content_chunks(self, monkeypatch):
        lines = [
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            b"",
            b'data: {"choices": [{"delta": {"content": " world"}}]}',
            b"data: [DONE]",
        ]
        self._patch_post(monkeypatch, FakeResponse(lines=lines))
        nlg = StreamingNLG("http://x", "k")
        assert "".join(nlg.generate_streaming("prompt")) == "Hello world"

    def test_skips_malformed_json_lines(self, monkeypatch):
        lines = [
            b"data: not-json",
            b'data: {"choices": [{"delta": {"content": "ok"}}]}',
        ]
        self._patch_post(monkeypatch, FakeResponse(lines=lines))
        nlg = StreamingNLG("http://x", "k")
        assert "".join(nlg.generate_streaming("prompt")) == "ok"

    def test_request_exception_yields_error_chunk(self, monkeypatch):
        monkeypatch.setattr(streaming_nlg, "requests", requests, raising=False)

        def raise_conn(*a, **k):
            raise requests.exceptions.ConnectionError("down")

        monkeypatch.setattr(requests, "post", raise_conn)
        nlg = StreamingNLG("http://x", "k")
        out = "".join(nlg.generate_streaming("prompt"))
        assert out.startswith("[Error:")
        assert "down" in out


class TestGenerateAnswer:
    def test_returns_model_content(self, monkeypatch):
        response = FakeResponse(
            json_data={"choices": [{"message": {"content": "ZA Bank has 501-1000 employees."}}]}
        )
        monkeypatch.setattr(requests, "post", lambda *a, **k: response)
        nlg = StreamingNLG("http://x", "k")
        answer = nlg.generate_answer("size?", {"employees": "501-1000"})
        assert answer == "ZA Bank has 501-1000 employees."

    def test_missing_choices_falls_back(self, monkeypatch):
        response = FakeResponse(json_data={"choices": []})
        monkeypatch.setattr(requests, "post", lambda *a, **k: response)
        nlg = StreamingNLG("http://x", "k")
        answer = nlg.generate_answer("my query", {})
        assert answer == "Based on the data, my query"

    def test_exception_falls_back(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr(requests, "post", boom)
        nlg = StreamingNLG("http://x", "k")
        answer = nlg.generate_answer("my query", {})
        assert answer == "Based on the data, my query"
