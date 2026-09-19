#!/usr/bin/env python3
"""Unit tests for QueryArbitrator response parsing edge cases.

Uses a fake llm_caller so no network or heavy deps are needed.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.arbitrator import ArbitrationResult, QueryArbitrator  # noqa: E402


class FakeLLM:
    """Records prompts and returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, prompt, temperature=0.0):
        self.calls.append((prompt, temperature))
        return self.response


class TestEmptyQueryShortCircuit(unittest.TestCase):
    def test_empty_string_is_invalid_without_llm_call(self):
        llm = FakeLLM("A")
        arb = QueryArbitrator(llm)
        result = arb.arbitrate("")
        self.assertIsInstance(result, ArbitrationResult)
        self.assertEqual(result.query_type, "invalid")
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(llm.calls, [])

    def test_whitespace_only_is_invalid_without_llm_call(self):
        llm = FakeLLM("A")
        arb = QueryArbitrator(llm)
        result = arb.arbitrate("   \t  ")
        self.assertEqual(result.query_type, "invalid")
        self.assertEqual(llm.calls, [])

    def test_none_query_is_invalid(self):
        llm = FakeLLM("A")
        arb = QueryArbitrator(llm)
        result = arb.arbitrate(None)
        self.assertEqual(result.query_type, "invalid")
        self.assertEqual(llm.calls, [])


class TestResponseParsing(unittest.TestCase):
    def _arbitrate(self, response, query="What is ZA Bank's employee size?"):
        llm = FakeLLM(response)
        arb = QueryArbitrator(llm)
        return arb.arbitrate(query), llm

    def test_letter_a_maps_to_task(self):
        result, _ = self._arbitrate("A")
        self.assertEqual(result.query_type, "task")
        self.assertEqual(result.confidence, 0.8)

    def test_letter_b_maps_to_knowledge(self):
        result, _ = self._arbitrate("B")
        self.assertEqual(result.query_type, "knowledge")

    def test_letter_c_maps_to_small_talk(self):
        result, _ = self._arbitrate("C")
        self.assertEqual(result.query_type, "small_talk")

    def test_letter_d_maps_to_invalid(self):
        result, _ = self._arbitrate("D")
        self.assertEqual(result.query_type, "invalid")

    def test_lowercase_letter_is_uppercased(self):
        result, _ = self._arbitrate("b")
        self.assertEqual(result.query_type, "knowledge")

    def test_surrounding_whitespace_is_stripped(self):
        result, _ = self._arbitrate("  C  ")
        self.assertEqual(result.query_type, "small_talk")

    def test_unexpected_letter_defaults_to_task(self):
        result, _ = self._arbitrate("Z")
        self.assertEqual(result.query_type, "task")

    def test_none_response_defaults_to_task(self):
        result, _ = self._arbitrate(None)
        self.assertEqual(result.query_type, "task")

    def test_non_string_response_defaults_to_task(self):
        result, _ = self._arbitrate({"answer": "A"})
        self.assertEqual(result.query_type, "task")

    def test_empty_string_response_defaults_to_task(self):
        result, _ = self._arbitrate("")
        self.assertEqual(result.query_type, "task")


class TestPromptConstruction(unittest.TestCase):
    def test_query_is_stripped_before_prompt(self):
        llm = FakeLLM("A")
        arb = QueryArbitrator(llm)
        arb.arbitrate("   hello there   ")
        prompt, temperature = llm.calls[0]
        self.assertIn("Query: hello there", prompt)
        self.assertEqual(temperature, 0.1)

    def test_empty_history_uses_placeholder(self):
        llm = FakeLLM("A")
        arb = QueryArbitrator(llm)
        arb.arbitrate("hello")
        prompt, _ = llm.calls[0]
        self.assertIn("Context: No history", prompt)

    def test_history_is_embedded_when_provided(self):
        llm = FakeLLM("A")
        arb = QueryArbitrator(llm)
        arb.arbitrate("hello", history="user: hi")
        prompt, _ = llm.calls[0]
        self.assertIn("Context: user: hi", prompt)


if __name__ == "__main__":
    unittest.main()
