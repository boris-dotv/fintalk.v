"""Unit tests for formula.py pure logic.

Covers the AST-based safe expression evaluator and the formula lookup
helpers. Only stdlib + loguru are required; no network or API keys.
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from formula import (
    calculate_from_expression,
    find_formula_for_query,
    get_financial_formulas,
)


class TestGetFinancialFormulas(unittest.TestCase):
    def test_returns_name_expression_tuples(self):
        formulas = get_financial_formulas()
        self.assertIsInstance(formulas, list)
        self.assertTrue(formulas)
        for name, expression in formulas:
            self.assertIsInstance(name, str)
            self.assertIsInstance(expression, str)
            self.assertTrue(name)
            self.assertTrue(expression)

    def test_cache_returns_same_object(self):
        self.assertIs(get_financial_formulas(), get_financial_formulas())

    def test_known_formula_present(self):
        names = [name for name, _ in get_financial_formulas()]
        self.assertIn("executive_director_ratio", names)


class TestFindFormulaForQuery(unittest.TestCase):
    def test_finds_formula_and_variables(self):
        name, expr, variables = find_formula_for_query(
            "can you get me the executive_director_ratio for a company?"
        )
        self.assertEqual(name, "executive_director_ratio")
        self.assertIn("Count of Executive Directors", variables)
        self.assertIn("Total Count of Directors", variables)

    def test_unknown_query_returns_none_triple(self):
        self.assertEqual(find_formula_for_query("what is the weather today"), (None, None, None))


class TestCalculateFromExpression(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(calculate_from_expression("1 + 2 * 3", {}), 7.0)

    def test_parentheses_and_unary_minus(self):
        self.assertEqual(calculate_from_expression("-(2 + 3)", {}), -5.0)

    def test_variable_substitution(self):
        result = calculate_from_expression("A / B", {"A": 10.0, "B": 4.0})
        self.assertEqual(result, 2.5)

    def test_longer_variable_names_not_partially_replaced(self):
        # "A" must not be substituted inside "AB".
        result = calculate_from_expression("AB - A", {"A": 1.0, "AB": 5.0})
        self.assertEqual(result, 4.0)

    def test_unknown_variable_returns_nan(self):
        result = calculate_from_expression("A + B", {"A": 1.0})
        self.assertTrue(math.isnan(result))

    def test_division_by_zero_literal_returns_nan(self):
        result = calculate_from_expression("10 / 0", {})
        self.assertTrue(math.isnan(result))

    def test_division_by_zero_variable_returns_nan(self):
        result = calculate_from_expression("A / B", {"A": 10.0, "B": 0.0})
        self.assertTrue(math.isnan(result))

    def test_function_call_is_rejected(self):
        result = calculate_from_expression("__import__('os')", {})
        self.assertTrue(math.isnan(result))

    def test_attribute_access_is_rejected(self):
        result = calculate_from_expression("A.real", {"A": 1.0})
        self.assertTrue(math.isnan(result))

    def test_string_literal_is_rejected(self):
        result = calculate_from_expression("'hello'", {})
        self.assertTrue(math.isnan(result))

    def test_syntax_error_returns_nan(self):
        result = calculate_from_expression("1 +", {})
        self.assertTrue(math.isnan(result))

    def test_unsupported_operator_returns_nan(self):
        # Modulo is not in the safe operator table.
        result = calculate_from_expression("5 % 2", {})
        self.assertTrue(math.isnan(result))

    def test_values_dict_is_not_mutated(self):
        values = {"A": 1.0, "B": 2.0}
        calculate_from_expression("A + B", values)
        self.assertEqual(values, {"A": 1.0, "B": 2.0})


if __name__ == "__main__":
    unittest.main()
