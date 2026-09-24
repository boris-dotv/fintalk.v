#!/usr/bin/env python3
"""Unit tests for RejectionDetector fallback keyword precedence.

When the LLM output contains no bare 0/1 digit, should_accept falls back
to a keyword scan. The accept keywords are checked before the reject
keywords, so an output containing both must resolve to Accept. An output
containing only a reject keyword must resolve to Reject, and an output
with neither must fall back to the safe default (Accept).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestHeuristicPrecedence(unittest.TestCase):
    def _detector(self, return_value):
        return RejectionDetector(lambda prompt, temperature=0.1: return_value)

    def test_accept_keyword_alone_accepts(self):
        for output in ("accept", "yes", "within scope"):
            with self.subTest(output=output):
                self.assertTrue(self._detector(output).should_accept("q"))

    def test_reject_keyword_alone_rejects(self):
        for output in ("reject", "no", "out of scope", "unrelated"):
            with self.subTest(output=output):
                self.assertFalse(self._detector(output).should_accept("q"))

    def test_accept_keyword_wins_when_both_present(self):
        self.assertTrue(
            self._detector("yes, but no").should_accept("q")
        )

    def test_keyword_match_is_case_insensitive(self):
        self.assertTrue(self._detector("ACCEPT").should_accept("q"))
        self.assertFalse(self._detector("REJECT").should_accept("q"))

    def test_no_keyword_defaults_to_accept(self):
        self.assertTrue(self._detector("maybe later").should_accept("q"))

    def test_none_output_defaults_to_accept(self):
        self.assertTrue(self._detector(None).should_accept("q"))


if __name__ == "__main__":
    unittest.main()
