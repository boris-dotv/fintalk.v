#!/usr/bin/env python3
"""Edge-case unit tests for enhanced_core.correlation_checker.CorrelationChecker.

The module only depends on the standard library (logging) and takes an
injected llm_caller, so these tests need no network or heavy deps.
"""

import unittest

from enhanced_core.correlation_checker import CorrelationChecker


class _Recorder:
    """Callable that records prompts and returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, prompt, temperature=None):
        self.calls.append({"prompt": prompt, "temperature": temperature})
        return self.response


class TestCorrelationCheckerEdgeCases(unittest.TestCase):
    def test_empty_prev_query_short_circuits(self):
        rec = _Recorder("Yes")
        checker = CorrelationChecker(rec)
        self.assertFalse(checker.is_correlated("", "current"))
        self.assertEqual(rec.calls, [])

    def test_empty_curr_query_short_circuits(self):
        rec = _Recorder("Yes")
        checker = CorrelationChecker(rec)
        self.assertFalse(checker.is_correlated("previous", ""))
        self.assertEqual(rec.calls, [])

    def test_none_queries_short_circuit(self):
        rec = _Recorder("Yes")
        checker = CorrelationChecker(rec)
        self.assertFalse(checker.is_correlated(None, "current"))
        self.assertFalse(checker.is_correlated("previous", None))
        self.assertEqual(rec.calls, [])

    def test_prompt_contains_both_queries(self):
        rec = _Recorder("Yes")
        checker = CorrelationChecker(rec)
        checker.is_correlated("first query", "second query")
        prompt = rec.calls[0]["prompt"]
        self.assertIn("first query", prompt)
        self.assertIn("second query", prompt)
        self.assertEqual(rec.calls[0]["temperature"], 0.1)

    def test_yes_variants_are_correlated(self):
        for response in ("Yes", "yes", "YES", "  Yes  ", "Yes, they are correlated", "Yes."):
            with self.subTest(response=response):
                checker = CorrelationChecker(_Recorder(response))
                self.assertTrue(checker.is_correlated("a", "b"))

    def test_no_variants_are_not_correlated(self):
        for response in ("No", "no", "NO", "  No  ", "No, unrelated"):
            with self.subTest(response=response):
                checker = CorrelationChecker(_Recorder(response))
                self.assertFalse(checker.is_correlated("a", "b"))

    def test_empty_response_defaults_to_false(self):
        for response in ("", "   ", None):
            with self.subTest(response=response):
                checker = CorrelationChecker(_Recorder(response))
                self.assertFalse(checker.is_correlated("a", "b"))

    def test_unexpected_response_defaults_to_false(self):
        for response in ("Maybe", "I think so", "42"):
            with self.subTest(response=response):
                checker = CorrelationChecker(_Recorder(response))
                self.assertFalse(checker.is_correlated("a", "b"))


if __name__ == "__main__":
    unittest.main()
