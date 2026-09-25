#!/usr/bin/env python3
"""Unit tests for RejectionDetector handling of empty/None LLM output.

When the LLM returns None or a blank string, the digit regex cannot
match and the keyword scan runs against an empty string, so the safe
default (accept) must be returned. These tests pin that contract so a
future refactor cannot silently flip the default to reject on missing
LLM output.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestEmptyOutputDefaultsToAccept(unittest.TestCase):
    def _detector(self, return_value):
        return RejectionDetector(lambda prompt, temperature=0.1: return_value)

    def test_none_output_defaults_to_accept(self):
        self.assertTrue(self._detector(None).should_accept("q"))

    def test_empty_string_defaults_to_accept(self):
        self.assertTrue(self._detector("").should_accept("q"))

    def test_whitespace_only_defaults_to_accept(self):
        self.assertTrue(self._detector("   \n\t  ").should_accept("q"))

    def test_none_output_does_not_raise(self):
        # str(None) would be 'None' which contains no digit or keyword;
        # the None guard must short-circuit before that.
        detector = self._detector(None)
        try:
            detector.should_accept("some query")
        except Exception as exc:  # pragma: no cover - failure path
            self.fail(f"should_accept raised on None output: {exc!r}")

    def test_punctuation_only_defaults_to_accept(self):
        self.assertTrue(self._detector("...").should_accept("q"))


if __name__ == "__main__":
    unittest.main()
