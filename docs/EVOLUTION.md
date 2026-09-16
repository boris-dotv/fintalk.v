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

