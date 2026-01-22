#!/usr/bin/env python3
"""
Session start hook - show ready work and context.

Gracefully handles missing CLIs and misconfigured providers.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib import DPConfig, TaskTracker, get_config
from lib.providers import (
    check_provider_available,
    feedback,
    get_project_dir,
    get_ready_count,
    handle_degradation,
    mark_provider_warned,
    should_warn_about_provider,
)


def show_ready_work(config: DPConfig) -> None:
    """Show ready work based on configured task tracker."""
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
        config = get_config()
        show_ready_work(config)
        return 0
    except Exception as e:
        # Hooks should never crash - fail gracefully
        feedback(f"⚠️ Session start hook error: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
