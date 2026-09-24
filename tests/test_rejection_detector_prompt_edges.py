#!/usr/bin/env python3
"""Unit tests for RejectionDetector prompt edge-case handling.

These tests lock in how should_accept embeds unusual queries into the
prompt: empty strings, whitespace-only input, multi-line queries, and
queries that themselves contain the 'Decision:' marker must all be
passed through verbatim so the LLM sees the real query. A future
prompt refactor must not strip, truncate, or otherwise mangle them.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestPromptEdgeCases(unittest.TestCase):
    def _capture(self, return_value="1"):
        captured = {}

        def caller(prompt, temperature=0.1):
            captured["prompt"] = prompt
            captured["temperature"] = temperature
            return return_value

        return caller, captured

    def test_empty_query_still_calls_llm(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        detector.should_accept("")
        self.assertIn("prompt", captured)

    def test_whitespace_query_is_preserved_verbatim(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        query = "   "
        detector.should_accept(query)
        self.assertIn(query, captured["prompt"])

    def test_multiline_query_is_preserved_verbatim(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        query = "Compare ZA Bank\nand WeLab Bank\nshareholders"
        detector.should_accept(query)
        self.assertIn(query, captured["prompt"])

    def test_query_containing_decision_marker_is_preserved(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        query = "What does Decision: 0 mean in the report?"
        detector.should_accept(query)
        self.assertIn(query, captured["prompt"])

    def test_query_with_special_characters_is_preserved(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        query = "ZA Bank's top-5 shareholders (>= 10%)?"
        detector.should_accept(query)
        self.assertIn(query, captured["prompt"])


if __name__ == "__main__":
    unittest.main()
