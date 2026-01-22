#!/usr/bin/env python3
"""
Session start hook - show ready work and context.

Gracefully handles missing CLIs and misconfigured providers.
Runs health checks and reports degradation level.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib import DPConfig, TaskTracker, get_config
from lib.degradation import (
    DegradationLevel,
    get_current_level,
    run_health_checks,
)
from lib.providers import (
    check_cli_available,
    check_provider_available,
    feedback,
    get_project_dir,
    get_ready_count,
    handle_degradation,
    mark_provider_warned,
    should_warn_about_provider,
)
import subprocess


def run_startup_health_check() -> DegradationLevel:
    """Run health checks and return current level."""
    try:
        state = run_health_checks()
        return state.level
    except Exception:
        return DegradationLevel.FULL


def show_degradation_status(level: DegradationLevel) -> None:
    """Show degradation status if not at full level."""
    if level == DegradationLevel.FULL:
        return

    level_messages = {
        DegradationLevel.REDUCED: "⚠️ Running in reduced mode (some features disabled). Run '/dp:health' for details.",
        DegradationLevel.MANUAL: "⚠️ Running in manual mode (requires intervention). Run '/dp:health' for details.",
        DegradationLevel.SAFE: "🔒 Running in safe mode (minimal operation). Run '/dp:repair' to attempt recovery.",
        DegradationLevel.RECOVERY: "🔄 Recovery in progress. Run '/dp:health' for status.",
    }

    message = level_messages.get(level)
    if message:
        feedback(message)


def show_chainlink_session_context(config: DPConfig, project_dir: Path) -> None:
    """Show Chainlink session context if available."""
    if config.task_tracker != TaskTracker.CHAINLINK:
        return

    if not check_cli_available("chainlink"):
        return

    chainlink_dir = project_dir / ".chainlink"
    if not chainlink_dir.is_dir():
        return

    try:
        # Get session status
        result = subprocess.run(
            ["chainlink", "session", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir,
        )

        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            # Check if there's an active session or handoff notes
            if "No active session" not in output:
                feedback(f"📝 Active session:\n{output}")
            elif "Handoff notes" in output or "Previous session" in output:
                # Show handoff notes from previous session
                feedback(f"📝 Previous session context:\n{output}")
                feedback("Start new session with: /dp:session start")
    except (subprocess.TimeoutExpired, OSError):
        pass  # Fail silently - session info is nice-to-have


def show_ready_work(config: DPConfig, level: DegradationLevel) -> None:
    """Show ready work based on configured task tracker."""
    # Skip task tracking if in safe mode
    if level == DegradationLevel.SAFE:
        return

    tracker = config.task_tracker
    project_dir = get_project_dir()

    # Check provider availability
    status = check_provider_available(tracker, project_dir)

    if not status.available:
        # Handle unavailable provider
        if should_warn_about_provider():
            mark_provider_warned()
            handle_degradation(
                config.degradation.on_tracker_unavailable,
                f"Task provider '{tracker.value}' unavailable: {status.reason}",
                exit_on_fail=False,
            )
        return

    # Skip if no tracking configured
    if tracker == TaskTracker.NONE:
        return

    # Get ready count
    ready_count = get_ready_count(tracker, project_dir)

    if ready_count is not None and ready_count > 0:
        feedback(f"📋 {ready_count} tasks ready. Run '/dp:task ready' to see them.")


def main() -> int:
    """Main entry point."""
    try:
        # Run health checks first
        level = run_startup_health_check()

        # Show degradation status if not full
        show_degradation_status(level)

        # Load config
        config = get_config()
        project_dir = get_project_dir()

        # Show Chainlink session context if available
        show_chainlink_session_context(config, project_dir)

        # Show ready work
        show_ready_work(config, level)

        return 0
    except Exception as e:
        # Hooks should never crash - fail gracefully
        feedback(f"⚠️ Session start hook error: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
