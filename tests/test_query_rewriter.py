#!/usr/bin/env python3
"""Unit tests for enhanced_core.query_rewriter.QueryRewriter pure logic.

These tests use an injected fake llm_caller so no network, API keys or heavy
dependencies are required.
"""

import sys
import unittest
from pathlib import Path

# Ensure the repo root is importable when tests are run from anywhere.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from enhanced_core.query_rewriter import QueryRewriter


class _RecordingCaller:
    """Fake llm_caller that records prompts and returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, prompt, temperature=0.0):
        self.calls.append({"prompt": prompt, "temperature": temperature})
        return self.response


class TestQueryRewriter(unittest.TestCase):
    def test_empty_query_returns_stripped_query_without_calling_llm(self):
        caller = _RecordingCaller("should not be used")
        rewriter = QueryRewriter(caller)
        self.assertEqual(rewriter.rewrite("", "some history"), "")
        self.assertEqual(caller.calls, [])

    def test_whitespace_only_query_is_stripped(self):
        caller = _RecordingCaller("should not be used")
        rewriter = QueryRewriter(caller)
        self.assertEqual(rewriter.rewrite("   ", "some history"), "")
        self.assertEqual(caller.calls, [])

    def test_none_query_returns_none(self):
        caller = _RecordingCaller("should not be used")
        rewriter = QueryRewriter(caller)
        self.assertIsNone(rewriter.rewrite(None, "some history"))
        self.assertEqual(caller.calls, [])

    def test_missing_history_short_circuits(self):
        caller = _RecordingCaller("rewritten")
        rewriter = QueryRewriter(caller)
        self.assertEqual(rewriter.rewrite("What is ZA Bank?", ""), "What is ZA Bank?")
        self.assertEqual(caller.calls, [])

    def test_none_history_short_circuits(self):
        caller = _RecordingCaller("rewritten")
        rewriter = QueryRewriter(caller)
        self.assertEqual(rewriter.rewrite("What is ZA Bank?", None), "What is ZA Bank?")
        self.assertEqual(caller.calls, [])

    def test_good_rewrite_is_returned_stripped(self):
        caller = _RecordingCaller("  What is WeLab Bank's employee size?  ")
        rewriter = QueryRewriter(caller)
        result = rewriter.rewrite("How about WeLab?", "history text")
        self.assertEqual(result, "What is WeLab Bank's employee size?")
        self.assertEqual(len(caller.calls), 1)
        self.assertEqual(caller.calls[0]["temperature"], 0.3)

    def test_empty_llm_response_falls_back_to_original(self):
        caller = _RecordingCaller("")
        rewriter = QueryRewriter(caller)
        self.assertEqual(rewriter.rewrite("How about WeLab?", "history"), "How about WeLab?")

    def test_none_llm_response_falls_back_to_original(self):
        caller = _RecordingCaller(None)
        rewriter = QueryRewriter(caller)
        self.assertEqual(rewriter.rewrite("How about WeLab?", "history"), "How about WeLab?")

    def test_low_overlap_rewrite_is_rejected(self):
        # Completely unrelated characters -> overlap below len(original)/4
        caller = _RecordingCaller("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
        rewriter = QueryRewriter(caller)
        self.assertEqual(rewriter.rewrite("How about WeLab?", "history"), "How about WeLab?")

    def test_prompt_contains_history_and_query(self):
        caller = _RecordingCaller("How about WeLab?")
        rewriter = QueryRewriter(caller)
        rewriter.rewrite("How about WeLab?", "User: hi\nAssistant: hello")
        self.assertEqual(len(caller.calls), 1)
        prompt = caller.calls[0]["prompt"]
        self.assertIn("User: hi", prompt)
        self.assertIn("How about WeLab?", prompt)

    def test_is_bad_rewrite_empty_string(self):
        rewriter = QueryRewriter(_RecordingCaller("x"))
        self.assertTrue(rewriter._is_bad_rewrite("original query", ""))

    def test_is_bad_rewrite_none(self):
        rewriter = QueryRewriter(_RecordingCaller("x"))
        self.assertTrue(rewriter._is_bad_rewrite("original query", None))

    def test_is_bad_rewrite_high_overlap(self):
        rewriter = QueryRewriter(_RecordingCaller("x"))
        self.assertFalse(rewriter._is_bad_rewrite("ZA Bank employees", "ZA Bank employees count"))


if __name__ == "__main__":
    unittest.main()
