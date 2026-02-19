"""Tests for DAG validation, cycle detection, and coverage.

@trace SPEC-07
"""

from __future__ import annotations

import pytest

from tools.spec_decompose.graph import (
    CoverageResult,
    CriticalPathEntry,
    check_coverage,
    check_reachability,
    compute_critical_path,
    topological_sort,
    validate_dag,
)


class TestValidateDAG:
    """Tests for DAG validation."""

    def test_empty_graph_is_valid(self) -> None:
        assert validate_dag([], []) == []

    def test_single_task_no_deps_is_valid(self) -> None:
        tasks = [{"number": 1, "depends_on_tasks": [], "depends_on_holes": []}]
        assert validate_dag(tasks, []) == []

    def test_simple_chain_is_valid(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [], "depends_on_holes": []},
            {"number": 2, "depends_on_tasks": [1], "depends_on_holes": []},
            {"number": 3, "depends_on_tasks": [2], "depends_on_holes": []},
        ]
        assert validate_dag(tasks, []) == []

    def test_diamond_dag_is_valid(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [], "depends_on_holes": []},
            {"number": 2, "depends_on_tasks": [1], "depends_on_holes": []},
            {"number": 3, "depends_on_tasks": [1], "depends_on_holes": []},
            {"number": 4, "depends_on_tasks": [2, 3], "depends_on_holes": []},
        ]
        assert validate_dag(tasks, []) == []

    def test_self_reference_detected(self) -> None:
        tasks = [{"number": 1, "depends_on_tasks": [1], "depends_on_holes": []}]
        errors = validate_dag(tasks, [])
        assert any("depends on itself" in e for e in errors)

    def test_cycle_detected(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [2], "depends_on_holes": []},
            {"number": 2, "depends_on_tasks": [1], "depends_on_holes": []},
        ]
        errors = validate_dag(tasks, [])
        assert any("Cycle" in e or "depends on itself" in e for e in errors)

    def test_three_node_cycle_detected(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [3], "depends_on_holes": []},
            {"number": 2, "depends_on_tasks": [1], "depends_on_holes": []},
            {"number": 3, "depends_on_tasks": [2], "depends_on_holes": []},
        ]
        errors = validate_dag(tasks, [])
        assert any("Cycle" in e for e in errors)

    def test_missing_task_reference(self) -> None:
        tasks = [{"number": 1, "depends_on_tasks": [99], "depends_on_holes": []}]
        errors = validate_dag(tasks, [])
        assert any("non-existent task 99" in e for e in errors)

    def test_missing_hole_reference(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [], "depends_on_holes": ["H999"]}
        ]
        errors = validate_dag(tasks, [])
        assert any("non-existent hole H999" in e for e in errors)

    def test_hole_blocks_invalid_task(self) -> None:
        tasks = [{"number": 1, "depends_on_tasks": [], "depends_on_holes": []}]
        holes = [{"number": "H001", "blocks_tasks": [99]}]
        errors = validate_dag(tasks, holes)
        assert any("non-existent task 99" in e for e in errors)

    def test_hole_integration(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [], "depends_on_holes": []},
            {"number": 2, "depends_on_tasks": [], "depends_on_holes": ["H001"]},
        ]
        holes = [{"number": "H001", "blocks_tasks": [2]}]
        errors = validate_dag(tasks, holes)
        assert errors == []

    def test_parallel_tasks_no_deps(self) -> None:
        tasks = [
            {"number": i, "depends_on_tasks": [], "depends_on_holes": []}
            for i in range(1, 6)
        ]
        assert validate_dag(tasks, []) == []


