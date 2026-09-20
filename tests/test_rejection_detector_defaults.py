#!/usr/bin/env python3
"""Unit tests for RejectionDetector unparseable-output fallback.

The module is pure stdlib (logging, re) and takes an injected llm_caller,
so it can be exercised without network or heavy dependencies.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.rejection_detector import RejectionDetector  # noqa: E402


class TestUnparseableDefaultsToAccept(unittest.TestCase):
    def _detector(self, response):
        calls = []

        def llm_caller(prompt, temperature=0.1):
            calls.append((prompt, temperature))
            return response

        return RejectionDetector(llm_caller), calls

    def test_none_response_defaults_to_accept(self):
        detector, calls = self._detector(None)
        self.assertTrue(detector.should_accept("Tell me about ZA Bank"))
        self.assertEqual(len(calls), 1)

    def test_empty_string_defaults_to_accept(self):
        detector, _ = self._detector("")
        self.assertTrue(detector.should_accept("Tell me about ZA Bank"))

    def test_whitespace_only_defaults_to_accept(self):
        detector, _ = self._detector("   \n  ")
        self.assertTrue(detector.should_accept("Tell me about ZA Bank"))

    def test_gibberish_without_keywords_defaults_to_accept(self):
        detector, _ = self._detector("??? maybe perhaps")
        self.assertTrue(detector.should_accept("Tell me about ZA Bank"))

    def test_multi_digit_output_defaults_to_accept(self):
        # '10' has no bare 0/1 word boundary match and no keywords
        detector, _ = self._detector("10")
        self.assertTrue(detector.should_accept("Tell me about ZA Bank"))

    def test_prompt_embeds_query(self):
        detector, calls = self._detector("1")
        detector.should_accept("Compare ZA Bank and WeLab Bank")
        prompt, temperature = calls[0]
        self.assertIn("Compare ZA Bank and WeLab Bank", prompt)
        self.assertEqual(temperature, 0.1)


if __name__ == "__main__":
    unittest.main()
