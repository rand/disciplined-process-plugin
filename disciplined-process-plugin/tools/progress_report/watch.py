# @trace SPEC-08
"""Watch daemon for progress reports.

Polling loop that queries Beads state at configured intervals,
evaluates trigger conditions, and generates reports.
"""

from __future__ import annotations

import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.progress_report.broadcast import broadcast_report
from tools.progress_report.extractor import ProjectState, extract_state
from tools.progress_report.report import generate_report_json, write_report
from tools.progress_report.triggers import (
    evaluate_triggers,
    should_deduplicate,
)
from tools.shared.config import ProgressReportConfig, parse_interval


class WatchDaemon:
    """Polling daemon for progress reporting."""

    def __init__(
        self,
        config: ProgressReportConfig,
        project_root: Path | None = None,
        output_dir: Path | None = None,
        epic_title: str = "Project",
        no_broadcast: bool = False,
    ):
        self.config = config
        self.project_root = project_root or Path(".")
        self.output_dir = output_dir or Path("docs/progress")
        self.epic_title = epic_title
        self.no_broadcast = no_broadcast

        self._running = False
        self._prev_state: ProjectState | None = None
        self._last_report_time: datetime | None = None
        self._report_number = 0
        self._poll_interval = parse_interval(
            config.triggers.interval or "60s"
        )

    def start(self) -> None:
        """Start the watch loop. Blocks until stopped."""
        self._running = True
        self._setup_signal_handlers()

        print(
            f"Watch mode started. Polling every {self._poll_interval}s. "
            f"Press Ctrl+C to stop.",
            file=sys.stderr,
        )

        # Initial report
        self._check_and_report()

        while self._running:
            time.sleep(min(self._poll_interval, 5))
            if not self._running:
                break
            self._check_and_report()

        print("Watch mode stopped.", file=sys.stderr)

    def stop(self) -> None:
        """Signal the watch loop to stop."""
        self._running = False

    def _setup_signal_handlers(self) -> None:
        """Handle SIGTERM/SIGINT for clean shutdown (main thread only)."""
        import threading

        if threading.current_thread() is not threading.main_thread():
            return

        def handler(signum: int, frame: Any) -> None:
            self.stop()

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    def _check_and_report(self) -> None:
        """Check trigger conditions and generate report if needed."""
        curr_state = extract_state(self.project_root)

        result = evaluate_triggers(
            self.config.triggers,
            prev_state=self._prev_state,
            curr_state=curr_state,
            last_report_time=self._last_report_time,
        )

        if not result.should_report:
            return

        # Deduplication check
        if should_deduplicate(self._last_report_time):
            return

        self._report_number += 1
        md_path, json_path = write_report(
            curr_state,
            trigger_reason=result.reason,
            report_number=self._report_number,
            prev_state=self._prev_state,
            last_report_time=self._last_report_time,
            epic_title=self.epic_title,
            output_dir=self.output_dir,
        )

        print(f"Report #{self._report_number}: {md_path}", file=sys.stderr)

        # Broadcast
        if not self.no_broadcast:
            json_data = json.loads(json_path.read_text())
            md_content = md_path.read_text()
            for trigger in result.fired:
                delivered = broadcast_report(
                    self.config.broadcast,
                    md_content,
                    json_data,
                    trigger,
                    self.output_dir,
                )
                if delivered:
                    print(
                        f"  Broadcast to: {', '.join(delivered)}",
                        file=sys.stderr,
                    )

        self._prev_state = curr_state
        self._last_report_time = datetime.now(timezone.utc)
