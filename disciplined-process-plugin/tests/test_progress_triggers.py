# @trace SPEC-08
"""Tests for progress report trigger evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tools.progress_report.extractor import ProjectState, TaskState
from tools.progress_report.triggers import (
    TriggerResult,
    evaluate_triggers,
    should_deduplicate,
)
from tools.shared.config import TriggerConfig


def _task(
    id: str = "bd-1",
    title: str = "Task",
    status: str = "open",
    is_hole: bool = False,
    hole_type: str = "",
    blocked_by: list[str] | None = None,
) -> TaskState:
    return TaskState(
        id=id,
        title=title,
        status=status,
        is_hole=is_hole,
        hole_type=hole_type,
        blocked_by=blocked_by or [],
    )


class TestEvaluateTriggers:
    def test_first_report_always_triggers(self):
        config = TriggerConfig()
        state = ProjectState(tasks=[_task()])
        result = evaluate_triggers(config, prev_state=None, curr_state=state)
        assert result.should_report
        assert "initial" in result.fired

    def test_manual_trigger(self):
        config = TriggerConfig()
        state = ProjectState()
        result = evaluate_triggers(
            config,
            prev_state=ProjectState(),
            curr_state=state,
            manual_trigger="Phase 1 complete",
        )
        assert result.should_report
        assert "on_demand" in result.fired
        assert "Phase 1 complete" in result.reason

    def test_manual_trigger_disabled(self):
        config = TriggerConfig(on_demand=False)
        result = evaluate_triggers(
            config,
            prev_state=ProjectState(),
            curr_state=ProjectState(),
            manual_trigger="Test",
        )
        assert not result.should_report

    def test_tasks_completed_trigger(self):
        config = TriggerConfig(tasks_completed=2)
        prev = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="open"),
                _task(id="3", status="open"),
            ]
        )
        curr = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="closed"),
                _task(id="3", status="closed"),
            ]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "tasks_completed" in result.fired

    def test_tasks_completed_not_enough(self):
        config = TriggerConfig(tasks_completed=3)
        prev = ProjectState(
            tasks=[_task(id="1", status="open"), _task(id="2", status="open")]
        )
        curr = ProjectState(
            tasks=[_task(id="1", status="closed"), _task(id="2", status="open")]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "tasks_completed" not in result.fired

    def test_interval_trigger(self):
        config = TriggerConfig(interval="30m")
        prev = ProjectState()
        curr = ProjectState()
        old_time = datetime.now(timezone.utc) - timedelta(minutes=35)
        result = evaluate_triggers(
            config,
            prev_state=prev,
            curr_state=curr,
            last_report_time=old_time,
        )
        assert "interval" in result.fired

    def test_interval_not_elapsed(self):
        config = TriggerConfig(interval="30m")
        prev = ProjectState()
        curr = ProjectState()
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        result = evaluate_triggers(
            config,
            prev_state=prev,
            curr_state=curr,
            last_report_time=recent_time,
        )
        assert "interval" not in result.fired

    def test_epic_milestone_25(self):
        config = TriggerConfig()
        prev = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="open"),
                _task(id="3", status="open"),
                _task(id="4", status="open"),
            ]
        )  # 25% complete
        curr = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="closed"),
                _task(id="3", status="open"),
                _task(id="4", status="open"),
            ]
        )  # 50% complete
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "epic_milestone" in result.fired
        assert "50%" in result.reason

    def test_on_failure_detected(self):
        config = TriggerConfig()
        prev = ProjectState(tasks=[_task(id="1", status="in_progress")])
        curr = ProjectState(tasks=[_task(id="1", status="open")])
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "on_failure" in result.fired

    def test_on_blocker_triggered(self):
        config = TriggerConfig()
        prev = ProjectState(tasks=[_task(id="1", status="open")])
        curr = ProjectState(
            tasks=[_task(id="1", status="open", blocked_by=["H1"])]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "on_blocker" in result.fired

    def test_hole_created(self):
        config = TriggerConfig()
        prev = ProjectState(tasks=[_task(id="1")])
        curr = ProjectState(
            tasks=[
                _task(id="1"),
                _task(id="H1", is_hole=True, hole_type="clarification"),
            ]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "hole_created" in result.fired

    def test_hole_resolved(self):
        config = TriggerConfig()
        prev = ProjectState(
            tasks=[_task(id="H1", status="open", is_hole=True)]
        )
        curr = ProjectState(
            tasks=[_task(id="H1", status="closed", is_hole=True)]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "hole_resolved" in result.fired

    def test_all_work_hole_blocked(self):
        config = TriggerConfig()
        prev = ProjectState(tasks=[_task(id="1", status="open")])
        curr = ProjectState(
            tasks=[
                _task(id="1", status="open", blocked_by=["H1"]),
                _task(id="H1", status="open", is_hole=True),
            ]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "all_work_hole_blocked" in result.fired

    def test_on_rework_trigger(self):
        """Gap 2: on_rework trigger fires when rework tasks appear."""
        config = TriggerConfig(on_rework=True)
        prev = ProjectState(
            tasks=[_task(id="1", status="closed")]
        )
        curr = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="open", title="Rework: fix auth flow"),
            ]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "on_rework" in result.fired

    def test_on_rework_no_rework_tasks(self):
        """on_rework should not fire when new tasks are normal."""
        config = TriggerConfig(on_rework=True)
        prev = ProjectState(
            tasks=[_task(id="1", status="closed")]
        )
        curr = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="open", title="Add logging"),
            ]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert "on_rework" not in result.fired

    def test_no_triggers_fire(self):
        config = TriggerConfig(
            tasks_completed=0,
            issue_completed=False,
            epic_milestone=False,
            on_failure=False,
            on_rework=False,
            on_blocker=False,
            hole_created=False,
            hole_resolved=False,
            all_work_hole_blocked=False,
        )
        prev = ProjectState(tasks=[_task(id="1")])
        curr = ProjectState(tasks=[_task(id="1")])
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        assert not result.should_report

    def test_multiple_triggers_fire(self):
        config = TriggerConfig(tasks_completed=1)
        prev = ProjectState(
            tasks=[
                _task(id="1", status="open"),
                _task(id="2", status="open"),
                _task(id="3", status="open"),
                _task(id="4", status="open"),
            ]
        )
        curr = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="closed"),
                _task(id="3", status="open"),
                _task(id="4", status="open"),
            ]
        )
        result = evaluate_triggers(config, prev_state=prev, curr_state=curr)
        # Both tasks_completed and epic_milestone (50%) should fire
        assert "tasks_completed" in result.fired
        assert "epic_milestone" in result.fired


class TestDeduplication:
    def test_no_previous_report(self):
        assert should_deduplicate(None) is False

    def test_recent_report_deduplicates(self):
        recent = datetime.now(timezone.utc) - timedelta(minutes=2)
        assert should_deduplicate(recent) is True

    def test_old_report_allows(self):
        old = datetime.now(timezone.utc) - timedelta(minutes=10)
        assert should_deduplicate(old) is False

    def test_custom_window(self):
        recent = datetime.now(timezone.utc) - timedelta(seconds=30)
        assert should_deduplicate(recent, dedup_window_seconds=60) is True
        assert should_deduplicate(recent, dedup_window_seconds=10) is False
