#!/usr/bin/env python3
"""Unit tests for enhanced_core/function_registry.py pure dispatch logic.

Uses an in-memory sqlite3 database so no network or heavy deps are needed.
"""

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.function_registry import (  # noqa: E402
    FINANCIAL_FUNCTIONS,
    FinancialFunctionRegistry,
)


SCHEMA = """
CREATE TABLE companies (
    company_sort_id INTEGER PRIMARY KEY,
    name TEXT
);
CREATE TABLE management (
    company_sort_id INTEGER,
    director_type TEXT
);
CREATE TABLE shareholders (
    company_sort_id INTEGER,
    shareholder_name TEXT,
    share_percentage TEXT
);
"""


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO companies VALUES (1, 'ZA Bank')")
    conn.execute("INSERT INTO companies VALUES (2, 'WeLab Bank')")
    conn.execute("INSERT INTO management VALUES (1, 'Executive Director')")
    conn.execute("INSERT INTO management VALUES (1, 'Non-Executive Director')")
    conn.execute("INSERT INTO management VALUES (1, NULL)")
    conn.execute("INSERT INTO shareholders VALUES (1, 'Alpha', '40%')")
    conn.execute("INSERT INTO shareholders VALUES (1, 'Beta', '25%')")
    conn.execute("INSERT INTO shareholders VALUES (1, 'Gamma', '/')")
    conn.commit()
    return conn


class TestGetFunctions(unittest.TestCase):
    def test_returns_declared_functions(self):
        registry = FinancialFunctionRegistry()
        self.assertEqual(registry.get_functions(), FINANCIAL_FUNCTIONS)

    def test_every_function_has_name(self):
        for entry in FINANCIAL_FUNCTIONS:
            self.assertIn("name", entry["function"])


class TestExecuteDispatch(unittest.TestCase):
    def setUp(self):
        self.registry = FinancialFunctionRegistry(db_connection=make_db())

    def test_unknown_function_returns_error(self):
        result = self.registry.execute("does_not_exist", {})
        self.assertIn("error", result)
        self.assertIn("does_not_exist", result["error"])

    def test_missing_required_parameter_is_caught(self):
        result = self.registry.execute("get_company_info", {})
        self.assertIn("error", result)

    def test_get_company_info_success(self):
        result = self.registry.execute("get_company_info", {"company_name": "ZA Bank"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["company"], "ZA Bank")
        self.assertIn("info", result)

    def test_get_company_info_not_found(self):
        result = self.registry.execute("get_company_info", {"company_name": "Nope Inc"})
        self.assertIn("error", result)

    def test_get_top_shareholders_default_top_n(self):
        result = self.registry.execute("get_top_shareholders", {"company_name": "ZA Bank"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], len(result["top_n_shareholders"]))

    def test_calculate_concentration_skips_slash(self):
        result = self.registry.execute(
            "calculate_shareholder_concentration",
            {"company_name": "ZA Bank", "top_n": 3},
        )
        self.assertEqual(result["status"], "success")
        # 40 + 25 + 0 (the '/' row) == 65.0
        self.assertAlmostEqual(result["concentration"], 65.0)
        self.assertEqual(result["concentration_percentage"], "65.00%")

    def test_compare_companies_picks_higher(self):
        result = self.registry.execute(
            "compare_companies",
            {"company1": "ZA Bank", "company2": "WeLab Bank", "metric": "concentration"},
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["higher"], "ZA Bank")

    def test_compare_companies_missing_company_errors(self):
        result = self.registry.execute(
            "compare_companies",
            {"company1": "ZA Bank", "company2": "Nope Inc", "metric": "concentration"},
        )
        self.assertIn("error", result)


class TestGetCompanyId(unittest.TestCase):
    def setUp(self):
        self.registry = FinancialFunctionRegistry(db_connection=make_db())

    def test_empty_name_returns_none(self):
        self.assertIsNone(self.registry._get_company_id(""))
        self.assertIsNone(self.registry._get_company_id("   "))

    def test_case_insensitive_match(self):
        self.assertEqual(self.registry._get_company_id("za bank"), 1)

    def test_no_match_returns_none(self):
        self.assertIsNone(self.registry._get_company_id("Nonexistent"))

    def test_no_db_returns_none(self):
        registry = FinancialFunctionRegistry()
        self.assertIsNone(registry._get_company_id("ZA Bank"))


if __name__ == "__main__":
    unittest.main()
