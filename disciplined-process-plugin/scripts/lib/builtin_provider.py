"""
Builtin provider for Claude Code's native task system.

Tasks are stored in ~/.claude/tasks/<task_list_id>/<task_id>.json
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def get_task_list_id(project_dir: Path, config_id: str | None = None) -> str:
    """
    Get or generate task list ID for project isolation.

    Args:
        project_dir: The project directory to hash
        config_id: Optional configured ID (takes precedence)

    Returns:
        Task list ID string (12-char hash or configured value)
    """
    if config_id:
        return config_id
    # Generate from project path
    return hashlib.sha256(str(project_dir.resolve()).encode()).hexdigest()[:12]


def get_tasks_dir(task_list_id: str) -> Path:
    """Get the tasks directory for a task list."""
    return Path.home() / ".claude" / "tasks" / task_list_id


def ensure_env_set(task_list_id: str) -> None:
    """Ensure CLAUDE_CODE_TASK_LIST_ID is set for current process."""
    os.environ["CLAUDE_CODE_TASK_LIST_ID"] = task_list_id


def list_tasks(task_list_id: str) -> list[dict]:
    """
    List all tasks in task list.

    Args:
        task_list_id: The task list to query

    Returns:
        List of task dictionaries
    """
    tasks_dir = get_tasks_dir(task_list_id)
    if not tasks_dir.exists():
        return []

    tasks = []
    for task_file in tasks_dir.glob("*.json"):
        if task_file.name.startswith("."):
            continue
        try:
            with open(task_file) as f:
                tasks.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return tasks


def get_ready_count(task_list_id: str) -> int:
    """
    Count tasks that are ready (pending, no blockers).

    Args:
        task_list_id: The task list to query

    Returns:
        Count of ready tasks
    """
    tasks = list_tasks(task_list_id)
    return sum(
        1
        for t in tasks
        if t.get("status") == "pending" and not t.get("blockedBy", [])
    )


def create_task(
    task_list_id: str,
    subject: str,
    description: str = "",
    active_form: str | None = None,
) -> dict:
    """
    Create a new task.

    Args:
        task_list_id: The task list to create in
        subject: Task title
        description: Task description
        active_form: Present continuous form for spinner

    Returns:
        The created task dictionary
    """
    tasks_dir = get_tasks_dir(task_list_id)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Find next ID
    existing = list_tasks(task_list_id)
    next_id = str(max((int(t["id"]) for t in existing), default=0) + 1)

    task = {
        "id": next_id,
        "subject": subject,
        "description": description,
        "status": "pending",
        "blocks": [],
        "blockedBy": [],
    }

    if active_form:
        task["activeForm"] = active_form

    task_file = tasks_dir / f"{next_id}.json"
    with open(task_file, "w") as f:
        json.dump(task, f, indent=2)

    return task


def update_task(task_list_id: str, task_id: str, **updates) -> dict | None:
    """
    Update an existing task.

    Args:
        task_list_id: The task list containing the task
        task_id: The task ID to update
        **updates: Fields to update (status, subject, description, etc.)

    Returns:
        Updated task dictionary, or None if not found
    """
    tasks_dir = get_tasks_dir(task_list_id)
    task_file = tasks_dir / f"{task_id}.json"

    if not task_file.exists():
        return None

    try:
        with open(task_file) as f:
            task = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # Apply updates
    for key, value in updates.items():
        if key in ("blocks", "blockedBy") and isinstance(value, list):
            # Merge lists for dependency updates
            existing = task.get(key, [])
            task[key] = list(set(existing + value))
        else:
            task[key] = value

    with open(task_file, "w") as f:
        json.dump(task, f, indent=2)

    return task


def add_blocker(task_list_id: str, task_id: str, blocker_id: str) -> bool:
    """
    Add a blocker to a task.

    Args:
        task_list_id: The task list
        task_id: The task being blocked
        blocker_id: The task that blocks it

    Returns:
        True if successful
    """
    result = update_task(task_list_id, task_id, blockedBy=[blocker_id])
    if result:
        # Also update the blocker's blocks list
        update_task(task_list_id, blocker_id, blocks=[task_id])
        return True
    return False
