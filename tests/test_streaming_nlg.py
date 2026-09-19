#!/usr/bin/env python3
"""Unit tests for enhanced_core.streaming_nlg.StreamingNLG input validation."""

import sys
import types
import unittest

# Stub 'requests' before importing the module under test so no network
# dependency is required. The validation paths under test never touch it.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _RequestException(Exception):
        pass

    exceptions_stub = types.ModuleType("requests.exceptions")
    exceptions_stub.RequestException = _RequestException
    requests_stub.exceptions = exceptions_stub

    def _post(*args, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("requests.post should not be called for invalid input")

    requests_stub.post = _post
    sys.modules["requests"] = requests_stub
    sys.modules["requests.exceptions"] = exceptions_stub

from enhanced_core.streaming_nlg import StreamingNLG


class TestGenerateAnswerValidation(unittest.TestCase):
    def setUp(self):
        self.nlg = StreamingNLG("http://example.invalid/api", "test-key")

    def test_empty_dict_returns_chinese_fallback(self):
        result = self.nlg.generate_answer("query", {})
        self.assertEqual(result, "抱歉，查询结果为空或格式不正确。")

    def test_none_data_returns_chinese_fallback(self):
        result = self.nlg.generate_answer("query", None)
        self.assertEqual(result, "抱歉，查询结果为空或格式不正确。")

    def test_non_dict_data_returns_chinese_fallback(self):
        result = self.nlg.generate_answer("query", [1, 2, 3])
        self.assertEqual(result, "抱歉，查询结果为空或格式不正确。")

    def test_empty_query_returns_query_fallback(self):
        result = self.nlg.generate_answer("", {"rows": [1]})
        self.assertEqual(result, "抱歉，查询内容为空。")

    def test_whitespace_query_returns_query_fallback(self):
        result = self.nlg.generate_answer("   \n\t ", {"rows": [1]})
        self.assertEqual(result, "抱歉，查询内容为空。")

    def test_non_string_query_returns_query_fallback(self):
        result = self.nlg.generate_answer(123, {"rows": [1]})
        self.assertEqual(result, "抱歉，查询内容为空。")

    def test_headers_use_bearer_token(self):
        self.assertEqual(
            self.nlg.headers.get("Authorization"), "Bearer test-key"
        )


class TestGenerateStreamingValidation(unittest.TestCase):
    def setUp(self):
        self.nlg = StreamingNLG("http://example.invalid/api", "test-key")

    def test_empty_prompt_yields_error_chunk(self):
        chunks = list(self.nlg.generate_streaming(""))
        self.assertEqual(chunks, ["[Error: Empty prompt]"])

    def test_whitespace_prompt_yields_error_chunk(self):
        chunks = list(self.nlg.generate_streaming("   \n"))
        self.assertEqual(chunks, ["[Error: Empty prompt]"])

    def test_non_string_prompt_yields_error_chunk(self):
        chunks = list(self.nlg.generate_streaming(None))
        self.assertEqual(chunks, ["[Error: Empty prompt]"])


if __name__ == "__main__":
    unittest.main()