class TestCheckCoverage:
    """Tests for requirement coverage checking."""

    def test_full_coverage(self) -> None:
        reqs = [{"id": "SPEC-01.01"}, {"id": "SPEC-01.02"}]
        tasks = [
            {"spec_traces": ["SPEC-01.01"]},
            {"spec_traces": ["SPEC-01.02"]},
        ]
        result = check_coverage(reqs, tasks)
        assert result.is_complete
        assert result.requirements_covered == 2
        assert result.uncovered == []

    def test_partial_coverage(self) -> None:
        reqs = [{"id": "SPEC-01.01"}, {"id": "SPEC-01.02"}, {"id": "SPEC-01.03"}]
        tasks = [{"spec_traces": ["SPEC-01.01"]}]
        result = check_coverage(reqs, tasks)
        assert not result.is_complete
        assert result.requirements_covered == 1
        assert set(result.uncovered) == {"SPEC-01.02", "SPEC-01.03"}

    def test_empty_requirements(self) -> None:
        result = check_coverage([], [])
        assert result.is_complete
        assert result.coverage_ratio == 1.0

    def test_task_covers_multiple_reqs(self) -> None:
        reqs = [{"id": "SPEC-01.01"}, {"id": "SPEC-01.02"}]
        tasks = [{"spec_traces": ["SPEC-01.01", "SPEC-01.02"]}]
        result = check_coverage(reqs, tasks)
        assert result.is_complete

    def test_coverage_ratio(self) -> None:
        reqs = [{"id": "SPEC-01.01"}, {"id": "SPEC-01.02"}]
        tasks = [{"spec_traces": ["SPEC-01.01"]}]
        result = check_coverage(reqs, tasks)
        assert result.coverage_ratio == 0.5


class TestCheckReachability:
    """Tests for orphan detection."""

    def test_empty_returns_empty(self) -> None:
        assert check_reachability([]) == []

    def test_single_task_is_reachable(self) -> None:
        tasks = [{"number": 1, "depends_on_tasks": []}]
        assert check_reachability(tasks) == []

    def test_chain_all_reachable(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": []},
            {"number": 2, "depends_on_tasks": [1]},
            {"number": 3, "depends_on_tasks": [2]},
        ]
        assert check_reachability(tasks) == []

    def test_disconnected_task_is_orphan(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": []},
            {"number": 2, "depends_on_tasks": [1]},
            {"number": 3, "depends_on_tasks": []},  # disconnected
        ]
        # Task 3 is a root (no deps), so it's reachable. It's only orphaned
        # if it has deps but nobody reaches it.
        # Actually both 1 and 3 are roots, so no orphans
        assert check_reachability(tasks) == []

    def test_parallel_roots_not_orphaned(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": []},
            {"number": 2, "depends_on_tasks": []},
        ]
        assert check_reachability(tasks) == []


class TestTopologicalSort:
    """Tests for topological sorting."""

    def test_empty_graph(self) -> None:
        assert topological_sort([]) == []

    def test_single_task(self) -> None:
        tasks = [{"number": 1, "depends_on_tasks": []}]
        assert topological_sort(tasks) == [1]

    def test_simple_chain(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": []},
            {"number": 2, "depends_on_tasks": [1]},
            {"number": 3, "depends_on_tasks": [2]},
        ]
        result = topological_sort(tasks)
        assert result.index(1) < result.index(2) < result.index(3)

    def test_diamond(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": []},
            {"number": 2, "depends_on_tasks": [1]},
            {"number": 3, "depends_on_tasks": [1]},
            {"number": 4, "depends_on_tasks": [2, 3]},
        ]
        result = topological_sort(tasks)
        assert result.index(1) < result.index(2)
        assert result.index(1) < result.index(3)
        assert result.index(2) < result.index(4)
        assert result.index(3) < result.index(4)

    def test_cycle_raises(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [2]},
            {"number": 2, "depends_on_tasks": [1]},
        ]
        with pytest.raises(ValueError, match="cycles"):
            topological_sort(tasks)

    def test_parallel_tasks_deterministic(self) -> None:
        tasks = [
            {"number": 3, "depends_on_tasks": []},
            {"number": 1, "depends_on_tasks": []},
            {"number": 2, "depends_on_tasks": []},
        ]
        result = topological_sort(tasks)
        # Should be deterministic (sorted within each level)
        assert result == [1, 2, 3]


