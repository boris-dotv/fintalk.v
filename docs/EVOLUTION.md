# FinTalk.v Evolution Log

This file is maintained automatically by `scripts/daily_improve.py`, which runs
every 2 hours. Each entry records one autonomous improvement (or a reflection on
why none landed) plus the ideas queued for the next run. The AI reads the most
recent entries before deciding what to do, so this file is the project's memory.

Newest entries are at the bottom.

## 2026-09-16 03:27 UTC — Reflection: no code change landed
- **Attempted:** Add unit tests for RejectionDetector parsing logic
- **Blocked by:** rejected by gate: tests/test_rejection_detector.py failed: ---------------------------------------------------------------------- | Ran 11 tests in 0.001s | FAILED (failures=1)
- **Next:** Add tests for enhanced_core/conversation_manager.py pure helpers; Add tests for formula.py ratio calculations with edge cases (zero denominators); Harden rejection_detector: log at debug level for successful parses to reduce noise

## 2026-09-16 03:43 UTC — Add unit tests for ConversationManager pure logic
- **Type:** tests
- **Files:** tests/test_conversation_manager.py
- **Why:** The previous run's attempt at rejection_detector tests was rejected by the gate, and the evolution log explicitly suggests testing conversation_manager pure helpers next. ConversationManager has no heavy imports (only stdlib + logging), so its history/context/slot behaviour can be verified with the standard library unittest without network or API keys. These tests lock in current observable behaviour (turn ordering, maxlen trimming, entity dedup, clear() reset) so future refactors cannot silently break it.
- **Next:** Add tests for formula.py calculate_from_expression edge cases (division by zero, unknown variables, unsupported AST nodes) in tests/test_formula.py; Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Add tests for enhanced_core/correlation_checker.py keyword matching logic; Document ConversationManager context keys in API_REFERENCE.md

## 2026-09-16 08:58 UTC — Add unit tests for formula.py safe expression evaluation
- **Type:** tests
- **Files:** tests/test_formula.py
- **Why:** The evolution log's next ideas explicitly call for tests of formula.calculate_from_expression edge cases (division by zero, unknown variables, unsupported AST nodes). formula.py is pure stdlib + loguru, so it can be tested without network or heavy deps. These tests lock in the current safe-evaluation contract (NaN on unknown variables, NaN on division by zero, rejection of function calls/attribute access) so future refactors cannot silently weaken the sandbox.
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Add tests for enhanced_core/correlation_checker.py keyword matching logic in tests/test_correlation_checker.py; Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/arbitrator.py decision parsing in tests/test_arbitrator.py

## 2026-09-16 14:30 UTC — Reflection: no code change landed
- **Attempted:** Add unit tests for RejectionDetector parsing logic
- **Blocked by:** rejected by gate: tests/test_rejection_detector.py failed: FAIL: test_digit_embedded_in_text_is_parsed (tests.test_rejection_detector.TestRejectionDetectorParsing.test_digit_embedded_in_text_is_parsed) | self.assertFal
- **Next:** Add tests for enhanced_core/correlation_checker.py keyword matching logic in tests/test_correlation_checker.py; Add tests for enhanced_core/arbitrator.py decision parsing in tests/test_arbitrator.py; Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Document ConversationManager context keys in API_REFERENCE.md

## 2026-09-16 19:16 UTC — Add unit tests for CorrelationChecker and QueryArbitrator
- **Type:** tests
- **Files:** tests/test_correlation_checker.py, tests/test_arbitrator.py
- **Why:** The evolution log repeatedly lists tests for enhanced_core/correlation_checker.py and enhanced_core/arbitrator.py as next ideas, and both modules are pure stdlib (logging + dataclasses) with an injected llm_caller, so they can be tested without network or heavy deps. These tests lock in the observable parsing contract (empty input short-circuits, 'yes'/'no' prefix matching, unexpected responses default to False, arbitration letter mapping and fallback to 'A' on bad/None output) so future refactors cannot silently change behaviour.
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Add tests for enhanced_core/rejection_detector.py parsing (note: previous attempts failed on the digit-embedded-in-text case; verify regex \b([01])\b behaviour before asserting); Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/query_rewriter.py prompt construction in tests/test_query_rewriter.py

## 2026-09-16 22:32 UTC — Reflection: no code change landed
- **Attempted:** Add unit tests for rejection_detector parsing logic
- **Blocked by:** rejected by gate: tests/test_rejection_detector.py failed: ERROR: test_empty_llm_response_defaults_to_not_rejected (tests.test_rejection_detector.TestRejectionDetector.test_empty_llm_response_defaults_to_not_rejected) 
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/query_rewriter.py prompt construction in tests/test_query_rewriter.py; Add tests for enhanced_core/function_registry.py registration/lookup logic in tests/test_function_registry.py

