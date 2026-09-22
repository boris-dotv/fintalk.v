#!/usr/bin/env python3
"""Unit tests for RejectionDetector fallback keyword ordering.

The digit regex is checked first; when it does not match, the fallback scans
for accept keywords before reject keywords. These tests lock in that
precedence so a refactor cannot silently flip the decision.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestKeywordOrdering(unittest.TestCase):
    def _detector(self, output):
        return RejectionDetector(lambda prompt, temperature=0.1: output)

    def test_accept_keyword_wins_over_reject_keyword(self):
        # "yes" (accept) appears before "no" (reject) in the scan order
        self.assertTrue(self._detector("yes, but no").should_accept("hello"))

    def test_accept_keyword_alone(self):
        self.assertTrue(self._detector("within scope").should_accept("hello"))

    def test_reject_keyword_alone(self):
        self.assertFalse(self._detector("out of scope").should_accept("hello"))

    def test_reject_keyword_unrelated(self):
        self.assertFalse(self._detector("unrelated topic").should_accept("hello"))

    def test_digit_takes_precedence_over_keywords(self):
        # A bare 0 must reject even though "accept" appears in the text
        self.assertFalse(self._detector("0 (do not accept)").should_accept("hello"))

    def test_unparseable_defaults_to_accept(self):
        self.assertTrue(self._detector("maybe?").should_accept("hello"))

    def test_none_output_defaults_to_accept(self):
        self.assertTrue(self._detector(None).should_accept("hello"))


if __name__ == "__main__":
    unittest.main()