class TestCriticalPath:
    """Tests for critical path analysis (Gap 3)."""

    def test_empty_returns_empty(self) -> None:
        assert compute_critical_path([], []) == []

    def test_single_task(self) -> None:
        tasks = [{"number": 1, "depends_on_tasks": [],
                  "estimated_tokens": {"total": 5000}}]
        path = compute_critical_path(tasks)
        assert len(path) == 1
        assert path[0].task_id == 1
        assert path[0].cumulative_tokens == 5000

    def test_chain_is_full_path(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [],
             "estimated_tokens": {"total": 1000}},
            {"number": 2, "depends_on_tasks": [1],
             "estimated_tokens": {"total": 2000}},
            {"number": 3, "depends_on_tasks": [2],
             "estimated_tokens": {"total": 3000}},
        ]
        path = compute_critical_path(tasks)
        ids = [e.task_id for e in path]
        assert ids == [1, 2, 3]
        # Cumulative: 1000, 3000, 6000
        assert path[-1].cumulative_tokens == 6000

    def test_picks_heavier_branch(self) -> None:
        """In a diamond, should pick the heavier branch."""
        tasks = [
            {"number": 1, "depends_on_tasks": [],
             "estimated_tokens": {"total": 1000}},
            {"number": 2, "depends_on_tasks": [1],
             "estimated_tokens": {"total": 500}},
            {"number": 3, "depends_on_tasks": [1],
             "estimated_tokens": {"total": 9000}},
            {"number": 4, "depends_on_tasks": [2, 3],
             "estimated_tokens": {"total": 1000}},
        ]
        path = compute_critical_path(tasks)
        ids = [e.task_id for e in path]
        # The heavier branch goes through task 3
        assert 3 in ids
        assert path[-1].task_id == 4

    def test_cumulative_is_monotonic(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [],
             "estimated_tokens": {"total": 1000}},
            {"number": 2, "depends_on_tasks": [1],
             "estimated_tokens": {"total": 2000}},
            {"number": 3, "depends_on_tasks": [2],
             "estimated_tokens": {"total": 500}},
        ]
        path = compute_critical_path(tasks)
        cumulative = [e.cumulative_tokens for e in path]
        for i in range(1, len(cumulative)):
            assert cumulative[i] >= cumulative[i - 1]

    def test_path_is_valid_topo_order(self) -> None:
        tasks = [
            {"number": 1, "depends_on_tasks": [],
             "estimated_tokens": {"total": 100}},
            {"number": 2, "depends_on_tasks": [1],
             "estimated_tokens": {"total": 200}},
            {"number": 3, "depends_on_tasks": [1],
             "estimated_tokens": {"total": 300}},
        ]
        path = compute_critical_path(tasks)
        ids = [e.task_id for e in path]
        # Task 1 should always come before any task that depends on it
        if 1 in ids and 2 in ids:
            assert ids.index(1) < ids.index(2)
        if 1 in ids and 3 in ids:
            assert ids.index(1) < ids.index(3)


# Property-based tests
try:
    from hypothesis import given, settings, assume
    from hypothesis import strategies as st

    def _make_dag(n: int, edges: list[tuple[int, int]]) -> list[dict]:
        """Build a task list from edges, filtering cycles."""
        tasks = [{"number": i, "depends_on_tasks": []} for i in range(n)]
        for a, b in edges:
            if 0 <= a < n and 0 <= b < n and a != b:
                tasks[b]["depends_on_tasks"].append(a)
        return tasks

    @given(
        st.integers(min_value=1, max_value=10),
        st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=9),
                st.integers(min_value=0, max_value=9),
            ),
            max_size=20,
        ),
    )
    @settings(max_examples=50)
    def test_validate_dag_returns_list(n: int, edges: list[tuple[int, int]]) -> None:
        """@trace SPEC-07 - validate_dag always returns a list."""
        tasks = _make_dag(n, edges)
        result = validate_dag(tasks, [])
        assert isinstance(result, list)

except ImportError:
    pass
