#!/usr/bin/env python3
"""Unit tests for RejectionDetector unparseable-output fallback.

These tests lock in the final safety net of should_accept(): when the LLM
output is None, empty, or contains neither a decision digit nor a keyword,
the detector must default to accepting the query and must never raise.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestUnparseableFallback(unittest.TestCase):
    def _detector(self, output):
        return RejectionDetector(lambda prompt, temperature=0.1: output)

    def test_none_output_defaults_to_accept(self):
        self.assertTrue(self._detector(None).should_accept("Hello"))

    def test_empty_string_defaults_to_accept(self):
        self.assertTrue(self._detector("").should_accept("Hello"))

    def test_whitespace_only_defaults_to_accept(self):
        self.assertTrue(self._detector("   \n\t ").should_accept("Hello"))

    def test_gibberish_without_digit_or_keyword_defaults_to_accept(self):
        self.assertTrue(self._detector("???").should_accept("Hello"))

    def test_non_string_output_does_not_raise(self):
        # str() is applied to any non-None value, so an int without a
        # decision digit (e.g. 42) must fall through to the safe default.
        self.assertTrue(self._detector(42).should_accept("Hello"))


if __name__ == "__main__":
    unittest.main()
