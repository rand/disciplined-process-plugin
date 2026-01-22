"""
Provider detection and availability utilities for disciplined-process hooks.

Handles checking for CLI availability and provider-specific operations.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import DPConfig, DegradationAction, TaskTracker, get_config


@dataclass
class ProviderStatus:
    """Status of a task tracker provider."""

    available: bool
    reason: str | None = None
    ready_count: int | None = None


def get_project_dir() -> Path:
    """Get the project directory from environment or current working directory."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))


def get_warn_file() -> Path:
    """Get the path to the provider warning file."""
    return get_project_dir() / ".claude" / ".dp-provider-warned"


def check_cli_available(command: str) -> bool:
    """Check if a CLI command is available on the system."""
    return shutil.which(command) is not None


def check_provider_available(tracker: TaskTracker, project_dir: Path | None = None) -> ProviderStatus:
    """
    Check if a task tracker provider is available and configured.

    Args:
        tracker: The task tracker type to check
        project_dir: The project directory (defaults to CLAUDE_PROJECT_DIR)

    Returns:
        ProviderStatus with availability info
    """
    if project_dir is None:
        project_dir = get_project_dir()

    match tracker:
        case TaskTracker.BEADS:
            if not check_cli_available("bd"):
                return ProviderStatus(False, "'bd' CLI not found. Run 'pip install beads' or change provider.")
            beads_dir = project_dir / ".beads"
            if not beads_dir.is_dir():
                return ProviderStatus(False, ".beads/ not initialized. Run 'bd init' in project root.")
            return ProviderStatus(True)

        case TaskTracker.CHAINLINK:
            # Chainlink uses local markdown files, always available
            return ProviderStatus(True)

        case TaskTracker.GITHUB:
            if not check_cli_available("gh"):
                return ProviderStatus(False, "'gh' CLI not found. Install GitHub CLI or change provider.")
            return ProviderStatus(True)

        case TaskTracker.LINEAR:
            if not check_cli_available("linear"):
                return ProviderStatus(False, "'linear' CLI not found. Install Linear CLI or change provider.")
            return ProviderStatus(True)

        case TaskTracker.MARKDOWN:
            # Always available - uses local files
            return ProviderStatus(True)

        case TaskTracker.NONE:
            return ProviderStatus(True)

        case _:
            return ProviderStatus(False, f"Unknown provider: {tracker}")


def should_warn_about_provider(warn_file: Path | None = None) -> bool:
    """
    Check if we should warn about a missing provider.

    Only warns once per day to avoid spam.
    """
    if warn_file is None:
        warn_file = get_warn_file()

    if not warn_file.exists():
        return True

    # Check if warning is older than 24 hours
    try:
        mtime = datetime.fromtimestamp(warn_file.stat().st_mtime)
        return datetime.now() - mtime > timedelta(hours=24)
    except (OSError, ValueError):
        return True


def mark_provider_warned(warn_file: Path | None = None) -> None:
    """Mark that we've warned about the provider."""
    if warn_file is None:
        warn_file = get_warn_file()

    warn_file.parent.mkdir(parents=True, exist_ok=True)
    warn_file.touch()


def get_ready_count(tracker: TaskTracker, project_dir: Path | None = None) -> int | None:
    """
    Get the count of ready tasks for a provider.

    Returns None if unable to get count.
    """
    if project_dir is None:
        project_dir = get_project_dir()

    try:
        match tracker:
            case TaskTracker.BEADS:
                result = subprocess.run(
                    ["bd", "ready", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=project_dir,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    return len(data) if isinstance(data, list) else None
                return None

            case TaskTracker.GITHUB:
                result = subprocess.run(
                    ["gh", "issue", "list", "--label", "ready", "--json", "number"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=project_dir,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    return len(data) if isinstance(data, list) else None
                return None

            case TaskTracker.MARKDOWN:
                tasks_dir = project_dir / "docs" / "tasks"
                if not tasks_dir.is_dir():
                    return 0
                count = 0
                for md_file in tasks_dir.glob("*.md"):
                    try:
                        content = md_file.read_text()
                        if "status: ready" in content.lower():
                            count += 1
                    except (OSError, UnicodeDecodeError):
                        continue
                return count

            case TaskTracker.CHAINLINK:
                # Chainlink uses beads under the hood if available
                if check_cli_available("bd") and (project_dir / ".beads").is_dir():
                    return get_ready_count(TaskTracker.BEADS, project_dir)
                return None

            case TaskTracker.NONE:
                return None

            case _:
                return None

    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def sync_tracker(tracker: TaskTracker, project_dir: Path | None = None) -> bool:
    """
    Sync the task tracker.

    Returns True if sync was successful or not needed.
    """
    if project_dir is None:
        project_dir = get_project_dir()

    try:
        match tracker:
            case TaskTracker.BEADS | TaskTracker.CHAINLINK:
                if check_cli_available("bd") and (project_dir / ".beads").is_dir():
                    result = subprocess.run(
                        ["bd", "sync"],
                        capture_output=True,
                        timeout=30,
                        cwd=project_dir,
                    )
                    return result.returncode == 0
                return True  # No sync needed if bd not available

            case TaskTracker.GITHUB | TaskTracker.LINEAR:
                # These sync automatically via their CLIs
                return True

            case TaskTracker.MARKDOWN | TaskTracker.NONE:
                # No sync needed
                return True

            case _:
                return True

    except subprocess.TimeoutExpired:
        return False


# Output helpers for hook feedback


def feedback(message: str) -> None:
    """Output a feedback message in Claude hook format."""
    print(json.dumps({"feedback": message}))


def error(message: str) -> None:
    """Output an error message in Claude hook format."""
    print(json.dumps({"error": message}))


def output(data: dict[str, Any]) -> None:
    """Output arbitrary JSON data."""
    print(json.dumps(data))


def handle_degradation(
    action: DegradationAction,
    message: str,
    exit_on_fail: bool = True,
) -> bool:
    """
    Handle a degradation scenario based on configured action.

    Args:
        action: The configured degradation action
        message: The message to display
        exit_on_fail: Whether to exit with error code on FAIL action

    Returns:
        True if execution should continue, False if it should stop
    """
    match action:
        case DegradationAction.WARN:
            feedback(f"Warning: {message}")
            return True
        case DegradationAction.SKIP:
            return True
        case DegradationAction.FAIL:
            error(message)
            if exit_on_fail:
                raise SystemExit(1)
            return False
    return True
