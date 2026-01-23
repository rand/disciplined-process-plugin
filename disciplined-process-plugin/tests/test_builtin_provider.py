"""Tests for the builtin provider module."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from scripts.lib.builtin_provider import (
    add_blocker,
    create_task,
    ensure_env_set,
    get_ready_count,
    get_task_list_id,
    get_tasks_dir,
    list_tasks,
    update_task,
)


class TestGetTaskListId:
    """Tests for get_task_list_id function."""

    def test_returns_config_id_when_provided(self):
        """Should return the configured ID when provided."""
        project = Path("/tmp/test-project")
        result = get_task_list_id(project, "my-custom-id")
        assert result == "my-custom-id"

    def test_generates_hash_when_no_config_id(self):
        """Should generate a 12-char hash from project path."""
        project = Path("/tmp/test-project")
        result = get_task_list_id(project, None)
        assert len(result) == 12
        assert result.isalnum()

    def test_same_path_generates_same_hash(self):
        """Should be deterministic - same path produces same hash."""
        project = Path("/tmp/test-project")
        result1 = get_task_list_id(project)
        result2 = get_task_list_id(project)
        assert result1 == result2

    def test_different_paths_generate_different_hashes(self):
        """Different project paths should produce different hashes."""
        project1 = Path("/tmp/project-one")
        project2 = Path("/tmp/project-two")
        result1 = get_task_list_id(project1)
        result2 = get_task_list_id(project2)
        assert result1 != result2


class TestGetTasksDir:
    """Tests for get_tasks_dir function."""

    def test_returns_correct_path(self):
        """Should return ~/.claude/tasks/<task_list_id>/."""
        result = get_tasks_dir("test-list")
        expected = Path.home() / ".claude" / "tasks" / "test-list"
        assert result == expected


class TestEnsureEnvSet:
    """Tests for ensure_env_set function."""

    def test_sets_environment_variable(self):
        """Should set CLAUDE_CODE_TASK_LIST_ID env var."""
        # Clear any existing value
        os.environ.pop("CLAUDE_CODE_TASK_LIST_ID", None)

        ensure_env_set("my-task-list")
        assert os.environ.get("CLAUDE_CODE_TASK_LIST_ID") == "my-task-list"

        # Clean up
        os.environ.pop("CLAUDE_CODE_TASK_LIST_ID", None)


class TestListTasks:
    """Tests for list_tasks function."""

    def test_returns_empty_list_when_no_tasks_dir(self):
        """Should return empty list when tasks directory doesn't exist."""
        result = list_tasks("nonexistent-list-12345")
        assert result == []

    def test_lists_tasks_from_json_files(self, tmp_path):
        """Should read and return task data from JSON files."""
        # Create mock tasks directory
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            # Create some task files
            task1 = {"id": "1", "subject": "Task 1", "status": "pending"}
            task2 = {"id": "2", "subject": "Task 2", "status": "completed"}

            (tmp_path / "1.json").write_text(json.dumps(task1))
            (tmp_path / "2.json").write_text(json.dumps(task2))

            result = list_tasks("test-list")
            assert len(result) == 2
            subjects = {t["subject"] for t in result}
            assert subjects == {"Task 1", "Task 2"}

    def test_ignores_hidden_files(self, tmp_path):
        """Should skip files starting with dot."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            task1 = {"id": "1", "subject": "Visible"}
            hidden = {"id": "h", "subject": "Hidden"}

            (tmp_path / "1.json").write_text(json.dumps(task1))
            (tmp_path / ".hidden.json").write_text(json.dumps(hidden))

            result = list_tasks("test-list")
            assert len(result) == 1
            assert result[0]["subject"] == "Visible"


class TestGetReadyCount:
    """Tests for get_ready_count function."""

    def test_counts_pending_tasks_without_blockers(self, tmp_path):
        """Should count tasks that are pending with no blockedBy."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            # Ready: pending, no blockers
            task1 = {"id": "1", "subject": "Ready", "status": "pending", "blockedBy": []}
            # Not ready: has blocker
            task2 = {
                "id": "2",
                "subject": "Blocked",
                "status": "pending",
                "blockedBy": ["1"],
            }
            # Not ready: not pending
            task3 = {"id": "3", "subject": "Done", "status": "completed", "blockedBy": []}
            # Ready: pending, no blockedBy field
            task4 = {"id": "4", "subject": "Also Ready", "status": "pending"}

            (tmp_path / "1.json").write_text(json.dumps(task1))
            (tmp_path / "2.json").write_text(json.dumps(task2))
            (tmp_path / "3.json").write_text(json.dumps(task3))
            (tmp_path / "4.json").write_text(json.dumps(task4))

            result = get_ready_count("test-list")
            assert result == 2


