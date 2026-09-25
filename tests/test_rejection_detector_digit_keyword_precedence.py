#!/usr/bin/env python3
"""Unit tests for RejectionDetector digit-vs-keyword precedence.

should_accept first tries to extract a bare 0/1 token with a
word-boundary regex; only when that fails does it fall back to the
keyword scan (accept keywords first, then reject keywords). These
tests pin that ordering so a refactor cannot let a keyword override an
explicit digit decision, or let a reject keyword win over an accept
keyword.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestDigitBeatsKeyword(unittest.TestCase):
    def _detector(self, return_value):
        return RejectionDetector(lambda prompt, temperature=0.1: return_value)

    def test_digit_one_wins_over_reject_keyword(self):
        # Explicit '1' must accept even though 'reject' appears later.
        self.assertTrue(self._detector("1 reject").should_accept("q"))

    def test_digit_zero_wins_over_accept_keyword(self):
        # Explicit '0' must reject even though 'accept' appears later.
        self.assertFalse(self._detector("0 accept").should_accept("q"))

    def test_digit_zero_wins_over_yes_keyword(self):
        self.assertFalse(self._detector("0 yes").should_accept("q"))

    def test_digit_one_wins_over_out_of_scope_phrase(self):
        self.assertTrue(self._detector("1 out of scope").should_accept("q"))


class TestKeywordScanOrder(unittest.TestCase):
    def _detector(self, return_value):
        return RejectionDetector(lambda prompt, temperature=0.1: return_value)

    def test_accept_keyword_beats_reject_keyword(self):
        # No bare digit, so the keyword scan runs; accept keywords are
        # checked first, so 'accept' wins over 'reject'.
        self.assertTrue(self._detector("accept, not reject").should_accept("q"))

    def test_yes_keyword_beats_no_keyword(self):
        self.assertTrue(self._detector("yes but no").should_accept("q"))

    def test_within_scope_phrase_accepts(self):
        self.assertTrue(self._detector("within scope").should_accept("q"))

    def test_reject_keyword_alone_rejects(self):
        self.assertFalse(self._detector("this is unrelated").should_accept("q"))

    def test_out_of_scope_phrase_rejects(self):
        self.assertFalse(self._detector("out of scope").should_accept("q"))


if __name__ == "__main__":
    unittest.main()
