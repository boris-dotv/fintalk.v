"""Unit tests for formula.py — the financial formula library.

Covers formula loading/caching, natural-language formula lookup, and the
safe AST-based expression evaluator (including error handling).
"""

import math

import pytest

import formula
from formula import (
    _safe_eval_node,
    calculate_from_expression,
    find_formula_for_query,
    get_financial_formulas,
)


@pytest.fixture(autouse=True)
def _reset_formula_cache():
    """Reset the module-level formula cache around every test."""
    original = formula._FORMULA_CACHE
    formula._FORMULA_CACHE = None
    yield
    formula._FORMULA_CACHE = original


class TestGetFinancialFormulas:
    def test_returns_list_of_name_expression_tuples(self):
        formulas = get_financial_formulas()
        assert isinstance(formulas, list)
        assert formulas, "formula list should not be empty"
        for item in formulas:
            assert isinstance(item, tuple)
            assert len(item) == 2
            name, expr = item
            assert isinstance(name, str) and name
            assert isinstance(expr, str) and expr

    def test_contains_known_formulas(self):
        names = {name for name, _ in get_financial_formulas()}
        assert "executive_director_ratio" in names
        assert "employee_growth_rate" in names
        assert "debt_to_equity_ratio" in names

    def test_expression_lookup_matches_expected(self):
        mapping = dict(get_financial_formulas())
        assert mapping["executive_director_ratio"] == (
            "Count of Executive Directors / Total Count of Directors"
        )

    def test_result_is_cached(self):
        first = get_financial_formulas()
        second = get_financial_formulas()
        # Same object returned because of the module-level cache.
        assert first is second
        assert formula._FORMULA_CACHE is first


class TestFindFormulaForQuery:
    def test_finds_formula_in_natural_language_query(self):
        name, expr, variables = find_formula_for_query(
            "can you get me the executive director ratio?"
        )
        assert name == "executive_director_ratio"
        assert expr == "Count of Executive Directors / Total Count of Directors"
        assert variables == [
            "Count of Executive Directors",
            "Total Count of Directors",
        ]

    def test_normalizes_spaces_and_hyphens(self):
        # "executive-director-ratio" should normalize to the underscore name.
        name, _, _ = find_formula_for_query("executive-director-ratio please")
        assert name == "executive_director_ratio"

    def test_extracts_variables_from_growth_expression(self):
        name, expr, variables = find_formula_for_query("employee_growth_rate")
        assert name == "employee_growth_rate"
        # The expression references "Previous Year Employees" twice, and the
        # splitter does not de-duplicate, so it appears twice.
        assert variables == [
            "Current Year Employees",
            "Previous Year Employees",
            "Previous Year Employees",
        ]

    def test_returns_none_tuple_when_not_found(self):
        result = find_formula_for_query("what is the weather today")
        assert result == (None, None, None)


class TestCalculateFromExpression:
    def test_basic_division(self):
        result = calculate_from_expression(
            "Count of Executive Directors / Total Count of Directors",
            {"Count of Executive Directors": 5, "Total Count of Directors": 9},
        )
        assert result == pytest.approx(5 / 9)

    def test_growth_rate_with_parentheses(self):
        expr = "(Current Year Employees - Previous Year Employees) / Previous Year Employees"
        result = calculate_from_expression(
            expr,
            {"Current Year Employees": 1174, "Previous Year Employees": 800},
        )
        assert result == pytest.approx((1174 - 800) / 800)

    def test_all_arithmetic_operators(self):
        assert calculate_from_expression("A + B", {"A": 2, "B": 3}) == 5
        assert calculate_from_expression("A - B", {"A": 10, "B": 4}) == 6
        assert calculate_from_expression("A * B", {"A": 6, "B": 7}) == 42
        assert calculate_from_expression("A / B", {"A": 8, "B": 2}) == 4
        assert calculate_from_expression("A ** B", {"A": 2, "B": 10}) == 1024

    def test_unary_negation(self):
        assert calculate_from_expression("-A + B", {"A": 5, "B": 8}) == 3

    def test_longer_variable_names_take_precedence(self):
        # "AB" must be substituted before "A" to avoid partial replacement.
        result = calculate_from_expression("AB / A", {"A": 2, "AB": 10})
        assert result == 5

    def test_division_by_zero_returns_nan(self):
        result = calculate_from_expression(
            "A / B", {"A": 1, "B": 0}
        )
        assert math.isnan(result)

    def test_unresolved_variable_returns_nan(self):
        # "Unknown" has no value supplied, so a variable-like token remains.
        result = calculate_from_expression("A / Unknown", {"A": 5})
        assert math.isnan(result)

    def test_does_not_mutate_input_values(self):
        values = {"A": 1, "B": 2}
        calculate_from_expression("A + B", values)
        assert values == {"A": 1, "B": 2}

    def test_rejects_function_call_expression(self):
        # No variables to substitute; a bare function call must be rejected.
        result = calculate_from_expression("__import__('os')", {})
        assert math.isnan(result)


class TestSafeEvalNode:
    def _eval(self, expr):
        import ast

        return _safe_eval_node(ast.parse(expr, mode="eval"), {})

    def test_evaluates_plain_arithmetic(self):
        assert self._eval("(2 + 3) * 4") == 20

    def test_rejects_string_constant(self):
        with pytest.raises(ValueError):
            self._eval("'hello'")

    def test_rejects_disallowed_operator(self):
        # Modulo is not in the allow-list of binary operators.
        with pytest.raises(ValueError):
            self._eval("7 % 2")

    def test_rejects_function_call_node(self):
        with pytest.raises(ValueError):
            self._eval("abs(-1)")

    def test_rejects_none_constant(self):
        with pytest.raises(ValueError):
            self._eval("None")

    def test_rejects_unsupported_unary_operator(self):
        # ``not`` maps to ast.Not, which is not in the unary allow-list.
        with pytest.raises(ValueError):
            self._eval("not 1")

    def test_rejects_unsupported_node_type(self):
        # A comparison node (1 < 2) is not an allowed node type.
        with pytest.raises(ValueError):
            self._eval("1 < 2")


class TestCalculateSyntaxErrorHandling:
    def test_invalid_syntax_after_substitution_returns_nan(self):
        # After substitution the expression "1 1" is a syntax error.
        result = calculate_from_expression("A A", {"A": 1})
        assert math.isnan(result)
