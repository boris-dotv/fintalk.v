#!/usr/bin/env python3
"""Unit tests for enhanced_core/parallel_executor.py error and timeout paths.

Pure stdlib: no network or heavy deps required.
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.parallel_executor import ParallelExecutor, TaskResult  # noqa: E402


class TestConstructorValidation(unittest.TestCase):
    def test_non_positive_max_workers_raises(self):
        with self.assertRaises(ValueError):
            ParallelExecutor(max_workers=0)
        with self.assertRaises(ValueError):
            ParallelExecutor(max_workers=-1)


class TestExecuteParallelValidation(unittest.TestCase):
    def setUp(self):
        self.executor = ParallelExecutor(max_workers=2)

    def test_empty_tasks_returns_empty_dict(self):
        self.assertEqual(self.executor.execute_parallel({}), {})

    def test_non_positive_timeout_raises(self):
        with self.assertRaises(ValueError):
            self.executor.execute_parallel({"a": lambda: 1}, timeout=0)

    def test_non_callable_task_raises(self):
        with self.assertRaises(ValueError):
            self.executor.execute_parallel({"a": 123})


class TestExecuteParallelResults(unittest.TestCase):
    def setUp(self):
        self.executor = ParallelExecutor(max_workers=4)

    def test_successful_task_returns_result(self):
        results = self.executor.execute_parallel({"ok": lambda: 42})
        self.assertIn("ok", results)
        self.assertIsInstance(results["ok"], TaskResult)
        self.assertEqual(results["ok"].result, 42)
        self.assertIsNone(results["ok"].error)

    def test_raising_task_captures_error(self):
        def boom():
            raise RuntimeError("kaboom")

        results = self.executor.execute_parallel({"bad": boom})
        self.assertIn("bad", results)
        self.assertIsNone(results["bad"].result)
        self.assertIn("kaboom", results["bad"].error)

    def test_timeout_still_returns_all_task_keys(self):
        def slow():
            time.sleep(2)
            return "done"

        results = self.executor.execute_parallel({"slow": slow}, timeout=0.2)
        self.assertIn("slow", results)
        self.assertIsInstance(results["slow"], TaskResult)
        self.assertIsNotNone(results["slow"].error)


class TestExecuteParallelWithCallbacks(unittest.TestCase):
    def setUp(self):
        self.executor = ParallelExecutor(max_workers=4)

    def test_empty_tasks_returns_empty_dict(self):
        self.assertEqual(self.executor.execute_parallel_with_callbacks({}), {})

    def test_non_positive_timeout_raises(self):
        with self.assertRaises(ValueError):
            self.executor.execute_parallel_with_callbacks({"a": lambda: 1}, timeout=0)

    def test_on_complete_callback_invoked(self):
        seen = []
        results = self.executor.execute_parallel_with_callbacks(
            {"ok": lambda: 7}, on_complete=seen.append
        )
        self.assertEqual(results["ok"].result, 7)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].result, 7)

    def test_on_error_callback_invoked(self):
        seen = []

        def boom():
            raise ValueError("nope")

        results = self.executor.execute_parallel_with_callbacks(
            {"bad": boom}, on_error=seen.append
        )
        self.assertIn("nope", results["bad"].error)
        self.assertEqual(len(seen), 1)
        self.assertIn("nope", seen[0].error)

    def test_timeout_still_returns_all_task_keys(self):
        def slow():
            time.sleep(2)
            return "done"

        results = self.executor.execute_parallel_with_callbacks(
            {"slow": slow}, timeout=0.2
        )
        self.assertIn("slow", results)
        self.assertIsNotNone(results["slow"].error)


if __name__ == "__main__":
    unittest.main()
