#!/usr/bin/env python3
"""
Stop hook - handle session handoff and sync tracker.

Runs when Claude Code session ends to:
1. Prompt for session handoff notes (Chainlink)
2. Sync issue tracker
3. Show session summary
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import DPConfig, TaskTracker, get_config
from lib.providers import (
    check_cli_available,
    feedback,
    get_project_dir,
    sync_tracker,
)


def get_chainlink_session_status(project_dir: Path) -> dict | None:
    """Get current Chainlink session status."""
    if not check_cli_available("chainlink"):
        return None

    chainlink_dir = project_dir / ".chainlink"
    if not chainlink_dir.is_dir():
        return None

    try:
        result = subprocess.run(
            ["chainlink", "session", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse session info
            return {
                "active": "No active session" not in output,
                "output": output,
            }
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def end_chainlink_session(project_dir: Path, notes: str = "") -> bool:
    """End the current Chainlink session with handoff notes."""
    if not check_cli_available("chainlink"):
        return False

    try:
        cmd = ["chainlink", "session", "end"]
        if notes:
            cmd.extend(["--notes", notes])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir,
        )

        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def get_session_summary(project_dir: Path, config: DPConfig) -> dict:
    """Generate session summary."""
    summary = {
        "tracker": config.task_tracker.value,
        "synced": False,
        "session_ended": False,
    }

    # Get git status for summary
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir,
        )
        if result.returncode == 0:
            changes = [l for l in result.stdout.strip().split("\n") if l.strip()]
            summary["uncommitted_changes"] = len(changes)
    except (subprocess.TimeoutExpired, OSError):
        pass

    return summary


def format_session_end_message(summary: dict, config: DPConfig) -> str:
    """Format the session end message."""
    lines = [
        "",
        "=" * 50,
        "Session Ending",
        "=" * 50,
        "",
    ]

    if summary.get("uncommitted_changes", 0) > 0:
        lines.append(
            f"Warning: {summary['uncommitted_changes']} uncommitted changes"
        )
        lines.append("Consider: git add && git commit before closing")
        lines.append("")

    if config.task_tracker == TaskTracker.CHAINLINK:
        lines.append("Chainlink session status:")
        if summary.get("session_ended"):
            lines.append("  Session ended with handoff notes saved")
        else:
            lines.append("  Use /dp:session end --notes '...' to save context")
        lines.append("")

    if summary.get("synced"):
        lines.append(f"Tracker synced: {config.task_tracker.value}")
    else:
        lines.append(f"Sync tracker: bd sync (or git push for Chainlink)")

    lines.extend([
        "",
        "=" * 50,
    ])

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    try:
        project_dir = get_project_dir()
        config = get_config()

        # Generate session summary
        summary = get_session_summary(project_dir, config)

        # Handle Chainlink session
        if config.task_tracker == TaskTracker.CHAINLINK:
            session_status = get_chainlink_session_status(project_dir)
            if session_status and session_status.get("active"):
                # Session is active - remind user to end it
                feedback(
                    "Active Chainlink session detected. "
                    "Use '/dp:session end --notes \"...\"' to save handoff notes."
                )

        # Sync tracker
        if sync_tracker(config.task_tracker, project_dir):
            summary["synced"] = True

        # Output session end message
        message = format_session_end_message(summary, config)
        feedback(message)

        # Output JSON for hook system
        print(
            json.dumps({
                "continue": True,
                "summary": summary,
            })
        )

        return 0

    except Exception as e:
        feedback(f"Warning: Stop handler error: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