## 2026-09-17 02:51 UTC — Add unit tests for QueryRewriter pure logic
- **Type:** tests
- **Files:** tests/test_query_rewriter.py
- **Why:** The evolution log repeatedly lists tests for enhanced_core/query_rewriter.py prompt construction as a next idea, and the module is pure stdlib (logging + typing) with an injected llm_caller, so it can be tested without network or heavy deps. Reading the implementation shows a duplicated _is_bad_rewrite definition (the second silently overrides the first) and clear observable contracts: empty/whitespace queries are returned stripped, missing history short-circuits, bad rewrites (empty or low character overlap) fall back to the original query, and good rewrites are stripped and returned. These t
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Add tests for enhanced_core/function_registry.py registration/lookup logic in tests/test_function_registry.py; Remove the duplicated _is_bad_rewrite definition in enhanced_core/query_rewriter.py (second silently overrides first); Document ConversationManager context keys in API_REFERENCE.md

## 2026-09-17 09:04 UTC — Reflection: no code change landed
- **Attempted:** Remove duplicated _is_bad_rewrite in query_rewriter.py
- **Blocked by:** rejected by gate: edit 0: old == new (no-op)
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Add tests for enhanced_core/function_registry.py registration/lookup logic in tests/test_function_registry.py; Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/streaming_nlg.py pure formatting helpers in tests/test_streaming_nlg.py

## 2026-09-17 14:34 UTC — Reflection: no code change landed
- **Attempted:** Remove unreachable duplicate return in _get_company_info
- **Blocked by:** rejected by gate: tests/test_function_registry.py failed: KeyError: 'company_name' | FAIL: test_executive_director_ratio (tests.test_function_registry.TestExecuteDispatch.test_executive_director_ratio) | self.assertEqu
- **Next:** Add tests for enhanced_core/streaming_nlg.py pure helpers (generate_answer input validation paths) in tests/test_streaming_nlg.py; Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/parallel_executor.py result aggregation in tests/test_parallel_executor.py

## 2026-09-17 19:28 UTC — Fix timeout handling in ParallelExecutor.execute_parallel
- **Type:** bugfix
- **Files:** enhanced_core/parallel_executor.py
- **Why:** as_completed(future_to_task, timeout=timeout) raises concurrent.futures.TimeoutError when the overall timeout elapses, but the code only catches the builtin TimeoutError inside the per-future loop, so a timeout propagates out of execute_parallel and the 'ensure all tasks have results' backfill never runs. The same flaw exists in execute_parallel_with_callbacks. Wrapping the collection loop in try/except concurrent.futures.TimeoutError lets the existing backfill fill in the missing tasks, matching the documented contract that every task gets a TaskResult.
- **Next:** —

## 2026-09-17 22:34 UTC — Add unit tests for ParallelExecutor result aggregation
- **Type:** tests
- **Files:** tests/test_parallel_executor.py
- **Why:** The evolution log repeatedly lists tests for enhanced_core/parallel_executor.py result aggregation as a next idea, and the module is pure stdlib (logging, typing, concurrent.futures, dataclasses) so it can be tested without network or heavy deps. Reading the implementation shows clear observable contracts: empty task dict returns {}, non-callable values and non-positive timeout/max_workers raise ValueError, every submitted task gets a TaskResult even on timeout, exceptions are captured into TaskResult.error, and callbacks fire on success/error. These tests lock in that contract so future refac
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/function_registry.py registration/lookup logic in tests/test_function_registry.py; Add tests for enhanced_core/streaming_nlg.py pure formatting helpers in tests/test_streaming_nlg.py

## 2026-09-18 02:38 UTC — Reflection: no code change landed
- **Attempted:** Add unit tests for RejectionDetector parsing logic
- **Blocked by:** rejected by gate: tests/test_rejection_detector.py failed: FAIL: test_none_response_defaults_to_accept (tests.test_rejection_detector.TestRejectionDetectorParsing.test_none_response_defaults_to_accept) | self.assertTru
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/function_registry.py registration/lookup logic in tests/test_function_registry.py; Add tests for enhanced_core/streaming_nlg.py pure formatting helpers in tests/test_streaming_nlg.py

## 2026-09-18 08:39 UTC — Reflection: no code change landed
- **Attempted:** Add unit tests for RejectionDetector parsing logic
- **Blocked by:** rejected by gate: tests/test_rejection_detector.py failed: FAIL: test_none_response_defaults_to_accept (tests.test_rejection_detector.TestRejectionDetectorParsing.test_none_response_defaults_to_accept) | self.assertTru
- **Next:** Harden enhanced_core/rejection_detector.py: log successful parses at debug level to reduce log noise; Document ConversationManager context keys in API_REFERENCE.md; Add tests for enhanced_core/function_registry.py registration/lookup logic in tests/test_function_registry.py (note: previous attempt failed on KeyError 'company_name' and executive_director_ratio — verify _execute_sql column names before asserting); Add tests for enhanced_core/streaming_nlg.py pure formatting helpers in tests/test_streaming_nlg.py; Remove the unreachable duplicate return block after the first return in enhanced_core/function_registry.py _get_company_info

