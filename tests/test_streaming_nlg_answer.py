#!/usr/bin/env python3
"""Unit tests for StreamingNLG.generate_answer success and fallback paths.

These tests stub the 'requests' module via sys.modules so no network access
is required. The module imports requests lazily inside generate_answer, so
installing the stub before calling is sufficient.
"""

import json
import sys
import types
import unittest


class _FakeResponse:
    def __init__(self, payload=None, raise_exc=None):
        self._payload = payload
        self._raise_exc = raise_exc
        self.closed = False

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._payload

    def close(self):
        self.closed = True


class _FakeRequests(types.ModuleType):
    """Minimal stand-in for the requests module used by StreamingNLG."""

    def __init__(self):
        super().__init__("requests")
        self.post_calls = []
        self.next_response = None
        self.next_exception = None

        class _Exceptions:
            class RequestException(Exception):
                pass

        self.exceptions = _Exceptions

    def post(self, url, headers=None, json=None, timeout=None, stream=False):
        self.post_calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
                "stream": stream,
            }
        )
        if self.next_exception is not None:
            raise self.next_exception
        return self.next_response


class TestGenerateAnswerSuccess(unittest.TestCase):
    def setUp(self):
        self.fake_requests = _FakeRequests()
        self._saved_requests = sys.modules.get("requests")
        sys.modules["requests"] = self.fake_requests

        from enhanced_core.streaming_nlg import StreamingNLG

        self.nlg = StreamingNLG(api_url="http://example.test/v1", api_key="secret")

    def tearDown(self):
        if self._saved_requests is None:
            sys.modules.pop("requests", None)
        else:
            sys.modules["requests"] = self._saved_requests

    def _set_choices(self, content):
        self.fake_requests.next_response = _FakeResponse(
            payload={"choices": [{"message": {"content": content}}]}
        )

    def test_invalid_data_returns_message_without_http(self):
        self.assertEqual(
            self.nlg.generate_answer("q", {}),
            "抱歉，查询结果为空或格式不正确。",
        )
        self.assertEqual(self.fake_requests.post_calls, [])

    def test_non_dict_data_returns_message_without_http(self):
        self.assertEqual(
            self.nlg.generate_answer("q", ["a", "b"]),
            "抱歉，查询结果为空或格式不正确。",
        )
        self.assertEqual(self.fake_requests.post_calls, [])

    def test_empty_query_returns_message_without_http(self):
        self.assertEqual(
            self.nlg.generate_answer("   ", {"rows": [1]}),
            "抱歉，查询内容为空。",
        )
        self.assertEqual(self.fake_requests.post_calls, [])

    def test_success_returns_choice_content(self):
        self._set_choices("ZA Bank has 3 shareholders.")
        answer = self.nlg.generate_answer("How many?", {"rows": [{"n": 3}]})
        self.assertEqual(answer, "ZA Bank has 3 shareholders.")

    def test_prompt_contains_query_and_data(self):
        self._set_choices("ok")
        self.nlg.generate_answer("How many shareholders?", {"count": 7})
        payload = self.fake_requests.post_calls[0]["json"]
        prompt = payload["messages"][0]["content"]
        self.assertIn("How many shareholders?", prompt)
        self.assertIn("7", prompt)

    def test_uses_deepseek_chat_model_and_timeout(self):
        self._set_choices("ok")
        self.nlg.generate_answer("q", {"a": 1})
        call = self.fake_requests.post_calls[0]
        self.assertEqual(call["json"]["model"], "deepseek-chat")
        self.assertEqual(call["timeout"], 30)
        self.assertFalse(call["stream"])

    def test_large_data_is_truncated_in_prompt(self):
        self._set_choices("ok")
        big = {"blob": "x" * 20000}
        self.nlg.generate_answer("q", big)
        prompt = self.fake_requests.post_calls[0]["json"]["messages"][0]["content"]
        self.assertIn("... (truncated)", prompt)
        # The full untruncated blob must not appear in the prompt.
        self.assertNotIn("x" * 6000, prompt)

    def test_small_data_is_not_truncated(self):
        self._set_choices("ok")
        self.nlg.generate_answer("q", {"a": 1})
        prompt = self.fake_requests.post_calls[0]["json"]["messages"][0]["content"]
        self.assertNotIn("... (truncated)", prompt)

    def test_missing_choices_falls_back(self):
        self.fake_requests.next_response = _FakeResponse(payload={"choices": []})
        answer = self.nlg.generate_answer("my query", {"a": 1})
        self.assertEqual(answer, "Based on the data, my query")

    def test_http_exception_falls_back(self):
        self.fake_requests.next_exception = RuntimeError("boom")
        answer = self.nlg.generate_answer("my query", {"a": 1})
        self.assertEqual(answer, "Based on the data, my query")

    def test_authorization_header_uses_api_key(self):
        self._set_choices("ok")
        self.nlg.generate_answer("q", {"a": 1})
        headers = self.fake_requests.post_calls[0]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer secret")


if __name__ == "__main__":
    unittest.main()
