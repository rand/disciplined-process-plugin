# @trace SPEC-08
"""Tests for progress report state extraction."""

from __future__ import annotations

import pytest

from tools.progress_report.extractor import (
    GitState,
    ProjectState,
    TaskState,
    extract_state_from_json,
)


def _task(
    id: str = "bd-1",
    title: str = "Task",
    status: str = "open",
    priority: int = 2,
    labels: list[str] | None = None,
    blocked_by: list[str] | None = None,
    is_hole: bool = False,
    hole_type: str = "",
) -> TaskState:
    return TaskState(
        id=id,
        title=title,
        status=status,
        priority=priority,
        labels=labels or [],
        blocked_by=blocked_by or [],
        is_hole=is_hole,
        hole_type=hole_type,
    )


class TestProjectState:
    def test_empty_state(self):
        state = ProjectState()
        assert state.total_tasks == 0
        assert state.completed_tasks == 0
        assert state.progress_ratio == 0.0
        assert state.all_work_hole_blocked is False

    def test_task_counts(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="in_progress"),
                _task(id="3", status="open"),
                _task(id="4", status="open", blocked_by=["1"]),
            ]
        )
        assert state.total_tasks == 4
        assert state.completed_tasks == 1
        assert state.in_progress_tasks == 1
        assert state.open_tasks == 2
        assert len(state.blocked_tasks) == 1
        assert len(state.ready_tasks) == 1
        assert state.progress_ratio == 0.25

    def test_holes_separate_from_tasks(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="H1", status="open", is_hole=True, hole_type="clarification"),
                _task(id="H2", status="closed", is_hole=True, hole_type="validation"),
            ]
        )
        assert state.total_tasks == 1
        assert state.total_holes == 2
        assert len(state.open_holes) == 1
        assert len(state.resolved_holes) == 1

    def test_all_work_hole_blocked(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="open", blocked_by=["H1"]),
                _task(id="2", status="open", blocked_by=["H1"]),
                _task(id="H1", status="open", is_hole=True, hole_type="clarification"),
            ]
        )
        # No ready tasks, no in-progress tasks, but open holes exist
        assert state.ready_tasks == []
        assert state.all_work_hole_blocked is True

    def test_not_all_blocked_if_ready_exists(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="open"),  # Ready
                _task(id="2", status="open", blocked_by=["H1"]),
                _task(id="H1", status="open", is_hole=True),
            ]
        )
        assert state.all_work_hole_blocked is False


class TestExtractStateFromJson:
    def test_basic_extraction(self):
        issues = [
            {
                "id": "bd-abc",
                "title": "Configure OAuth",
                "status": "open",
                "priority": 1,
                "labels": [],
                "blocked_by": [],
            },
            {
                "id": "bd-xyz",
                "title": "HOLE: Rate limit",
                "status": "open",
                "priority": 1,
                "labels": ["hole", "hole:research"],
                "blocked_by": [],
            },
        ]
        state = extract_state_from_json(issues)
        assert state.total_tasks == 1
        assert state.total_holes == 1
        assert state.tasks[1].is_hole is True
        assert state.tasks[1].hole_type == "research"

    def test_with_git_state(self):
        git = GitState(
            current_branch="feat/auth",
            recent_commits=[{"hash": "abc12345", "message": "Add auth"}],
            files_changed=["src/auth.py"],
        )
        state = extract_state_from_json([], git_state=git)
        assert state.git.current_branch == "feat/auth"
        assert len(state.git.files_changed) == 1

    def test_blocked_by(self):
        issues = [
            {
                "id": "bd-1",
                "title": "Task A",
                "status": "open",
                "labels": [],
                "blocked_by": [{"id": "bd-2"}],
            },
            {
                "id": "bd-2",
                "title": "Task B",
                "status": "open",
                "labels": [],
                "blocked_by": [],
            },
        ]
        state = extract_state_from_json(issues)
        assert state.tasks[0].blocked_by == ["bd-2"]
        assert len(state.blocked_tasks) == 1
        assert len(state.ready_tasks) == 1

    def test_empty_list(self):
        state = extract_state_from_json([])
        assert state.total_tasks == 0
        assert state.total_holes == 0
