#!/usr/bin/env python3
"""Heuristic-fallback unit tests for enhanced_core.rejection_detector.RejectionDetector.

The module only depends on the standard library (logging, re) and takes an
injected llm_caller, so these tests need no network or heavy deps.
"""

import unittest

from enhanced_core.rejection_detector import RejectionDetector


class _Recorder:
    """Callable that records prompts and returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, prompt, temperature=None):
        self.calls.append({"prompt": prompt, "temperature": temperature})
        return self.response


class TestRejectionDetectorHeuristics(unittest.TestCase):
    def test_prompt_contains_query_and_temperature(self):
        rec = _Recorder("1")
        detector = RejectionDetector(rec)
        detector.should_accept("How many employees at ZA Bank?")
        self.assertEqual(len(rec.calls), 1)
        self.assertIn("How many employees at ZA Bank?", rec.calls[0]["prompt"])
        self.assertEqual(rec.calls[0]["temperature"], 0.1)

    def test_accept_keywords_without_digit(self):
        for response in ("accept", "ACCEPT", "Yes", "yes please", "within scope"):
            with self.subTest(response=response):
                detector = RejectionDetector(_Recorder(response))
                self.assertTrue(detector.should_accept("q"))

    def test_reject_keywords_without_digit(self):
        for response in ("reject", "REJECT", "no", "out of scope", "unrelated"):
            with self.subTest(response=response):
                detector = RejectionDetector(_Recorder(response))
                self.assertFalse(detector.should_accept("q"))

    def test_accept_keyword_wins_over_reject_keyword(self):
        # The accept branch is checked first, so a mixed response is accepted.
        detector = RejectionDetector(_Recorder("accept, not reject"))
        self.assertTrue(detector.should_accept("q"))

    def test_unparseable_response_defaults_to_accept(self):
        for response in ("maybe", "???", "42", "", "   ", None):
            with self.subTest(response=response):
                detector = RejectionDetector(_Recorder(response))
                self.assertTrue(detector.should_accept("q"))

    def test_digit_takes_precedence_over_keywords(self):
        # A bare 0 wins even when accept-ish words are present.
        detector = RejectionDetector(_Recorder("0 (reject)"))
        self.assertFalse(detector.should_accept("q"))
        detector = RejectionDetector(_Recorder("1 (accept)"))
        self.assertTrue(detector.should_accept("q"))


if __name__ == "__main__":
    unittest.main()
