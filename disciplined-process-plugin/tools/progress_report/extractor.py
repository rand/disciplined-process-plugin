# @trace SPEC-08
"""State extraction from Beads, git, and task files.

Gathers project state into a structured ProjectState dataclass
for use by the report generator and trigger evaluator.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TaskState:
    """State of a single work item."""

    id: str
    title: str
    status: str  # open, in_progress, closed
    priority: int = 2
    labels: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    is_hole: bool = False
    hole_type: str = ""
    closed_at: str = ""


@dataclass
class GitState:
    """State from git log and diff."""

    recent_commits: list[dict[str, str]] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    current_branch: str = ""


@dataclass
class ProjectState:
    """Complete snapshot of project state."""

    tasks: list[TaskState] = field(default_factory=list)
    git: GitState = field(default_factory=GitState)

    # Derived statistics
    @property
    def total_tasks(self) -> int:
        return len([t for t in self.tasks if not t.is_hole])

    @property
    def completed_tasks(self) -> int:
        return len(
            [t for t in self.tasks if not t.is_hole and t.status == "closed"]
        )

    @property
    def in_progress_tasks(self) -> int:
        return len(
            [t for t in self.tasks if not t.is_hole and t.status == "in_progress"]
        )

    @property
    def open_tasks(self) -> int:
        return len(
            [t for t in self.tasks if not t.is_hole and t.status == "open"]
        )

    @property
    def blocked_tasks(self) -> list[TaskState]:
        return [t for t in self.tasks if not t.is_hole and t.blocked_by]

    @property
    def ready_tasks(self) -> list[TaskState]:
        return [
            t
            for t in self.tasks
            if not t.is_hole and t.status == "open" and not t.blocked_by
        ]

    @property
    def total_holes(self) -> int:
        return len([t for t in self.tasks if t.is_hole])

    @property
    def open_holes(self) -> list[TaskState]:
        return [t for t in self.tasks if t.is_hole and t.status != "closed"]

    @property
    def resolved_holes(self) -> list[TaskState]:
        return [t for t in self.tasks if t.is_hole and t.status == "closed"]

    @property
    def progress_ratio(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    @property
    def all_work_hole_blocked(self) -> bool:
        """True if all remaining work is blocked by open holes."""
        if not self.open_holes:
            return False
        ready = self.ready_tasks
        in_progress = [t for t in self.tasks if t.status == "in_progress"]
        return len(ready) == 0 and len(in_progress) == 0


def extract_state(project_root: Path | None = None) -> ProjectState:
    """Extract project state from Beads and git.

    Args:
        project_root: Root directory of the project.

    Returns:
        ProjectState with current task and git info.
    """
    if project_root is None:
        project_root = Path(".")

    state = ProjectState()

    # Extract from Beads
    state.tasks = _extract_beads_state(project_root)

    # Extract from git
    state.git = _extract_git_state(project_root)

    return state


def _extract_beads_state(project_root: Path) -> list[TaskState]:
    """Extract task state from Beads."""
    tasks: list[TaskState] = []

    try:
        result = subprocess.run(
            ["bd", "list", "--json"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=10,
        )
        if result.returncode != 0:
            return tasks

        issues = json.loads(result.stdout)
        if not isinstance(issues, list):
            return tasks

        for issue in issues:
            labels = issue.get("labels", [])
            is_hole = any(l.startswith("hole") for l in labels)
            hole_type = ""
            if is_hole:
                for l in labels:
                    if l.startswith("hole:") and l not in (
                        "hole:agent-resolvable",
                        "hole:human-required",
                    ):
                        hole_type = l.split(":", 1)[1]
                        break

            blocked_by = [
                d.get("id", "") for d in issue.get("blocked_by", [])
            ]

            tasks.append(
                TaskState(
                    id=issue.get("id", ""),
                    title=issue.get("title", ""),
                    status=issue.get("status", "open"),
                    priority=issue.get("priority", 2),
                    labels=labels,
                    blocked_by=blocked_by,
                    is_hole=is_hole,
                    hole_type=hole_type,
                    closed_at=issue.get("closed_at", ""),
                )
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass

    return tasks


def _extract_git_state(project_root: Path) -> GitState:
    """Extract git log and diff state."""
    git = GitState()

    try:
        # Current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=5,
        )
        if result.returncode == 0:
            git.current_branch = result.stdout.strip()

        # Recent commits (last 10)
        result = subprocess.run(
            ["git", "log", "--oneline", "-10", "--format=%H|%s|%an|%aI"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 3)
                if len(parts) >= 2:
                    git.recent_commits.append(
                        {
                            "hash": parts[0][:8],
                            "message": parts[1],
                            "author": parts[2] if len(parts) > 2 else "",
                            "date": parts[3] if len(parts) > 3 else "",
                        }
                    )

        # Files changed (uncommitted)
        result = subprocess.run(
            ["git", "diff", "--stat", "--name-only"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=5,
        )
        if result.returncode == 0:
            git.files_changed = [
                f for f in result.stdout.strip().split("\n") if f
            ]

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return git


def extract_state_from_json(
    issues_json: list[dict[str, Any]],
    git_state: GitState | None = None,
) -> ProjectState:
    """Build ProjectState from pre-loaded JSON (for testing or API use).

    Args:
        issues_json: List of issue dicts (as from bd list --json).
        git_state: Optional pre-built git state.

    Returns:
        ProjectState.
    """
    state = ProjectState()
    state.git = git_state or GitState()

    for issue in issues_json:
        labels = issue.get("labels", [])
        is_hole = any(l.startswith("hole") for l in labels)
        hole_type = ""
        if is_hole:
            for l in labels:
                if l.startswith("hole:") and l not in (
                    "hole:agent-resolvable",
                    "hole:human-required",
                ):
                    hole_type = l.split(":", 1)[1]
                    break

        blocked_by = [d.get("id", "") for d in issue.get("blocked_by", [])]

        state.tasks.append(
            TaskState(
                id=issue.get("id", ""),
                title=issue.get("title", ""),
                status=issue.get("status", "open"),
                priority=issue.get("priority", 2),
                labels=labels,
                blocked_by=blocked_by,
                is_hole=is_hole,
                hole_type=hole_type,
                closed_at=issue.get("closed_at", ""),
            )
        )

    return state
