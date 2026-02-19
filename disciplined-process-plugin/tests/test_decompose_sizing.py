"""Tests for context-window sizing model.

@trace SPEC-07
"""

from __future__ import annotations

import pytest

from tools.spec_decompose.sizing import (
    WINDOW_PRESETS,
    SizingWarning,
    TaskEstimate,
    TokenBudget,
    compute_budget,
    estimate_task_tokens,
    should_merge,
    should_split,
    validate_decomposition_sizing,
)


class TestComputeBudget:
    """Tests for budget computation. [SIZE-1]"""

    def test_default_200k_window(self) -> None:
        budget = compute_budget()
        assert budget.context_window == 200_000
        assert budget.overhead_ceiling == 30_000  # 15% of 200K
        assert budget.total_ceiling == 160_000  # 80% of 200K
        assert budget.buffer == 40_000  # 20% of 200K

    def test_128k_window(self) -> None:
        budget = compute_budget(context_window=128_000)
        assert budget.context_window == 128_000
        assert budget.overhead_ceiling == 19_200  # 15% of 128K
        assert budget.total_ceiling == 102_400  # 80% of 128K

    def test_64k_window(self) -> None:
        budget = compute_budget(context_window=64_000)
        assert budget.overhead_ceiling == 9_600  # 15% of 64K
        assert budget.total_ceiling == 51_200  # 80% of 64K

    def test_overhead_is_15_percent(self) -> None:
        for window in [50_000, 100_000, 200_000, 500_000]:
            budget = compute_budget(context_window=window)
            assert budget.overhead_ceiling == int(window * 0.15)

    def test_total_is_80_percent(self) -> None:
        for window in [50_000, 100_000, 200_000, 500_000]:
            budget = compute_budget(context_window=window)
            assert budget.total_ceiling == int(window * 0.80)

    def test_working_memory_positive(self) -> None:
        budget = compute_budget()
        assert budget.working_memory > 0

    def test_small_window_working_memory_nonnegative(self) -> None:
        budget = compute_budget(context_window=10_000, system_overhead=50_000)
        assert budget.working_memory >= 0

    def test_custom_system_overhead(self) -> None:
        budget = compute_budget(system_overhead=15_000)
        expected_wm = budget.total_ceiling - 15_000 - budget.overhead_ceiling
        assert budget.working_memory == max(0, expected_wm)


class TestTaskEstimate:
    """Tests for TaskEstimate dataclass."""

    def test_overhead_calculation(self) -> None:
        est = TaskEstimate(
            task_number=1,
            description_tokens=1000,
            context_file_tokens=2000,
            implementation_tokens=10000,
            test_tokens=4000,
            tool_overhead_tokens=3000,
        )
        assert est.overhead == 3000  # desc + context

    def test_total_calculation(self) -> None:
        est = TaskEstimate(
            task_number=1,
            description_tokens=1000,
            context_file_tokens=2000,
            implementation_tokens=10000,
            test_tokens=4000,
            tool_overhead_tokens=3000,
        )
        assert est.total == 20000

    def test_to_dict(self) -> None:
        est = TaskEstimate(
            task_number=1,
            description_tokens=1000,
            context_file_tokens=2000,
            implementation_tokens=10000,
            test_tokens=4000,
            tool_overhead_tokens=3000,
        )
        d = est.to_dict()
        assert d["overhead"] == 3000
        assert d["implementation"] == 10000
        assert d["tests"] == 4000
        assert d["total"] == 20000


class TestEstimateTaskTokens:
    """Tests for task token estimation."""

    def test_simple_task(self) -> None:
        task = {
            "number": 1,
            "description": "Configure OAuth provider",
            "context_files": [],
            "complexity": "simple",
        }
        est = estimate_task_tokens(task)
        assert est.implementation_tokens == 10_000
        assert est.test_tokens == 4_000
        assert est.total > 0

    def test_complex_task(self) -> None:
        task = {
            "number": 1,
            "description": "Implement full OAuth flow with PKCE",
            "context_files": [
                {"path": "src/auth.py", "estimated_tokens": 5000},
                {"path": "src/config.py", "estimated_tokens": 2000},
            ],
            "complexity": "complex",
        }
        est = estimate_task_tokens(task)
        assert est.implementation_tokens == 35_000
        assert est.context_file_tokens == 7_000

    def test_inferred_complexity(self) -> None:
        # High complexity signals
        task = {
            "number": 1,
            "description": "Complex task",
            "context_files": [],
            "complexity_signals": {
                "conditions": 3,
                "error_cases": 4,
                "integrations": 2,
            },
        }
        est = estimate_task_tokens(task)
        assert est.implementation_tokens == 35_000  # complex

    def test_existing_code_path(self, tmp_path) -> None:
        # Create a real file
        src = tmp_path / "src" / "auth.py"
        src.parent.mkdir(parents=True)
        src.write_text("def auth():\n    pass\n" * 100)

        task = {
            "number": 1,
            "description": "Update auth",
            "context_files": [{"path": "src/auth.py", "estimated_tokens": 50000}],
            "complexity": "simple",
        }
        est = estimate_task_tokens(task, existing_code=tmp_path)
        # Should use actual token count, not the 50000 estimate
        assert est.context_file_tokens < 50000


