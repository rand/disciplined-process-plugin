#!/usr/bin/env python3
"""
Pre-push sync - ensure task tracker is synced before pushing.

Gracefully skips if provider unavailable.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib import get_config
from lib.providers import (
    check_provider_available,
    feedback,
    get_project_dir,
    sync_tracker,
)


def main() -> int:
    """Main entry point."""
    project_dir = get_project_dir()

    try:
        config = get_config()
    except Exception:
        # If config can't be loaded, skip sync
        return 0

    tracker = config.task_tracker

    # Check if provider is available
    status = check_provider_available(tracker, project_dir)
    if not status.available:
        # Silently skip if provider not available
        return 0

    # Sync tracker
    if sync_tracker(tracker, project_dir):
        # Sync successful or not needed
        return 0
    else:
        # Sync failed - warn but don't block
        feedback("⚠️ Task tracker sync failed. Run 'bd sync' manually after push.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
