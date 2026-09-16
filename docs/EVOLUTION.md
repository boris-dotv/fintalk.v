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

