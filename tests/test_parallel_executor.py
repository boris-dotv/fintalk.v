"""Unit tests for enhanced_core.parallel_executor.ParallelExecutor."""

import time

from enhanced_core.parallel_executor import ParallelExecutor, TaskResult


class TestTaskResult:
    def test_defaults(self):
        result = TaskResult(task_name="t")
        assert result.task_name == "t"
        assert result.result is None
        assert result.error is None
        assert result.execution_time == 0.0


class TestExecuteParallel:
    def test_empty_tasks_returns_empty_dict(self):
        assert ParallelExecutor().execute_parallel({}) == {}

    def test_runs_all_tasks_and_collects_results(self):
        executor = ParallelExecutor(max_workers=3)
        tasks = {
            "a": lambda: 1,
            "b": lambda: "two",
            "c": lambda: [3],
        }
        results = executor.execute_parallel(tasks)
        assert set(results) == {"a", "b", "c"}
        assert results["a"].result == 1
        assert results["b"].result == "two"
        assert results["c"].result == [3]
        assert all(r.error is None for r in results.values())

    def test_captures_task_exception_as_error(self):
        def boom():
            raise ValueError("kaboom")

        results = ParallelExecutor().execute_parallel({"bad": boom})
        assert results["bad"].result is None
        assert "kaboom" in results["bad"].error

    def test_mixed_success_and_failure(self):
        def boom():
            raise RuntimeError("nope")

        results = ParallelExecutor().execute_parallel(
            {"ok": lambda: 42, "bad": boom}
        )
        assert results["ok"].result == 42
        assert results["ok"].error is None
        assert results["bad"].result is None
        assert results["bad"].error == "nope"

    def test_records_execution_time(self):
        def slow():
            time.sleep(0.05)
            return "done"

        results = ParallelExecutor().execute_parallel({"slow": slow})
        assert results["slow"].execution_time >= 0.05

    def test_runs_concurrently(self):
        def slow():
            time.sleep(0.2)
            return "x"

        tasks = {f"t{i}": slow for i in range(4)}
        start = time.time()
        ParallelExecutor(max_workers=4).execute_parallel(tasks)
        elapsed = time.time() - start
        # If tasks ran serially this would be ~0.8s; concurrently it's ~0.2s.
        assert elapsed < 0.6


class TestExecuteParallelWithCallbacks:
    def test_empty_tasks_returns_empty_dict(self):
        assert ParallelExecutor().execute_parallel_with_callbacks({}) == {}

    def test_on_complete_called_for_success(self):
        completed = []
        ParallelExecutor().execute_parallel_with_callbacks(
            {"a": lambda: 1},
            on_complete=completed.append,
        )
        assert len(completed) == 1
        assert completed[0].result == 1

    def test_on_error_called_for_failure(self):
        errored = []

        def boom():
            raise ValueError("bad")

        results = ParallelExecutor().execute_parallel_with_callbacks(
            {"bad": boom},
            on_error=errored.append,
        )
        assert len(errored) == 1
        assert errored[0].error == "bad"
        assert results["bad"].error == "bad"


class TestExecuteSingleTask:
    def test_success(self):
        result = ParallelExecutor()._execute_single_task("x", lambda: 99)
        assert result.task_name == "x"
        assert result.result == 99
        assert result.error is None

    def test_failure(self):
        def boom():
            raise KeyError("missing")

        result = ParallelExecutor()._execute_single_task("x", boom)
        assert result.result is None
        assert "missing" in result.error
