#!/usr/bin/env python3
"""Unit tests for enhanced_core.correlation_checker.CorrelationChecker."""

import unittest

from enhanced_core.correlation_checker import CorrelationChecker


class TestCorrelationChecker(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def llm_caller(prompt, temperature=0.1):
            self.calls.append((prompt, temperature))
            return self._response

        self._response = "Yes"
        self.checker = CorrelationChecker(llm_caller)

    def test_empty_prev_query_returns_false_without_calling_llm(self):
        self.assertFalse(self.checker.is_correlated("", "What is ZA Bank?"))
        self.assertEqual(self.calls, [])

    def test_empty_curr_query_returns_false_without_calling_llm(self):
        self.assertFalse(self.checker.is_correlated("What is ZA Bank?", ""))
        self.assertEqual(self.calls, [])

    def test_none_queries_return_false(self):
        self.assertFalse(self.checker.is_correlated(None, "x"))
        self.assertFalse(self.checker.is_correlated("x", None))
        self.assertEqual(self.calls, [])

    def test_yes_is_correlated(self):
        self._response = "Yes"
        self.assertTrue(self.checker.is_correlated("a", "b"))

    def test_yes_with_punctuation_is_correlated(self):
        self._response = "Yes."
        self.assertTrue(self.checker.is_correlated("a", "b"))

    def test_yes_with_trailing_text_is_correlated(self):
        self._response = "Yes, they are correlated"
        self.assertTrue(self.checker.is_correlated("a", "b"))

    def test_no_is_not_correlated(self):
        self._response = "No"
        self.assertFalse(self.checker.is_correlated("a", "b"))

    def test_no_with_trailing_text_is_not_correlated(self):
        self._response = "No, unrelated topic"
        self.assertFalse(self.checker.is_correlated("a", "b"))

    def test_unexpected_response_defaults_to_false(self):
        self._response = "Maybe"
        self.assertFalse(self.checker.is_correlated("a", "b"))

    def test_empty_llm_response_defaults_to_false(self):
        self._response = ""
        self.assertFalse(self.checker.is_correlated("a", "b"))

    def test_none_llm_response_defaults_to_false(self):
        self._response = None
        self.assertFalse(self.checker.is_correlated("a", "b"))

    def test_llm_called_with_low_temperature(self):
        self.checker.is_correlated("a", "b")
        self.assertEqual(len(self.calls), 1)
        _, temperature = self.calls[0]
        self.assertEqual(temperature, 0.1)

    def test_prompt_contains_both_queries(self):
        self.checker.is_correlated("first query", "second query")
        prompt, _ = self.calls[0]
        self.assertIn("first query", prompt)
        self.assertIn("second query", prompt)


if __name__ == "__main__":
    unittest.main()
