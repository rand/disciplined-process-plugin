# @trace SPEC-07
"""Tests for orchestration script generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tools.spec_decompose.orchestration import (
    _detect_parallel_conflicts,
    _infer_phases,
    generate_orchestration_script,
    generate_pull_loop_script,
    write_orchestration_output,
)


def _make_data(
    tasks: list[dict[str, Any]] | None = None,
    parallel_groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "tasks": tasks or [],
        "holes": [],
        "parallel_groups": parallel_groups or [],
        "epic": {"title": "Test Epic"},
    }


def _task(
    number: int,
    depends_on_tasks: list[int] | None = None,
    title: str = "",
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title or f"Task {number}",
        "depends_on_tasks": depends_on_tasks or [],
    }


class TestInferPhases:
    def test_no_deps_single_phase(self):
        tasks = [_task(1), _task(2), _task(3)]
        phases = _infer_phases(tasks)
        assert len(phases) == 1
        assert sorted(phases[0]["tasks"]) == [1, 2, 3]

    def test_linear_chain(self):
        tasks = [
            _task(1),
            _task(2, depends_on_tasks=[1]),
            _task(3, depends_on_tasks=[2]),
        ]
        phases = _infer_phases(tasks)
        assert len(phases) == 3
        assert phases[0]["tasks"] == [1]
        assert phases[1]["tasks"] == [2]
        assert phases[2]["tasks"] == [3]

    def test_diamond_deps(self):
        tasks = [
            _task(1),
            _task(2, depends_on_tasks=[1]),
            _task(3, depends_on_tasks=[1]),
            _task(4, depends_on_tasks=[2, 3]),
        ]
        phases = _infer_phases(tasks)
        assert len(phases) == 3
        assert phases[0]["tasks"] == [1]
        assert sorted(phases[1]["tasks"]) == [2, 3]
        assert phases[2]["tasks"] == [4]

    def test_empty_tasks(self):
        assert _infer_phases([]) == []

    def test_mixed_deps(self):
        tasks = [
            _task(1),
            _task(2),
            _task(3, depends_on_tasks=[1]),
            _task(4, depends_on_tasks=[2]),
            _task(5, depends_on_tasks=[3, 4]),
        ]
        phases = _infer_phases(tasks)
        assert len(phases) == 3
        assert sorted(phases[0]["tasks"]) == [1, 2]
        assert sorted(phases[1]["tasks"]) == [3, 4]
        assert phases[2]["tasks"] == [5]


class TestGenerateOrchestrationScript:
    def test_basic_script(self):
        data = _make_data(
            tasks=[_task(1), _task(2), _task(3, depends_on_tasks=[1, 2])],
            parallel_groups=[
                {"name": "foundation", "tasks": [1, 2]},
                {"name": "integration", "tasks": [3]},
            ],
        )
        script = generate_orchestration_script(data)
        assert "#!/usr/bin/env bash" in script
        assert "Phase 1: foundation" in script
        assert "Phase 2: integration" in script
        assert "claude -p" in script
        assert "Verifying Phase" in script

    def test_infers_phases_when_no_groups(self):
        data = _make_data(
            tasks=[
                _task(1),
                _task(2),
                _task(3, depends_on_tasks=[1]),
            ]
        )
        script = generate_orchestration_script(data)
        assert "Phase 1" in script
        assert "Phase 2" in script

    def test_parallel_slots(self):
        data = _make_data(
            tasks=[_task(1)],
            parallel_groups=[{"name": "p1", "tasks": [1]}],
        )
        script = generate_orchestration_script(data, parallel_slots=5)
        assert "PARALLEL_SLOTS=${PARALLEL_SLOTS:-5}" in script

    def test_verification_gates(self):
        data = _make_data(
            tasks=[_task(1)],
            parallel_groups=[{"name": "p1", "tasks": [1]}],
        )
        script = generate_orchestration_script(data)
        assert "Verifying Phase 1" in script
        assert "bd blocked" in script
        assert "Halting" in script

    def test_empty_data(self):
        data = _make_data()
        script = generate_orchestration_script(data)
        assert "#!/usr/bin/env bash" in script
        assert "Orchestration Complete" in script


class TestGeneratePullLoopScript:
    def test_basic_pull_loop(self):
        script = generate_pull_loop_script()
        assert "#!/usr/bin/env bash" in script
        assert "bd ready" in script
        assert "bd update" in script
        assert "claude -p" in script
        assert "while true" in script

    def test_hole_aware(self):
        script = generate_pull_loop_script(hole_aware=True)
        assert "hole:agent-resolvable" in script
        assert "human decisions" in script

    def test_not_hole_aware(self):
        script = generate_pull_loop_script(hole_aware=False)
        assert "hole:agent-resolvable" not in script


class TestWriteOrchestrationOutput:
    def test_writes_orchestrate_sh(self, tmp_path: Path):
        data = _make_data(
            tasks=[_task(1)],
            parallel_groups=[{"name": "p1", "tasks": [1]}],
        )
        paths = write_orchestration_output(data, output_dir=tmp_path)
        assert len(paths) == 1
        assert paths[0].name == "orchestrate.sh"
        assert paths[0].exists()
        content = paths[0].read_text()
        assert "#!/usr/bin/env bash" in content

    def test_with_pull_loop(self, tmp_path: Path):
        data = _make_data(
            tasks=[_task(1)],
            parallel_groups=[{"name": "p1", "tasks": [1]}],
        )
        paths = write_orchestration_output(
            data, output_dir=tmp_path, include_pull_loop=True
        )
        assert len(paths) == 2
        names = {p.name for p in paths}
        assert "orchestrate.sh" in names
        assert "pull-loop.sh" in names

    def test_default_output_dir(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = _make_data(
            tasks=[_task(1)],
            parallel_groups=[{"name": "p1", "tasks": [1]}],
        )
        paths = write_orchestration_output(data)
        assert paths[0] == Path("orchestrate.sh")


class TestDetectParallelConflicts:
    """Tests for Gap 10: produces/consumes conflict detection."""

    def test_no_conflicts(self):
        tasks = [
            {"number": 1, "produces": ["src/a.py"]},
            {"number": 2, "produces": ["src/b.py"]},
        ]
        groups = [{"name": "p1", "tasks": [1, 2]}]
        warnings = _detect_parallel_conflicts(tasks, groups)
        assert warnings == []

    def test_detects_shared_produce(self):
        tasks = [
            {"number": 1, "produces": ["src/shared.py", "src/a.py"]},
            {"number": 2, "produces": ["src/shared.py", "src/b.py"]},
        ]
        groups = [{"name": "p1", "tasks": [1, 2]}]
        warnings = _detect_parallel_conflicts(tasks, groups)
        assert len(warnings) == 1
        assert "T1" in warnings[0]
        assert "T2" in warnings[0]
        assert "src/shared.py" in warnings[0]

    def test_no_conflict_across_groups(self):
        tasks = [
            {"number": 1, "produces": ["src/shared.py"]},
            {"number": 2, "produces": ["src/shared.py"]},
        ]
        groups = [
            {"name": "p1", "tasks": [1]},
            {"name": "p2", "tasks": [2]},
        ]
        warnings = _detect_parallel_conflicts(tasks, groups)
        assert warnings == []

    def test_orchestration_metadata_fallback(self):
        tasks = [
            {"number": 1, "orchestration": {"produces": ["src/x.py"]}},
            {"number": 2, "orchestration": {"produces": ["src/x.py"]}},
        ]
        groups = [{"name": "p1", "tasks": [1, 2]}]
        warnings = _detect_parallel_conflicts(tasks, groups)
        assert len(warnings) == 1
        assert "src/x.py" in warnings[0]

    def test_empty_produces(self):
        tasks = [
            {"number": 1},
            {"number": 2},
        ]
        groups = [{"name": "p1", "tasks": [1, 2]}]
        warnings = _detect_parallel_conflicts(tasks, groups)
        assert warnings == []

    def test_multiple_conflicts_in_group(self):
        tasks = [
            {"number": 1, "produces": ["a.py", "b.py"]},
            {"number": 2, "produces": ["a.py"]},
            {"number": 3, "produces": ["b.py"]},
        ]
        groups = [{"name": "p1", "tasks": [1, 2, 3]}]
        warnings = _detect_parallel_conflicts(tasks, groups)
        assert len(warnings) == 2  # T1/T2 conflict on a.py, T1/T3 conflict on b.py


class TestVerificationGates:
    """Tests for Gap 5: per-task verification gates in orchestration script."""

    def test_per_task_status_check(self):
        data = _make_data(
            tasks=[
                {**_task(1), "acceptance_criteria": ["pytest tests/test_auth.py"]},
            ],
            parallel_groups=[{"name": "p1", "tasks": [1]}],
        )
        script = generate_orchestration_script(data)
        assert "T1_STATUS" in script
        assert 'not closed' in script.lower() or 'not closed' in script

    def test_acceptance_test_command_in_script(self):
        data = _make_data(
            tasks=[
                {**_task(1), "acceptance_criteria": ["pytest tests/test_auth.py"]},
            ],
            parallel_groups=[{"name": "p1", "tasks": [1]}],
        )
        script = generate_orchestration_script(data)
        assert "pytest tests/test_auth.py" in script

    def test_conflict_warnings_in_script(self):
        data = _make_data(
            tasks=[
                {**_task(1), "produces": ["src/shared.py"]},
                {**_task(2), "produces": ["src/shared.py"]},
            ],
            parallel_groups=[{"name": "p1", "tasks": [1, 2]}],
        )
        script = generate_orchestration_script(data)
        assert "WARNING: File conflicts" in script
        assert "src/shared.py" in script
