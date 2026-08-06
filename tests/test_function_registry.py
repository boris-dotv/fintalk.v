"""Unit tests for enhanced_core.function_registry.FinancialFunctionRegistry.

Uses an in-memory SQLite database so the registry's SQL-backed helpers can
be exercised end-to-end without any external services.
"""

import sqlite3

import pytest

from enhanced_core.function_registry import (
    FINANCIAL_FUNCTIONS,
    FinancialFunctionRegistry,
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE companies (company_sort_id INTEGER, name TEXT, employee_size TEXT)"
    )
    cur.execute(
        "CREATE TABLE management (company_sort_id INTEGER, director_type TEXT)"
    )
    cur.execute(
        "CREATE TABLE shareholders "
        "(company_sort_id INTEGER, shareholder_name TEXT, share_percentage TEXT)"
    )
    cur.executemany(
        "INSERT INTO companies VALUES (?, ?, ?)",
        [(1, "ZA Bank", "501-1000"), (2, "WeLab Bank", "201-500")],
    )
    cur.executemany(
        "INSERT INTO management VALUES (?, ?)",
        [
            (1, "Executive Director"),
            (1, "Executive Director"),
            (1, "Non-Executive Director"),
            (1, "Independent Director"),
            (2, "Executive Director"),
            (2, "Non-Executive Director"),
        ],
    )
    cur.executemany(
        "INSERT INTO shareholders VALUES (?, ?, ?)",
        [
            (1, "Alpha", "40%"),
            (1, "Beta", "30%"),
            (1, "Gamma", "20%"),
            (1, "Delta", "10%"),
            (2, "Zeta", "55%"),
            (2, "Eta", "25%"),
        ],
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def registry(db):
    return FinancialFunctionRegistry(db_connection=db)


class TestFunctionDefinitions:
    def test_get_functions_returns_definitions(self, registry):
        funcs = registry.get_functions()
        assert funcs is FINANCIAL_FUNCTIONS
        names = {f["function"]["name"] for f in funcs}
        assert names == {
            "get_company_info",
            "get_executive_director_ratio",
            "get_top_shareholders",
            "calculate_shareholder_concentration",
            "compare_companies",
        }


class TestExecuteDispatch:
    def test_unknown_function_returns_error(self, registry):
        result = registry.execute("does_not_exist", {})
        assert result == {"error": "Unknown function: does_not_exist"}

    def test_missing_required_param_returns_error(self, registry):
        # KeyError on parameters["company_name"] is caught and returned.
        result = registry.execute("get_company_info", {})
        assert "error" in result


class TestGetCompanyInfo:
    def test_returns_company_info(self, registry):
        result = registry.execute("get_company_info", {"company_name": "ZA Bank"})
        assert result["status"] == "success"
        assert result["company"] == "ZA Bank"
        assert result["info"]["name"] == "ZA Bank"

    def test_fuzzy_match_is_case_insensitive(self, registry):
        result = registry.execute("get_company_info", {"company_name": "za"})
        assert result["status"] == "success"
        assert result["info"]["name"] == "ZA Bank"

    def test_unknown_company_returns_error(self, registry):
        result = registry.execute(
            "get_company_info", {"company_name": "Nonexistent Bank"}
        )
        assert "error" in result


class TestExecutiveDirectorRatio:
    def test_computes_ratio(self, registry):
        result = registry.execute(
            "get_executive_director_ratio", {"company_name": "ZA Bank"}
        )
        assert result["status"] == "success"
        # The query counts director_type LIKE '%Executive%', which also matches
        # "Non-Executive Director" -> 2 Executive + 1 Non-Executive = 3.
        assert result["executive_directors"] == 3
        assert result["total_directors"] == 4
        assert result["ratio"] == pytest.approx(0.75)
        assert result["ratio_percentage"] == "75.00%"

    def test_unknown_company_returns_error(self, registry):
        result = registry.execute(
            "get_executive_director_ratio", {"company_name": "Ghost"}
        )
        assert "error" in result


class TestTopShareholders:
    def test_default_top_3(self, registry):
        result = registry.execute(
            "get_top_shareholders", {"company_name": "ZA Bank"}
        )
        assert result["status"] == "success"
        assert result["count"] == 3
        names = [s["shareholder_name"] for s in result["top_n_shareholders"]]
        assert names == ["Alpha", "Beta", "Gamma"]

    def test_custom_top_n(self, registry):
        result = registry.execute(
            "get_top_shareholders", {"company_name": "ZA Bank", "top_n": 2}
        )
        assert result["count"] == 2


class TestShareholderConcentration:
    def test_default_concentration(self, registry):
        result = registry.execute(
            "calculate_shareholder_concentration", {"company_name": "ZA Bank"}
        )
        assert result["status"] == "success"
        # 40 + 30 + 20 = 90
        assert result["concentration"] == pytest.approx(90.0)
        assert result["concentration_percentage"] == "90.00%"

    def test_error_propagates_for_unknown_company(self, registry):
        result = registry.execute(
            "calculate_shareholder_concentration", {"company_name": "Ghost"}
        )
        assert "error" in result


class TestCompareCompanies:
    def test_compares_concentration(self, registry):
        result = registry.execute(
            "compare_companies",
            {"company1": "ZA Bank", "company2": "WeLab Bank", "metric": "concentration"},
        )
        assert result["status"] == "success"
        # ZA Bank top-3 = 90, WeLab top-3 = 80 -> ZA Bank higher.
        assert result["higher"] == "ZA Bank"
        assert result["ZA Bank_concentration"] == pytest.approx(90.0)
        assert result["WeLab Bank_concentration"] == pytest.approx(80.0)

    def test_error_when_a_company_missing(self, registry):
        result = registry.execute(
            "compare_companies",
            {"company1": "ZA Bank", "company2": "Ghost", "metric": "concentration"},
        )
        assert result == {"error": "Failed to get comparison data"}


class TestNoBackendConfigured:
    def test_get_company_id_returns_none_without_db(self):
        reg = FinancialFunctionRegistry()
        result = reg.execute("get_company_info", {"company_name": "ZA Bank"})
        assert "error" in result
