#!/usr/bin/env python3
"""Unit tests for FinancialFunctionRegistry dispatch and helper contracts.

These tests lock in the observable behaviour of execute() and the small
pure helpers: unknown function names and missing parameters must return an
error dict (never raise), and _get_company_id must return None when no
company name or no database is available.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.function_registry import (  # noqa: E402
    FINANCIAL_FUNCTIONS,
    FinancialFunctionRegistry,
)


class TestGetFunctions(unittest.TestCase):
    def test_returns_declared_function_list(self):
        registry = FinancialFunctionRegistry()
        self.assertIs(registry.get_functions(), FINANCIAL_FUNCTIONS)

    def test_every_function_has_name_and_parameters(self):
        for entry in FINANCIAL_FUNCTIONS:
            self.assertEqual(entry["type"], "function")
            fn = entry["function"]
            self.assertTrue(fn["name"])
            self.assertEqual(fn["parameters"]["type"], "object")


class TestExecuteDispatch(unittest.TestCase):
    def setUp(self):
        self.registry = FinancialFunctionRegistry()

    def test_unknown_function_returns_error_dict(self):
        result = self.registry.execute("does_not_exist", {})
        self.assertEqual(result, {"error": "Unknown function: does_not_exist"})

    def test_missing_required_parameter_returns_error_dict(self):
        # get_company_info requires company_name; KeyError must be caught
        # and converted into an error dict rather than propagating.
        result = self.registry.execute("get_company_info", {})
        self.assertIn("error", result)
        self.assertIn("company_name", result["error"])

    def test_known_function_without_db_returns_error_dict(self):
        # No db and no osworld adapter -> _get_company_id returns None ->
        # the function reports a not-found error instead of raising.
        result = self.registry.execute("get_company_info", {"company_name": "ZA Bank"})
        self.assertIn("error", result)
        self.assertIn("ZA Bank", result["error"])


class TestGetCompanyId(unittest.TestCase):
    def setUp(self):
        self.registry = FinancialFunctionRegistry()

    def test_empty_name_returns_none(self):
        self.assertIsNone(self.registry._get_company_id(""))

    def test_whitespace_name_returns_none(self):
        self.assertIsNone(self.registry._get_company_id("   "))

    def test_no_backend_returns_none(self):
        self.assertIsNone(self.registry._get_company_id("ZA Bank"))


class TestCalculateConcentration(unittest.TestCase):
    def test_error_propagates_from_top_shareholders(self):
        registry = FinancialFunctionRegistry()
        result = registry._calculate_concentration("ZA Bank", 3)
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
