#!/usr/bin/env python3
"""Unit tests for the RejectionDetector prompt construction contract.

These tests lock in the interface between should_accept and the injected
llm_caller: the user query must be embedded verbatim in the prompt, the
prompt must ask for a binary 1/0 decision, and the temperature must be
forwarded as 0.1. A future prompt refactor must not silently drop the
query or change the sampling temperature.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestPromptConstruction(unittest.TestCase):
    def _capture(self, return_value="1"):
        captured = {}

        def caller(prompt, temperature=0.1):
            captured["prompt"] = prompt
            captured["temperature"] = temperature
            return return_value

        return caller, captured

    def test_query_is_embedded_verbatim(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        query = "Compare shareholder concentration between ZA Bank and WeLab Bank"
        detector.should_accept(query)
        self.assertIn(query, captured["prompt"])

    def test_prompt_requests_binary_decision(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        detector.should_accept("Hello")
        prompt = captured["prompt"]
        self.assertIn("1", prompt)
        self.assertIn("0", prompt)
        self.assertIn("accept", prompt.lower())
        self.assertIn("reject", prompt.lower())

    def test_temperature_is_forwarded_as_low_value(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        detector.should_accept("Hello")
        self.assertEqual(captured["temperature"], 0.1)

    def test_llm_caller_is_called_exactly_once_per_query(self):
        calls = []

        def caller(prompt, temperature=0.1):
            calls.append(prompt)
            return "1"

        detector = RejectionDetector(caller)
        detector.should_accept("How many employees does ZA Bank have?")
        self.assertEqual(len(calls), 1)

    def test_unicode_query_is_preserved(self):
        caller, captured = self._capture()
        detector = RejectionDetector(caller)
        query = "\u6bd4\u8f83 ZA Bank \u548c WeLab Bank \u7684\u80a1\u4e1c\u96c6\u4e2d\u5ea6"
        detector.should_accept(query)
        self.assertIn(query, captured["prompt"])


if __name__ == "__main__":
    unittest.main()
