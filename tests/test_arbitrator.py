#!/usr/bin/env python3
"""Unit tests for enhanced_core.arbitrator.QueryArbitrator."""

import unittest

from enhanced_core.arbitrator import ArbitrationResult, QueryArbitrator


class TestQueryArbitrator(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def llm_caller(prompt, temperature=0.1):
            self.calls.append((prompt, temperature))
            return self._response

        self._response = "A"
        self.arbitrator = QueryArbitrator(llm_caller)

    def test_empty_query_returns_invalid_without_calling_llm(self):
        result = self.arbitrator.arbitrate("")
        self.assertIsInstance(result, ArbitrationResult)
        self.assertEqual(result.query_type, "invalid")
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(self.calls, [])

    def test_whitespace_query_returns_invalid_without_calling_llm(self):
        result = self.arbitrator.arbitrate("   \n\t ")
        self.assertEqual(result.query_type, "invalid")
        self.assertEqual(self.calls, [])

    def test_letter_a_maps_to_task(self):
        self._response = "A"
        result = self.arbitrator.arbitrate("What is ZA Bank's employee size?")
        self.assertEqual(result.query_type, "task")
        self.assertEqual(result.confidence, 0.8)

    def test_letter_b_maps_to_knowledge(self):
        self._response = "B"
        result = self.arbitrator.arbitrate("How is executive_director_ratio calculated?")
        self.assertEqual(result.query_type, "knowledge")

    def test_letter_c_maps_to_small_talk(self):
        self._response = "C"
        result = self.arbitrator.arbitrate("Hello")
        self.assertEqual(result.query_type, "small_talk")

    def test_letter_d_maps_to_invalid(self):
        self._response = "D"
        result = self.arbitrator.arbitrate("asdfgh")
        self.assertEqual(result.query_type, "invalid")

    def test_lowercase_letter_is_accepted(self):
        self._response = "b"
        result = self.arbitrator.arbitrate("What does concentration mean?")
        self.assertEqual(result.query_type, "knowledge")

    def test_letter_with_whitespace_is_accepted(self):
        self._response = "  C  "
        result = self.arbitrator.arbitrate("Thanks")
        self.assertEqual(result.query_type, "small_talk")

    def test_unexpected_letter_defaults_to_task(self):
        self._response = "Z"
        result = self.arbitrator.arbitrate("some query")
        self.assertEqual(result.query_type, "task")

    def test_none_response_defaults_to_task(self):
        self._response = None
        result = self.arbitrator.arbitrate("some query")
        self.assertEqual(result.query_type, "task")

    def test_non_string_response_defaults_to_task(self):
        self._response = 42
        result = self.arbitrator.arbitrate("some query")
        self.assertEqual(result.query_type, "task")

    def test_reasoning_is_non_empty_string(self):
        self._response = "A"
        result = self.arbitrator.arbitrate("some query")
        self.assertIsInstance(result.reasoning, str)
        self.assertTrue(result.reasoning)

    def test_history_included_in_prompt(self):
        self.arbitrator.arbitrate("follow up", history="previous turn")
        prompt, _ = self.calls[0]
        self.assertIn("previous turn", prompt)

    def test_no_history_uses_placeholder(self):
        self.arbitrator.arbitrate("some query")
        prompt, _ = self.calls[0]
        self.assertIn("No history", prompt)

    def test_llm_called_with_low_temperature(self):
        self.arbitrator.arbitrate("some query")
        _, temperature = self.calls[0]
        self.assertEqual(temperature, 0.1)


if __name__ == "__main__":
    unittest.main()
