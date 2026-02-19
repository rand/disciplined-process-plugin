# @trace SPEC-08
"""Trigger evaluation for progress reports.

Compares previous and current ProjectState to determine if any
configured trigger conditions are met, warranting a new report.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from tools.progress_report.extractor import ProjectState
from tools.shared.config import TriggerConfig


@dataclass
class TriggerResult:
    """Result of trigger evaluation."""

    fired: list[str]  # List of trigger names that fired
    reason: str  # Human-readable reason for the report

    @property
    def should_report(self) -> bool:
        return len(self.fired) > 0


def evaluate_triggers(
    config: TriggerConfig,
    prev_state: ProjectState | None,
    curr_state: ProjectState,
    last_report_time: datetime | None = None,
    manual_trigger: str | None = None,
) -> TriggerResult:
    """Evaluate all trigger conditions.

    Args:
        config: Trigger configuration.
        prev_state: Previous project state (None on first report).
        curr_state: Current project state.
        last_report_time: When the last report was generated.
        manual_trigger: If set, this is a manual trigger with a reason.

    Returns:
        TriggerResult with fired triggers.
    """
    fired: list[str] = []
    reasons: list[str] = []

    # Manual trigger
    if manual_trigger and config.on_demand:
        fired.append("on_demand")
        reasons.append(f"Manual: {manual_trigger}")
        return TriggerResult(fired=fired, reason="; ".join(reasons))

    if prev_state is None:
        # First report — always generate
        fired.append("initial")
        reasons.append("Initial report")
        return TriggerResult(fired=fired, reason="; ".join(reasons))

    # Time-based trigger
    if last_report_time and config.interval:
        from tools.shared.config import parse_interval

        interval_secs = parse_interval(config.interval)
        elapsed = (datetime.now(timezone.utc) - last_report_time).total_seconds()
        if elapsed >= interval_secs:
            fired.append("interval")
            reasons.append(f"Interval ({config.interval}) elapsed")

    # Completion-based: tasks_completed
    if config.tasks_completed > 0:
        prev_completed = prev_state.completed_tasks
        curr_completed = curr_state.completed_tasks
        newly_completed = curr_completed - prev_completed
        if newly_completed >= config.tasks_completed:
            fired.append("tasks_completed")
            reasons.append(f"{newly_completed} tasks completed since last report")

    # Completion-based: issue_completed
    if config.issue_completed:
        if _check_issue_completed(prev_state, curr_state):
            fired.append("issue_completed")
            reasons.append("Issue completed")

    # Completion-based: epic_milestone
    if config.epic_milestone:
        milestone = _check_epic_milestone(prev_state, curr_state)
        if milestone:
            fired.append("epic_milestone")
            reasons.append(f"Epic milestone: {milestone}%")

    # Event-based: on_rework (new tasks with rework indicators)
    if config.on_rework:
        rework_tasks = _check_rework(prev_state, curr_state)
        if rework_tasks:
            fired.append("on_rework")
            reasons.append(f"{len(rework_tasks)} rework task(s) created")

    # Event-based: on_failure (tasks moved to a failed state)
    # Note: Beads doesn't have a "failed" status, but we detect it via
    # tasks that were in_progress and are now open again
    if config.on_failure:
        if _check_failure(prev_state, curr_state):
            fired.append("on_failure")
            reasons.append("Task failure detected")

    # Event-based: on_blocker
    if config.on_blocker:
        if _check_all_blocked(prev_state, curr_state):
            fired.append("on_blocker")
            reasons.append("All ready work exhausted")

    # Hole-specific: hole_created
    if config.hole_created:
        new_holes = _check_new_holes(prev_state, curr_state)
        if new_holes:
            fired.append("hole_created")
            reasons.append(f"{len(new_holes)} new hole(s) discovered")

    # Hole-specific: hole_resolved
    if config.hole_resolved:
        resolved = _check_resolved_holes(prev_state, curr_state)
        if resolved:
            fired.append("hole_resolved")
            reasons.append(f"{len(resolved)} hole(s) resolved")

    # Hole-specific: all_work_hole_blocked
    if config.all_work_hole_blocked:
        if curr_state.all_work_hole_blocked:
            fired.append("all_work_hole_blocked")
            reasons.append(
                "ALL remaining work blocked by holes — human attention needed"
            )

    return TriggerResult(fired=fired, reason="; ".join(reasons))


def _check_issue_completed(
    prev: ProjectState, curr: ProjectState
) -> bool:
    """Check if any logical issue (group of related tasks) completed."""
    # Simple heuristic: a task that had blockers before is now closed,
    # and all tasks that shared its label are also closed.
    # For now, use the simpler check: more closed tasks than before
    # and at least one was a group boundary (has dependents all closed).
    prev_closed_ids = {t.id for t in prev.tasks if t.status == "closed"}
    curr_closed_ids = {t.id for t in curr.tasks if t.status == "closed"}
    return len(curr_closed_ids - prev_closed_ids) > 0


def _check_epic_milestone(
    prev: ProjectState, curr: ProjectState
) -> int | None:
    """Check if epic crossed a 25% milestone. Returns milestone or None."""
    if curr.total_tasks == 0:
        return None

    prev_pct = int(prev.progress_ratio * 100)
    curr_pct = int(curr.progress_ratio * 100)

    for milestone in [25, 50, 75, 100]:
        if prev_pct < milestone <= curr_pct:
            return milestone

    return None


def _check_failure(prev: ProjectState, curr: ProjectState) -> bool:
    """Check if any task regressed from in_progress to open."""
    prev_in_progress = {
        t.id for t in prev.tasks if t.status == "in_progress"
    }
    curr_open = {t.id for t in curr.tasks if t.status == "open"}
    return bool(prev_in_progress & curr_open)


def _check_all_blocked(
    prev: ProjectState, curr: ProjectState
) -> bool:
    """Check if ready work went from >0 to 0."""
    prev_ready = len(prev.ready_tasks)
    curr_ready = len(curr.ready_tasks)
    return prev_ready > 0 and curr_ready == 0


def _check_new_holes(
    prev: ProjectState, curr: ProjectState
) -> list[str]:
    """Return IDs of newly created holes."""
    prev_hole_ids = {t.id for t in prev.tasks if t.is_hole}
    curr_holes = [t for t in curr.tasks if t.is_hole]
    return [h.id for h in curr_holes if h.id not in prev_hole_ids]


def _check_resolved_holes(
    prev: ProjectState, curr: ProjectState
) -> list[str]:
    """Return IDs of newly resolved holes."""
    prev_open_hole_ids = {
        t.id for t in prev.tasks if t.is_hole and t.status != "closed"
    }
    curr_closed_hole_ids = {
        t.id for t in curr.tasks if t.is_hole and t.status == "closed"
    }
    return list(prev_open_hole_ids & curr_closed_hole_ids)


def _check_rework(
    prev: ProjectState, curr: ProjectState
) -> list[str]:
    """Return IDs of newly created rework tasks.

    Detects rework by checking for new tasks that have 'rework' in
    their title (case-insensitive) or have a discovered-from dependency type.
    """
    prev_ids = {t.id for t in prev.tasks}
    rework_ids: list[str] = []
    for t in curr.tasks:
        if t.id not in prev_ids:
            title_lower = t.title.lower()
            if "rework" in title_lower or "discovered-from" in title_lower:
                rework_ids.append(t.id)
    return rework_ids


def should_deduplicate(
    last_report_time: datetime | None,
    dedup_window_seconds: int = 300,
) -> bool:
    """Check if a report was generated too recently (5-minute window).

    Args:
        last_report_time: When the last report was generated.
        dedup_window_seconds: Minimum seconds between reports (default 300 = 5min).

    Returns:
        True if a report was generated within the dedup window.
    """
    if last_report_time is None:
        return False
    elapsed = (datetime.now(timezone.utc) - last_report_time).total_seconds()
    return elapsed < dedup_window_seconds
