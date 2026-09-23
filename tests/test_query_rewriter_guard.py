#!/usr/bin/env python3
"""Unit tests for QueryRewriter.rewrite guard logic.

These tests lock in the observable contract of rewrite(): short-circuit
paths (empty query, empty history), the bad-rewrite fallback, and the
happy path where the LLM output is stripped and returned.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.query_rewriter import QueryRewriter  # noqa: E402


class TestRewriteShortCircuits(unittest.TestCase):
    def test_empty_query_returns_unchanged_without_llm(self):
        calls = []

        def llm(prompt, temperature=0.3):
            calls.append(prompt)
            return "should not be used"

        rewriter = QueryRewriter(llm)
        self.assertEqual(rewriter.rewrite("", "some history"), "")
        self.assertEqual(calls, [])

    def test_whitespace_query_is_stripped_without_llm(self):
        calls = []

        def llm(prompt, temperature=0.3):
            calls.append(prompt)
            return "should not be used"

        rewriter = QueryRewriter(llm)
        self.assertEqual(rewriter.rewrite("   ", "some history"), "")
        self.assertEqual(calls, [])

    def test_empty_history_returns_query_unchanged(self):
        calls = []

        def llm(prompt, temperature=0.3):
            calls.append(prompt)
            return "should not be used"

        rewriter = QueryRewriter(llm)
        self.assertEqual(rewriter.rewrite("What about WeLab?", ""), "What about WeLab?")
        self.assertEqual(calls, [])


class TestRewriteFallbacks(unittest.TestCase):
    def test_falsy_llm_output_falls_back_to_original(self):
        rewriter = QueryRewriter(lambda prompt, temperature=0.3: "")
        self.assertEqual(
            rewriter.rewrite("How about WeLab?", "User: ZA Bank employees?"),
            "How about WeLab?",
        )

    def test_low_overlap_rewrite_falls_back_to_original(self):
        # Completely unrelated output -> overlap below len(original)/4
        rewriter = QueryRewriter(lambda prompt, temperature=0.3: "zzzzzzzzzzzzzzzzzzzz")
        self.assertEqual(
            rewriter.rewrite("How about WeLab?", "User: ZA Bank employees?"),
            "How about WeLab?",
        )

    def test_happy_path_returns_stripped_rewrite(self):
        rewriter = QueryRewriter(
            lambda prompt, temperature=0.3: "  What is WeLab Bank's employee size?  "
        )
        self.assertEqual(
            rewriter.rewrite("How about WeLab?", "User: ZA Bank employees?"),
            "What is WeLab Bank's employee size?",
        )


if __name__ == "__main__":
    unittest.main()
