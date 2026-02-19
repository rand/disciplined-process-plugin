# @trace SPEC-08
"""Tests for progress report watch daemon."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.progress_report.extractor import ProjectState, TaskState
from tools.progress_report.watch import WatchDaemon
from tools.shared.config import ProgressReportConfig, TriggerConfig


def _task(
    id: str = "1",
    title: str = "Task",
    status: str = "open",
    is_hole: bool = False,
) -> TaskState:
    return TaskState(
        id=id, title=title, status=status, is_hole=is_hole,
    )


class TestWatchDaemon:
    def test_init(self):
        config = ProgressReportConfig()
        daemon = WatchDaemon(config, epic_title="Test")
        assert daemon.epic_title == "Test"
        assert daemon._running is False
        assert daemon._report_number == 0

    def test_stop(self):
        config = ProgressReportConfig()
        daemon = WatchDaemon(config)
        daemon._running = True
        daemon.stop()
        assert daemon._running is False

    @patch("tools.progress_report.watch.extract_state")
    def test_check_and_report_initial(self, mock_extract, tmp_path):
        """First check always generates a report."""
        mock_extract.return_value = ProjectState(
            tasks=[_task(id="1", status="open")]
        )
        config = ProgressReportConfig()
        daemon = WatchDaemon(
            config,
            output_dir=tmp_path,
            no_broadcast=True,
        )

        daemon._check_and_report()

        assert daemon._report_number == 1
        assert daemon._prev_state is not None
        assert daemon._last_report_time is not None
        # Report file should exist
        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) >= 1  # At least report + latest.md symlink

    @patch("tools.progress_report.watch.extract_state")
    def test_check_no_change_no_report(self, mock_extract, tmp_path):
        """Second check with no changes doesn't generate."""
        state = ProjectState(tasks=[_task(id="1", status="open")])
        mock_extract.return_value = state

        config = ProgressReportConfig(
            triggers=TriggerConfig(
                tasks_completed=0,
                issue_completed=False,
                epic_milestone=False,
                on_failure=False,
                on_blocker=False,
                hole_created=False,
                hole_resolved=False,
                all_work_hole_blocked=False,
                interval="999h",
            )
        )
        daemon = WatchDaemon(config, output_dir=tmp_path, no_broadcast=True)

        # First call
        daemon._check_and_report()
        assert daemon._report_number == 1

        # Second call — no triggers should fire
        daemon._check_and_report()
        assert daemon._report_number == 1  # No new report

    @patch("tools.progress_report.watch.extract_state")
    def test_check_with_task_completion(self, mock_extract, tmp_path):
        """Report generated when tasks complete."""
        config = ProgressReportConfig(
            triggers=TriggerConfig(tasks_completed=1, interval="999h")
        )
        daemon = WatchDaemon(config, output_dir=tmp_path, no_broadcast=True)

        # Initial state
        mock_extract.return_value = ProjectState(
            tasks=[_task(id="1", status="open"), _task(id="2", status="open")]
        )
        daemon._check_and_report()
        assert daemon._report_number == 1

        # Clear dedup window
        daemon._last_report_time = datetime(2020, 1, 1, tzinfo=timezone.utc)

        # Task completed
        mock_extract.return_value = ProjectState(
            tasks=[_task(id="1", status="closed"), _task(id="2", status="open")]
        )
        daemon._check_and_report()
        assert daemon._report_number == 2

    @patch("tools.progress_report.watch.extract_state")
    def test_start_and_stop(self, mock_extract, tmp_path):
        """Daemon starts and can be stopped from another thread."""
        mock_extract.return_value = ProjectState(tasks=[_task()])
        config = ProgressReportConfig(
            triggers=TriggerConfig(interval="1s")
        )
        daemon = WatchDaemon(config, output_dir=tmp_path, no_broadcast=True)

        def run_daemon():
            daemon.start()

        thread = threading.Thread(target=run_daemon)
        thread.start()

        # Give the daemon time to start and do initial check
        time.sleep(0.5)
        daemon.stop()
        thread.join(timeout=5)

        assert daemon._running is False
        assert daemon._report_number >= 1  # At least initial report

    @patch("tools.progress_report.watch.extract_state")
    def test_deduplication(self, mock_extract, tmp_path):
        """Reports within 5-min window are deduplicated."""
        mock_extract.return_value = ProjectState(
            tasks=[_task(id="1", status="open")]
        )
        config = ProgressReportConfig(
            triggers=TriggerConfig(tasks_completed=1)
        )
        daemon = WatchDaemon(config, output_dir=tmp_path, no_broadcast=True)

        # Initial report
        daemon._check_and_report()
        assert daemon._report_number == 1

        # Immediately trigger again — should be deduplicated
        mock_extract.return_value = ProjectState(
            tasks=[_task(id="1", status="closed")]
        )
        daemon._check_and_report()
        assert daemon._report_number == 1  # Dedup blocked it
