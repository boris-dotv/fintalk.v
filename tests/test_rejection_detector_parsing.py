#!/usr/bin/env python3
"""Unit tests for RejectionDetector response parsing and fallbacks.

Uses a fake llm_caller so no network or heavy deps are needed.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class FakeLLM:
    """Records prompts and returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, prompt, temperature=0.0):
        self.calls.append((prompt, temperature))
        return self.response


class TestDigitParsing(unittest.TestCase):
    def _detect(self, response, query="What is ZA Bank's employee size?"):
        llm = FakeLLM(response)
        detector = RejectionDetector(llm)
        return detector.should_accept(query), llm

    def test_bare_one_accepts(self):
        accept, _ = self._detect("1")
        self.assertTrue(accept)

    def test_bare_zero_rejects(self):
        accept, _ = self._detect("0")
        self.assertFalse(accept)

    def test_whitespace_padded_one_accepts(self):
        accept, _ = self._detect("  1  ")
        self.assertTrue(accept)

    def test_one_with_trailing_text_accepts(self):
        accept, _ = self._detect("1 (accept)")
        self.assertTrue(accept)

    def test_decision_prefix_zero_rejects(self):
        accept, _ = self._detect("Decision: 0")
        self.assertFalse(accept)

    def test_digit_inside_word_is_not_matched(self):
        # '10' has no standalone 0/1 token, so digit parsing must not fire;
        # no accept/reject keyword either, so the safe default (accept) applies.
        accept, _ = self._detect("10")
        self.assertTrue(accept)


class TestKeywordFallback(unittest.TestCase):
    def _detect(self, response):
        llm = FakeLLM(response)
        detector = RejectionDetector(llm)
        return detector.should_accept("hello")

    def test_accept_keyword_accepts(self):
        self.assertTrue(self._detect("ACCEPT"))

    def test_yes_keyword_accepts(self):
        self.assertTrue(self._detect("yes"))

    def test_within_scope_phrase_accepts(self):
        self.assertTrue(self._detect("This is within scope"))

    def test_reject_keyword_rejects(self):
        self.assertFalse(self._detect("REJECT"))

    def test_out_of_scope_phrase_rejects(self):
        self.assertFalse(self._detect("out of scope"))

    def test_unrelated_keyword_rejects(self):
        self.assertFalse(self._detect("unrelated topic"))


class TestSafeDefault(unittest.TestCase):
    def _detect(self, response):
        llm = FakeLLM(response)
        detector = RejectionDetector(llm)
        return detector.should_accept("hello")

    def test_none_response_defaults_to_accept(self):
        self.assertTrue(self._detect(None))

    def test_empty_string_defaults_to_accept(self):
        self.assertTrue(self._detect(""))

    def test_unparseable_text_defaults_to_accept(self):
        self.assertTrue(self._detect("???"))


class TestPromptConstruction(unittest.TestCase):
    def test_query_is_embedded_and_temperature_is_low(self):
        llm = FakeLLM("1")
        detector = RejectionDetector(llm)
        detector.should_accept("ZA Bank employees")
        prompt, temperature = llm.calls[0]
        self.assertIn("Query: ZA Bank employees", prompt)
        self.assertEqual(temperature, 0.1)


if __name__ == "__main__":
    unittest.main()
