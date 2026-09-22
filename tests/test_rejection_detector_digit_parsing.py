#!/usr/bin/env python3
"""Tests for RejectionDetector digit-parsing boundary behaviour.

Locks in the contract of the regex used to parse the LLM decision:
  - a bare 0/1 anywhere in the output is the decision
  - digits embedded in longer numbers (10, 2024) are NOT decisions
  - the first matching digit wins when several appear
"""

import unittest

from enhanced_core.rejection_detector import RejectionDetector


class _Recorder:
    """Fake llm_caller that always returns a fixed string."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, prompt, temperature=0.1):
        self.calls.append({"prompt": prompt, "temperature": temperature})
        return self.response


class TestDigitParsing(unittest.TestCase):
    def _detector(self, response):
        return RejectionDetector(_Recorder(response))

    def test_bare_one_accepts(self):
        self.assertTrue(self._detector("1").should_accept("hello"))

    def test_bare_zero_rejects(self):
        self.assertFalse(self._detector("0").should_accept("hello"))

    def test_padded_one_accepts(self):
        self.assertTrue(self._detector("   1   ").should_accept("hello"))

    def test_decision_prefix_zero_rejects(self):
        self.assertFalse(self._detector("Decision: 0").should_accept("hello"))

    def test_embedded_digit_in_longer_number_is_not_a_decision(self):
        # '10' contains a '1' but \b([01])\b must not match inside it.
        # No keywords present -> unparseable -> safe default accept.
        self.assertTrue(self._detector("10").should_accept("hello"))

    def test_year_like_number_is_not_a_decision(self):
        self.assertTrue(self._detector("2024").should_accept("hello"))

    def test_first_matching_digit_wins(self):
        # '1' appears before '0' -> accept.
        self.assertTrue(self._detector("1 then 0").should_accept("hello"))

    def test_zero_before_one_rejects(self):
        self.assertFalse(self._detector("0 then 1").should_accept("hello"))

    def test_none_response_defaults_to_accept(self):
        self.assertTrue(self._detector(None).should_accept("hello"))

    def test_empty_response_defaults_to_accept(self):
        self.assertTrue(self._detector("").should_accept("hello"))

    def test_llm_caller_receives_query_in_prompt(self):
        rec = _Recorder("1")
        detector = RejectionDetector(rec)
        detector.should_accept("unique-marker-query")
        self.assertEqual(len(rec.calls), 1)
        self.assertIn("unique-marker-query", rec.calls[0]["prompt"])


if __name__ == "__main__":
    unittest.main()