class TestShouldSplit:
    """Tests for split heuristic. [SIZE-3]"""

    def test_under_budget_no_split(self) -> None:
        budget = compute_budget(context_window=200_000)
        est = TaskEstimate(
            task_number=1,
            description_tokens=1000,
            context_file_tokens=2000,
            implementation_tokens=10000,
            test_tokens=4000,
            tool_overhead_tokens=3000,
        )
        assert not should_split(est, budget)

    def test_overhead_exceeds_ceiling(self) -> None:
        budget = compute_budget(context_window=200_000)
        est = TaskEstimate(
            task_number=1,
            description_tokens=20000,
            context_file_tokens=20000,  # 40K overhead > 30K ceiling
            implementation_tokens=10000,
            test_tokens=4000,
            tool_overhead_tokens=3000,
        )
        assert should_split(est, budget)

    def test_total_exceeds_ceiling(self) -> None:
        budget = compute_budget(context_window=200_000)
        est = TaskEstimate(
            task_number=1,
            description_tokens=1000,
            context_file_tokens=2000,
            implementation_tokens=100000,
            test_tokens=50000,
            tool_overhead_tokens=10000,
        )
        assert should_split(est, budget)


class TestShouldMerge:
    """Tests for merge heuristic. [SIZE-4]"""

    def test_tiny_task_should_merge(self) -> None:
        est = TaskEstimate(
            task_number=1,
            description_tokens=500,
            context_file_tokens=500,
            implementation_tokens=2000,
            test_tokens=800,
            tool_overhead_tokens=600,
        )
        assert est.total < 5000
        assert should_merge(est)

    def test_normal_task_should_not_merge(self) -> None:
        est = TaskEstimate(
            task_number=1,
            description_tokens=1000,
            context_file_tokens=2000,
            implementation_tokens=10000,
            test_tokens=4000,
            tool_overhead_tokens=3000,
        )
        assert not should_merge(est)

    def test_exactly_5000_should_not_merge(self) -> None:
        est = TaskEstimate(
            task_number=1,
            description_tokens=1000,
            context_file_tokens=1000,
            implementation_tokens=1500,
            test_tokens=1000,
            tool_overhead_tokens=500,
        )
        assert est.total == 5000
        assert not should_merge(est)


class TestWindowPresets:
    """Tests for window preset values."""

    def test_presets_exist(self) -> None:
        assert "claude-code" in WINDOW_PRESETS
        assert "codex" in WINDOW_PRESETS
        assert "parallel" in WINDOW_PRESETS

    def test_preset_values(self) -> None:
        assert WINDOW_PRESETS["claude-code"] == 200_000
        assert WINDOW_PRESETS["codex"] == 128_000
        assert WINDOW_PRESETS["parallel"] == 64_000


class TestValidateDecompositionSizing:
    """Tests for post-hoc sizing validation (Gap 8)."""

    def test_under_budget_no_warnings(self) -> None:
        tasks = [
            {"number": 1, "title": "Small task",
             "estimated_tokens": {"total": 10000, "overhead": 3000}},
        ]
        warnings = validate_decomposition_sizing(tasks)
        assert warnings == []

    def test_over_total_ceiling_warns(self) -> None:
        tasks = [
            {"number": 1, "title": "Huge task",
             "estimated_tokens": {"total": 200_000, "overhead": 5000}},
        ]
        warnings = validate_decomposition_sizing(tasks, context_window=200_000)
        assert len(warnings) == 1
        assert "total ceiling" in warnings[0].message
        assert warnings[0].task_number == 1

    def test_over_overhead_ceiling_warns(self) -> None:
        tasks = [
            {"number": 2, "title": "Heavy context task",
             "estimated_tokens": {"total": 50_000, "overhead": 35_000}},
        ]
        warnings = validate_decomposition_sizing(tasks, context_window=200_000)
        assert len(warnings) == 1
        assert "overhead ceiling" in warnings[0].message

    def test_multiple_warnings(self) -> None:
        tasks = [
            {"number": 1, "title": "OK",
             "estimated_tokens": {"total": 10_000, "overhead": 3000}},
            {"number": 2, "title": "Too big",
             "estimated_tokens": {"total": 200_000, "overhead": 5000}},
            {"number": 3, "title": "Also too big",
             "estimated_tokens": {"total": 180_000, "overhead": 5000}},
        ]
        warnings = validate_decomposition_sizing(tasks)
        assert len(warnings) == 2

    def test_small_window_stricter(self) -> None:
        tasks = [
            {"number": 1, "title": "Medium task",
             "estimated_tokens": {"total": 60_000, "overhead": 5000}},
        ]
        # Under 200K budget but over 64K budget
        assert validate_decomposition_sizing(tasks, 200_000) == []
        warnings = validate_decomposition_sizing(tasks, 64_000)
        assert len(warnings) == 1


# Property-based tests
try:
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @given(st.integers(min_value=10_000, max_value=1_000_000))
    @settings(max_examples=50)
    def test_budget_never_exceeds_window(context_window: int) -> None:
        """@trace SPEC-07 - Total ceiling never exceeds context window."""
        budget = compute_budget(context_window=context_window)
        assert budget.total_ceiling <= budget.context_window
        assert budget.overhead_ceiling <= budget.context_window
        assert budget.working_memory >= 0

    @given(st.integers(min_value=10_000, max_value=1_000_000))
    @settings(max_examples=50)
    def test_buffer_is_20_percent(context_window: int) -> None:
        """@trace SPEC-07 - Buffer is 20% of context window."""
        budget = compute_budget(context_window=context_window)
        assert budget.buffer == context_window - budget.total_ceiling

except ImportError:
    pass
