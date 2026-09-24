#!/usr/bin/env python3
"""Unit tests for RejectionDetector behaviour around the llm_caller.

These tests lock in two contracts that the existing tests do not cover:

1. When llm_caller raises, should_accept propagates the exception rather
   than silently accepting or rejecting the query.
2. When llm_caller returns None (or an empty string), the detector falls
   back to the safe default of accepting the query.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestLlmCallerErrors(unittest.TestCase):
    def test_exception_from_llm_caller_propagates(self):
        def boom(prompt, temperature=0.1):
            raise RuntimeError("llm unavailable")

        detector = RejectionDetector(boom)
        with self.assertRaises(RuntimeError):
            detector.should_accept("How many employees does ZA Bank have?")

    def test_none_result_defaults_to_accept(self):
        detector = RejectionDetector(lambda prompt, temperature=0.1: None)
        self.assertTrue(detector.should_accept("Hello"))

    def test_empty_string_result_defaults_to_accept(self):
        detector = RejectionDetector(lambda prompt, temperature=0.1: "")
        self.assertTrue(detector.should_accept("Hello"))

    def test_whitespace_only_result_defaults_to_accept(self):
        detector = RejectionDetector(lambda prompt, temperature=0.1: "   \n  ")
        self.assertTrue(detector.should_accept("Hello"))

    def test_prompt_contains_query_and_requests_binary_decision(self):
        captured = {}

        def capture(prompt, temperature=0.1):
            captured["prompt"] = prompt
            captured["temperature"] = temperature
            return "1"

        detector = RejectionDetector(capture)
        self.assertTrue(detector.should_accept("Compare ZA Bank and WeLab Bank"))
        self.assertIn("Compare ZA Bank and WeLab Bank", captured["prompt"])
        self.assertEqual(captured["temperature"], 0.1)


if __name__ == "__main__":
    unittest.main()
