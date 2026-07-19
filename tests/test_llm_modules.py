"""Unit tests for the LLM-driven enhanced_core modules.

These modules take an injectable ``llm_caller`` callable, so the tests use
simple stub callers to exercise parsing and fallback logic without any
network access.
"""

from enhanced_core.arbitrator import ArbitrationResult, QueryArbitrator
from enhanced_core.correlation_checker import CorrelationChecker
from enhanced_core.query_rewriter import QueryRewriter
from enhanced_core.rejection_detector import RejectionDetector


def make_caller(response):
    """Return a stub llm_caller that always yields ``response``."""

    def _caller(prompt, temperature=0.0):
        return response

    return _caller


class TestQueryArbitrator:
    def test_classifies_each_letter(self):
        cases = {
            "A": "task",
            "B": "knowledge",
            "C": "small_talk",
            "D": "invalid",
        }
        for letter, expected_type in cases.items():
            arb = QueryArbitrator(make_caller(letter))
            result = arb.arbitrate("some query")
            assert isinstance(result, ArbitrationResult)
            assert result.query_type == expected_type
            assert result.confidence == 0.8
            assert result.reasoning

    def test_strips_and_uppercases_response(self):
        arb = QueryArbitrator(make_caller("  b  "))
        assert arb.arbitrate("q").query_type == "knowledge"

    def test_unexpected_letter_defaults_to_task(self):
        arb = QueryArbitrator(make_caller("Z"))
        assert arb.arbitrate("q").query_type == "task"

    def test_none_response_defaults_to_task(self):
        arb = QueryArbitrator(make_caller(None))
        assert arb.arbitrate("q").query_type == "task"

    def test_non_string_response_defaults_to_task(self):
        arb = QueryArbitrator(make_caller(123))
        assert arb.arbitrate("q").query_type == "task"

    def test_prompt_includes_query_and_history(self):
        captured = {}

        def caller(prompt, temperature=0.0):
            captured["prompt"] = prompt
            return "A"

        arb = QueryArbitrator(caller)
        arb.arbitrate("my query", history="prior chat")
        assert "my query" in captured["prompt"]
        assert "prior chat" in captured["prompt"]

    def test_prompt_defaults_history_placeholder(self):
        captured = {}

        def caller(prompt, temperature=0.0):
            captured["prompt"] = prompt
            return "A"

        QueryArbitrator(caller).arbitrate("q")
        assert "No history" in captured["prompt"]


class TestRejectionDetector:
    def test_accepts_on_one(self):
        assert RejectionDetector(make_caller("1")).should_accept("q") is True

    def test_rejects_on_zero(self):
        assert RejectionDetector(make_caller("0")).should_accept("q") is False

    def test_parses_digit_embedded_in_text(self):
        det = RejectionDetector(make_caller("Decision: 0 (reject)"))
        assert det.should_accept("q") is False

    def test_heuristic_accept_when_no_digit(self):
        det = RejectionDetector(make_caller("Yes, this is within scope"))
        assert det.should_accept("q") is True

    def test_heuristic_reject_when_no_digit(self):
        det = RejectionDetector(make_caller("This is unrelated to finance"))
        assert det.should_accept("q") is False

    def test_defaults_to_accept_when_unparseable(self):
        det = RejectionDetector(make_caller("...???..."))
        assert det.should_accept("q") is True

    def test_empty_response_defaults_to_accept(self):
        det = RejectionDetector(make_caller(""))
        assert det.should_accept("q") is True


class TestCorrelationChecker:
    def test_correlated_yes(self):
        cc = CorrelationChecker(make_caller("Yes"))
        assert cc.is_correlated("q1", "q2") is True

    def test_not_correlated_no(self):
        cc = CorrelationChecker(make_caller("No"))
        assert cc.is_correlated("q1", "q2") is False

    def test_case_insensitive(self):
        cc = CorrelationChecker(make_caller("YES, definitely"))
        assert cc.is_correlated("q1", "q2") is True

    def test_empty_prev_query_returns_false_without_calling_llm(self):
        def caller(prompt, temperature=0.0):
            raise AssertionError("llm should not be called")

        cc = CorrelationChecker(caller)
        assert cc.is_correlated("", "q2") is False

    def test_empty_curr_query_returns_false(self):
        cc = CorrelationChecker(make_caller("Yes"))
        assert cc.is_correlated("q1", "") is False

    def test_empty_llm_result_defaults_false(self):
        cc = CorrelationChecker(make_caller(""))
        assert cc.is_correlated("q1", "q2") is False


class TestQueryRewriter:
    def test_no_history_returns_original_query(self):
        def caller(prompt, temperature=0.0):
            raise AssertionError("llm should not be called")

        qr = QueryRewriter(caller)
        assert qr.rewrite("What about WeLab?", history="") == "What about WeLab?"

    def test_returns_rewritten_query(self):
        rewritten = "What is WeLab Bank's employee size?"
        qr = QueryRewriter(make_caller(rewritten))
        result = qr.rewrite(
            "How about WeLab?",
            history="User: What is ZA Bank's employee size?",
        )
        assert result == rewritten

    def test_bad_rewrite_falls_back_to_original(self):
        # Response shares almost no characters with the original -> rejected.
        qr = QueryRewriter(make_caller("zzz"))
        original = "What is ZA Bank's employee size?"
        assert qr.rewrite(original, history="some history") == original

    def test_empty_rewrite_falls_back_to_original(self):
        qr = QueryRewriter(make_caller(""))
        original = "What is ZA Bank's employee size?"
        assert qr.rewrite(original, history="some history") == original

    def test_is_bad_rewrite_detects_low_overlap(self):
        qr = QueryRewriter(make_caller("x"))
        assert qr._is_bad_rewrite("original query text", "zzzzz") is True

    def test_is_bad_rewrite_accepts_high_overlap(self):
        qr = QueryRewriter(make_caller("x"))
        assert (
            qr._is_bad_rewrite("employee size", "What is the employee size") is False
        )

    def test_is_bad_rewrite_empty_is_bad(self):
        qr = QueryRewriter(make_caller("x"))
        assert qr._is_bad_rewrite("original", "") is True