class TestCreateTask:
    """Tests for create_task function."""

    def test_creates_task_with_defaults(self, tmp_path):
        """Should create task with default values."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            task = create_task("test-list", "My Task")

            assert task["id"] == "1"
            assert task["subject"] == "My Task"
            assert task["description"] == ""
            assert task["status"] == "pending"
            assert task["blocks"] == []
            assert task["blockedBy"] == []

            # Verify file was created
            task_file = tmp_path / "1.json"
            assert task_file.exists()

    def test_creates_task_with_description(self, tmp_path):
        """Should include description when provided."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            task = create_task("test-list", "My Task", description="Details here")
            assert task["description"] == "Details here"

    def test_creates_task_with_active_form(self, tmp_path):
        """Should include activeForm when provided."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            task = create_task(
                "test-list", "Run tests", active_form="Running tests"
            )
            assert task["activeForm"] == "Running tests"

    def test_increments_task_id(self, tmp_path):
        """Should increment ID based on existing tasks."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            task1 = create_task("test-list", "First")
            task2 = create_task("test-list", "Second")
            task3 = create_task("test-list", "Third")

            assert task1["id"] == "1"
            assert task2["id"] == "2"
            assert task3["id"] == "3"


class TestUpdateTask:
    """Tests for update_task function."""

    def test_updates_existing_task(self, tmp_path):
        """Should update fields on existing task."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            # Create a task first
            create_task("test-list", "Original")

            # Update it
            updated = update_task("test-list", "1", status="in_progress")

            assert updated["status"] == "in_progress"
            assert updated["subject"] == "Original"

    def test_returns_none_for_nonexistent_task(self, tmp_path):
        """Should return None when task doesn't exist."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            result = update_task("test-list", "999", status="done")
            assert result is None

    def test_merges_blocker_lists(self, tmp_path):
        """Should merge blockedBy lists instead of replacing."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            # Create task with existing blocker
            task_data = {
                "id": "1",
                "subject": "Test",
                "status": "pending",
                "blockedBy": ["2"],
                "blocks": [],
            }
            (tmp_path / "1.json").write_text(json.dumps(task_data))

            # Add another blocker
            updated = update_task("test-list", "1", blockedBy=["3"])

            assert set(updated["blockedBy"]) == {"2", "3"}


class TestAddBlocker:
    """Tests for add_blocker function."""

    def test_adds_bidirectional_blocking(self, tmp_path):
        """Should update both tasks with blocking relationship."""
        with mock.patch(
            "scripts.lib.builtin_provider.get_tasks_dir", return_value=tmp_path
        ):
            # Create two tasks
            create_task("test-list", "Task 1")
            create_task("test-list", "Task 2")

            # Task 2 is blocked by Task 1
            result = add_blocker("test-list", "2", "1")
            assert result is True

            # Verify Task 2 has Task 1 in blockedBy
            task2_file = tmp_path / "2.json"
            task2 = json.loads(task2_file.read_text())
            assert "1" in task2["blockedBy"]

            # Verify Task 1 has Task 2 in blocks
            task1_file = tmp_path / "1.json"
            task1 = json.loads(task1_file.read_text())
            assert "2" in task1["blocks"]
