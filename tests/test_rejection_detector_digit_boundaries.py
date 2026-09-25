#!/usr/bin/env python3
"""Unit tests for RejectionDetector digit-parsing boundaries.

should_accept first tries to extract a bare 0/1 token using a
word-boundary regex. These tests pin that contract: standalone digits
(with surrounding whitespace or punctuation) decide the outcome, while
digits embedded in larger numbers (10, 2.1, 100) must not match and
fall through to the keyword/default path.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestDigitParsing(unittest.TestCase):
    def _detector(self, return_value):
        return RejectionDetector(lambda prompt, temperature=0.1: return_value)

    def test_bare_one_accepts(self):
        self.assertTrue(self._detector("1").should_accept("q"))

    def test_bare_zero_rejects(self):
        self.assertFalse(self._detector("0").should_accept("q"))

    def test_whitespace_padded_digit(self):
        self.assertTrue(self._detector("  1  ").should_accept("q"))
        self.assertFalse(self._detector("\n0\n").should_accept("q"))

    def test_digit_with_trailing_text(self):
        self.assertTrue(self._detector("1 (accept)").should_accept("q"))
        self.assertFalse(self._detector("0 (reject)").should_accept("q"))

    def test_digit_with_leading_label(self):
        self.assertTrue(self._detector("Decision: 1").should_accept("q"))
        self.assertFalse(self._detector("Decision: 0").should_accept("q"))

    def test_multi_digit_number_does_not_match(self):
        # '10' has no word-boundary-isolated 0/1, so it must fall through
        # to the default (accept) rather than being read as '1'.
        self.assertTrue(self._detector("10").should_accept("q"))

    def test_decimal_number_does_not_match(self):
        self.assertTrue(self._detector("2.1").should_accept("q"))

    def test_integer_result_is_parsed(self):
        self.assertTrue(self._detector(1).should_accept("q"))
        self.assertFalse(self._detector(0).should_accept("q"))

    def test_embedded_digit_with_reject_keyword_rejects(self):
        # No isolated 0/1 token, but the reject keyword is present.
        self.assertFalse(self._detector("score 10, reject").should_accept("q"))


if __name__ == "__main__":
    unittest.main()
