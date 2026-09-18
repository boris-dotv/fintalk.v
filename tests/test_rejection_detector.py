#!/usr/bin/env python3
"""Unit tests for enhanced_core.rejection_detector.RejectionDetector parsing.

These tests only exercise the pure parsing/fallback logic with a stub
llm_caller, so no network or API keys are required.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_core.rejection_detector import RejectionDetector


class TestRejectionDetectorParsing(unittest.TestCase):
    def _make(self, response):
        return RejectionDetector(lambda prompt, temperature=0.1: response)

    def test_plain_one_accepts(self):
        self.assertTrue(self._make("1").should_accept("hello"))

    def test_plain_zero_rejects(self):
        self.assertFalse(self._make("0").should_accept("sports scores"))

    def test_whitespace_around_digit(self):
        self.assertTrue(self._make("   1   ").should_accept("hi"))
        self.assertFalse(self._make("\n0\n").should_accept("cook pasta"))

    def test_digit_with_trailing_text(self):
        self.assertTrue(self._make("1 (accept)").should_accept("hi"))
        self.assertFalse(self._make("Decision: 0").should_accept("cook pasta"))

    def test_none_response_defaults_to_accept(self):
        self.assertTrue(self._make(None).should_accept("hi"))

    def test_empty_string_defaults_to_accept(self):
        self.assertTrue(self._make("").should_accept("hi"))

    def test_heuristic_accept_keyword(self):
        self.assertTrue(self._make("This is within scope").should_accept("hi"))

    def test_heuristic_reject_keyword(self):
        self.assertFalse(self._make("out of scope").should_accept("cook pasta"))

    def test_unparseable_defaults_to_accept(self):
        self.assertTrue(self._make("???").should_accept("hi"))


if __name__ == "__main__":
    unittest.main()
