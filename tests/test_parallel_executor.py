#!/usr/bin/env python3
"""Unit tests for enhanced_core.parallel_executor.ParallelExecutor.

These tests only exercise pure/stdlib behaviour: no network, no API keys.
"""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_core.parallel_executor import ParallelExecutor, TaskResult


class TestParallelExecutorValidation(unittest.TestCase):
    def test_non_positive_max_workers_raises(self):
        with self.assertRaises(ValueError):
            ParallelExecutor(max_workers=0)
        with self.assertRaises(ValueError):
            ParallelExecutor(max_workers=-1)

    def test_empty_tasks_returns_empty_dict(self):
        executor = ParallelExecutor(max_workers=2)
        self.assertEqual(executor.execute_parallel({}), {})
        self.assertEqual(executor.execute_parallel_with_callbacks({}), {})

    def test_non_positive_timeout_raises(self):
        executor = ParallelExecutor(max_workers=2)
        with self.assertRaises(ValueError):
            executor.execute_parallel({"a": lambda: 1}, timeout=0)
        with self.assertRaises(ValueError):
            executor.execute_parallel({"a": lambda: 1}, timeout=-1.0)

    def test_non_callable_task_value_raises(self):
        executor = ParallelExecutor(max_workers=2)
        with self.assertRaises(ValueError):
            executor.execute_parallel({"a": 42})


class TestExecuteParallel(unittest.TestCase):
    def test_successful_tasks_return_results(self):
        executor = ParallelExecutor(max_workers=4)
        tasks = {
            "one": lambda: 1,
            "two": lambda: "two",
            "three": lambda: [3],
        }
        results = executor.execute_parallel(tasks, timeout=10.0)
        self.assertEqual(set(results.keys()), {"one", "two", "three"})
        for name, expected in (("one", 1), ("two", "two"), ("three", [3])):
            self.assertIsInstance(results[name], TaskResult)
            self.assertEqual(results[name].task_name, name)
            self.assertIsNone(results[name].error)
            self.assertEqual(results[name].result, expected)
            self.assertGreaterEqual(results[name].execution_time, 0.0)

    def test_exception_is_captured_in_task_result(self):
        def boom():
            raise RuntimeError("kaboom")

        executor = ParallelExecutor(max_workers=2)
        results = executor.execute_parallel({"bad": boom}, timeout=10.0)
        self.assertIn("bad", results)
        self.assertEqual(results["bad"].error, "kaboom")
        self.assertIsNone(results["bad"].result)

    def test_timeout_still_yields_result_for_every_task(self):
        def slow():
            time.sleep(2.0)
            return "late"

        executor = ParallelExecutor(max_workers=2)
        results = executor.execute_parallel({"slow": slow}, timeout=0.2)
        self.assertIn("slow", results)
        self.assertIsInstance(results["slow"], TaskResult)
        self.assertIsNotNone(results["slow"].error)

    def test_mixed_success_and_failure(self):
        def boom():
            raise ValueError("nope")

        executor = ParallelExecutor(max_workers=4)
        results = executor.execute_parallel(
            {"ok": lambda: "fine", "bad": boom}, timeout=10.0
        )
        self.assertEqual(results["ok"].result, "fine")
        self.assertIsNone(results["ok"].error)
        self.assertEqual(results["bad"].error, "nope")


class TestExecuteParallelWithCallbacks(unittest.TestCase):
    def test_on_complete_called_for_success(self):
        seen = []
        executor = ParallelExecutor(max_workers=2)
        results = executor.execute_parallel_with_callbacks(
            {"a": lambda: 7},
            on_complete=lambda r: seen.append(r),
            timeout=10.0,
        )
        self.assertEqual(results["a"].result, 7)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].task_name, "a")

    def test_on_error_called_for_failure(self):
        seen = []

        def boom():
            raise RuntimeError("bad")

        executor = ParallelExecutor(max_workers=2)
        results = executor.execute_parallel_with_callbacks(
            {"a": boom},
            on_error=lambda r: seen.append(r),
            timeout=10.0,
        )
        self.assertEqual(results["a"].error, "bad")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].task_name, "a")

    def test_non_positive_timeout_raises(self):
        executor = ParallelExecutor(max_workers=2)
        with self.assertRaises(ValueError):
            executor.execute_parallel_with_callbacks({"a": lambda: 1}, timeout=0)


if __name__ == "__main__":
    unittest.main()
