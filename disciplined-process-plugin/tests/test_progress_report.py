# @trace SPEC-08
"""Tests for progress report generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import json
import pytest

from tools.progress_report.extractor import (
    GitState,
    ProjectState,
    TaskState,
)
from tools.progress_report.report import (
    generate_report_json,
    generate_report_markdown,
    write_report,
)


def _task(
    id: str = "bd-1",
    title: str = "Task",
    status: str = "open",
    priority: int = 2,
    is_hole: bool = False,
    hole_type: str = "",
    blocked_by: list[str] | None = None,
    labels: list[str] | None = None,
) -> TaskState:
    return TaskState(
        id=id,
        title=title,
        status=status,
        priority=priority,
        is_hole=is_hole,
        hole_type=hole_type,
        blocked_by=blocked_by or [],
        labels=labels or [],
    )


class TestGenerateReportMarkdown:
    def test_basic_report(self):
        state = ProjectState(
            tasks=[
                _task(id="1", title="Task A", status="closed"),
                _task(id="2", title="Task B", status="open"),
                _task(id="3", title="Task C", status="open"),
            ]
        )
        md = generate_report_markdown(state, epic_title="Test Project")
        assert "# Progress Report: Test Project" in md
        assert "1 of 3 tasks done (33%)" in md
        assert "Ready Work" in md
        assert "For Agents" in md

    def test_with_holes(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="open"),
                _task(
                    id="H1",
                    title="Rate limit",
                    status="open",
                    is_hole=True,
                    hole_type="research",
                ),
                _task(
                    id="H2",
                    title="Session Q",
                    status="closed",
                    is_hole=True,
                    hole_type="clarification",
                ),
            ]
        )
        md = generate_report_markdown(state)
        assert "## Holes" in md
        assert "Open (blocking work)" in md
        assert "Rate limit" in md
        assert "Resolved" in md
        assert "Hole Metrics" in md

    def test_with_prev_state(self):
        prev = ProjectState(
            tasks=[
                _task(id="1", title="Task A", status="open"),
                _task(id="2", title="Task B", status="open"),
            ]
        )
        curr = ProjectState(
            tasks=[
                _task(id="1", title="Task A", status="closed"),
                _task(id="2", title="Task B", status="open"),
                _task(id="3", title="New Task", status="open"),
            ]
        )
        md = generate_report_markdown(
            curr,
            prev_state=prev,
            last_report_time=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        assert "Since Last Report" in md
        assert "Completed" in md
        assert "Task A" in md
        assert "New Issues Discovered" in md
        assert "New Task" in md

    def test_progress_bar(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="closed"),
                _task(id="3", status="open"),
                _task(id="4", status="open"),
            ]
        )
        md = generate_report_markdown(state)
        assert "50%" in md

    def test_blocked_tasks(self):
        state = ProjectState(
            tasks=[
                _task(id="1", title="Blocked Task", status="open", blocked_by=["2"]),
                _task(id="2", title="Blocker", status="open"),
            ]
        )
        md = generate_report_markdown(state)
        assert "Blocked" in md
        assert "Blocked Task" in md

    def test_files_changed(self):
        state = ProjectState(
            tasks=[_task()],
            git=GitState(files_changed=["src/auth.py", "tests/test_auth.py"]),
        )
        md = generate_report_markdown(state)
        assert "Files Changed" in md
        assert "src/auth.py" in md

    def test_action_items_for_humans(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="open"),
                _task(
                    id="H1",
                    title="Need human decision",
                    status="open",
                    is_hole=True,
                    hole_type="clarification",
                    priority=1,
                ),
            ]
        )
        md = generate_report_markdown(state)
        assert "For Humans: Action Items" in md
        assert "human decision" in md.lower()

    def test_all_work_hole_blocked_action(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="open", blocked_by=["H1"]),
                _task(id="H1", status="open", is_hole=True, hole_type="clarification"),
            ]
        )
        md = generate_report_markdown(state)
        assert "urgent" in md.lower()

    def test_key_decisions_section(self):
        """Gap 7: Key decisions labeled tasks appear in report."""
        state = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="closed", title="Use JWT tokens",
                      labels=["decision"]),
            ]
        )
        md = generate_report_markdown(state)
        assert "Key Decisions Made" in md
        assert "Use JWT tokens" in md

    def test_risks_section_blocked_high_priority(self):
        """Gap 7: High-priority blocked tasks appear as risks."""
        state = ProjectState(
            tasks=[
                _task(id="1", status="open", priority=1, blocked_by=["H1"]),
                _task(id="H1", status="open", is_hole=True),
            ]
        )
        md = generate_report_markdown(state)
        assert "Risks" in md

    def test_completed_table_has_duration_column(self):
        """Gap 6: Completed table should have Duration column."""
        prev = ProjectState(tasks=[_task(id="1", status="open")])
        state = ProjectState(tasks=[_task(id="1", status="closed")])
        md = generate_report_markdown(state, prev_state=prev)
        assert "Duration" in md

    def test_empty_state(self):
        state = ProjectState()
        md = generate_report_markdown(state)
        assert "# Progress Report" in md
        assert "0 of 0 tasks done" in md


class TestGenerateReportJson:
    def test_basic_json(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="open"),
                _task(id="3", status="in_progress"),
            ]
        )
        report = generate_report_json(state, trigger_reason="on_demand")
        assert report["trigger"] == "on_demand"
        assert report["tasks"]["total"] == 3
        assert report["tasks"]["completed"] == 1
        assert report["tasks"]["in_progress"] == 1
        assert report["tasks"]["not_started"] == 1
        assert report["epic_progress"] == pytest.approx(0.33, abs=0.01)
        # New fields per Gap 14
        assert report["report_number"] == 1
        assert report["epic_title"] == "Project"
        assert "ready_work" in report
        assert "risks" in report

    def test_with_holes(self):
        state = ProjectState(
            tasks=[
                _task(id="1", status="open"),
                _task(id="H1", status="open", is_hole=True, hole_type="research"),
            ]
        )
        report = generate_report_json(state)
        assert report["holes"]["total"] == 1
        assert report["holes"]["open_blocking"] == 1
        assert "tasks_blocked_by_holes" in report["holes"]
        assert len(report["open_holes"]) == 1
        assert report["open_holes"][0]["type"] == "research"

    def test_with_prev_state(self):
        prev = ProjectState(
            tasks=[
                _task(id="1", status="open"),
                _task(id="2", status="open"),
            ]
        )
        curr = ProjectState(
            tasks=[
                _task(id="1", status="closed"),
                _task(id="2", status="open"),
                _task(id="3", status="open"),
            ]
        )
        report = generate_report_json(curr, prev_state=prev)
        assert "1" in report["recently_completed"]
        assert "3" in report["discovered_issues"]

    def test_ready_task_ids(self):
        state = ProjectState(
            tasks=[
                _task(id="bd-abc", status="open"),
                _task(id="bd-def", status="open", blocked_by=["bd-abc"]),
            ]
        )
        report = generate_report_json(state)
        assert report["ready_task_ids"] == ["bd-abc"]

    def test_json_serializable(self):
        state = ProjectState(tasks=[_task()])
        report = generate_report_json(state)
        # Should not raise
        json.dumps(report)


class TestWriteReport:
    def test_writes_files(self, tmp_path: Path):
        state = ProjectState(
            tasks=[
                _task(id="1", title="Task A", status="closed"),
                _task(id="2", title="Task B", status="open"),
            ]
        )
        md_path, json_path = write_report(
            state,
            trigger_reason="test",
            output_dir=tmp_path,
        )
        assert md_path.exists()
        assert json_path.exists()
        assert json_path.name == "latest.json"

        # Check markdown content
        md_content = md_path.read_text()
        assert "Progress Report" in md_content

        # Check JSON content
        json_data = json.loads(json_path.read_text())
        assert json_data["tasks"]["total"] == 2

    def test_latest_symlink(self, tmp_path: Path):
        state = ProjectState(tasks=[_task()])
        write_report(state, output_dir=tmp_path)
        latest = tmp_path / "latest.md"
        assert latest.exists()

    def test_multiple_reports(self, tmp_path: Path):
        state = ProjectState(tasks=[_task()])
        md1, _ = write_report(
            state,
            trigger_reason="first",
            report_number=1,
            output_dir=tmp_path,
        )
        md2, _ = write_report(
            state,
            trigger_reason="second",
            report_number=2,
            output_dir=tmp_path,
        )
        # Both files exist
        assert md1.exists()
        assert md2.exists()
        assert md1 != md2

    def test_creates_output_dir(self, tmp_path: Path):
        output_dir = tmp_path / "nested" / "dir"
        state = ProjectState(tasks=[_task()])
        md_path, _ = write_report(state, output_dir=output_dir)
        assert md_path.exists()
        assert output_dir.exists()
