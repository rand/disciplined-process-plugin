# @trace SPEC-08
"""Progress report generation.

Produces structured Markdown + JSON reports from ProjectState.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.progress_report.extractor import ProjectState, TaskState


def generate_report_markdown(
    state: ProjectState,
    trigger_reason: str = "on_demand",
    report_number: int = 1,
    prev_state: ProjectState | None = None,
    last_report_time: datetime | None = None,
    epic_title: str = "Project",
) -> str:
    """Generate a full progress report in Markdown format.

    Args:
        state: Current project state.
        trigger_reason: Why this report was generated.
        report_number: Sequential report number.
        prev_state: Previous state for delta computation.
        last_report_time: When the previous report was generated.
        epic_title: Title for the report header.

    Returns:
        Markdown string.
    """
    now = datetime.now(timezone.utc)
    lines: list[str] = []

    # Header
    lines.append(f"# Progress Report: {epic_title}")
    lines.append("")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"**Trigger:** {trigger_reason}")
    lines.append(f"**Report #:** {report_number}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    pct = int(state.progress_ratio * 100)
    lines.append(
        f"{state.completed_tasks} of {state.total_tasks} tasks done ({pct}%)."
    )
    ready_count = len(state.ready_tasks)
    if ready_count > 0:
        lines.append(f"{ready_count} tasks ready for execution.")
    open_holes = state.open_holes
    if open_holes:
        lines.append(f"{len(open_holes)} open holes require attention.")
    lines.append("")

    # Since Last Report
    if prev_state is not None:
        lines.append("## Since Last Report")
        if last_report_time:
            elapsed = now - last_report_time
            minutes = int(elapsed.total_seconds() / 60)
            lines.append(f"({minutes} min ago)")
        lines.append("")

        # Completed tasks
        prev_closed_ids = {t.id for t in prev_state.tasks if t.status == "closed"}
        newly_completed = [
            t
            for t in state.tasks
            if t.status == "closed" and t.id not in prev_closed_ids and not t.is_hole
        ]
        if newly_completed:
            lines.append("### Completed")
            lines.append("")
            lines.append("| Task | Duration | Tokens |")
            lines.append("|------|----------|--------|")
            for t in newly_completed:
                duration = _format_duration(t, last_report_time)
                lines.append(
                    f"| {t.id}: {t.title} | {duration} | ~est |"
                )
            lines.append("")

        # New issues discovered
        prev_ids = {t.id for t in prev_state.tasks}
        new_tasks = [t for t in state.tasks if t.id not in prev_ids and not t.is_hole]
        if new_tasks:
            lines.append("### New Issues Discovered")
            lines.append("")
            lines.append("| Issue | Priority |")
            lines.append("|-------|----------|")
            for t in new_tasks:
                lines.append(f"| {t.id}: {t.title} | P{t.priority} |")
            lines.append("")

    # Key Decisions Made (Gap 7)
    decisions = [t for t in state.tasks if not t.is_hole
                 and "decision" in [l.lower() for l in t.labels]]
    if decisions:
        lines.append("## Key Decisions Made")
        lines.append("")
        for d in decisions:
            lines.append(f"- {d.id}: {d.title}")
        lines.append("")

    # Holes section
    if state.total_holes > 0:
        lines.append("## Holes")
        lines.append("")

        if open_holes:
            lines.append("### Open (blocking work)")
            lines.append("")
            lines.append("| Hole | Type | Urgency |")
            lines.append("|------|------|---------|")
            for h in open_holes:
                urgency = "HIGH" if h.priority <= 1 else "MEDIUM"
                lines.append(
                    f"| {h.id}: {h.title} | {h.hole_type} | {urgency} |"
                )
            lines.append("")

        resolved = state.resolved_holes
        if resolved:
            lines.append("### Resolved")
            lines.append("")
            for h in resolved:
                lines.append(f"- {h.id}: {h.title}")
            lines.append("")

        lines.append("### Hole Metrics")
        lines.append("")
        lines.append(
            f"- Total: {state.total_holes} | "
            f"Resolved: {len(resolved)} ({int(len(resolved) / state.total_holes * 100) if state.total_holes else 0}%) | "
            f"Open: {len(open_holes)}"
        )
        lines.append("")

    # Current State
    lines.append("## Current State")
    lines.append("")

    # Progress bar
    lines.append("### Progress")
    lines.append("")
    pct = int(state.progress_ratio * 100)
    filled = pct // 5  # 20 chars wide
    empty = 20 - filled
    bar = "\u2588" * filled + "\u2591" * empty
    lines.append(
        f"  {bar} {pct}% ({state.completed_tasks}/{state.total_tasks} tasks)"
    )
    lines.append("")

    # Ready work
    ready = state.ready_tasks
    if ready:
        lines.append("### Ready Work")
        lines.append("")
        lines.append("| Task | Priority |")
        lines.append("|------|----------|")
        for t in ready:
            lines.append(f"| {t.id}: {t.title} | P{t.priority} |")
        lines.append("")

    # Blocked
    blocked = state.blocked_tasks
    if blocked:
        lines.append("### Blocked")
        lines.append("")
        lines.append("| Task | Blocked By |")
        lines.append("|------|-----------|")
        for t in blocked:
            blockers = ", ".join(t.blocked_by)
            lines.append(f"| {t.id}: {t.title} | {blockers} |")
        lines.append("")

    # Warnings (Gap 7)
    warnings = _compute_warnings(state)
    if warnings:
        lines.append("### Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Risks (Gap 7)
    risks = _compute_risks(state)
    if risks:
        lines.append("### Risks")
        lines.append("")
        for r in risks:
            lines.append(f"- {r}")
        lines.append("")

    # Files changed
    if state.git.files_changed:
        lines.append("## Files Changed")
        lines.append("")
        for f in state.git.files_changed[:20]:
            lines.append(f"  {f}")
        if len(state.git.files_changed) > 20:
            lines.append(f"  ... and {len(state.git.files_changed) - 20} more")
        lines.append("")

    # Agent instructions
    lines.append("## For Agents: Context Loading Instructions")
    lines.append("")
    lines.append("If you're starting a new session:")
    lines.append("1. Read this file for high-level context.")
    lines.append("2. Run `bd ready --json` for your next task.")
    lines.append("3. Run `bd show <task-id>` for full task details.")
    lines.append(
        "4. Do NOT read the full spec or git log "
        "-- task descriptions are self-contained."
    )
    lines.append("")

    # Human action items
    action_items = _compute_action_items(state)
    if action_items:
        lines.append("## For Humans: Action Items")
        lines.append("")
        for item in action_items:
            lines.append(f"- [ ] {item}")
        lines.append("")

    return "\n".join(lines)


def generate_report_json(
    state: ProjectState,
    trigger_reason: str = "on_demand",
    prev_state: ProjectState | None = None,
    report_number: int = 1,
    epic_title: str = "Project",
) -> dict[str, Any]:
    """Generate machine-readable progress report.

    Args:
        state: Current project state.
        trigger_reason: Why this report was generated.
        prev_state: For computing deltas.
        report_number: Sequential report number.
        epic_title: Title for the epic.

    Returns:
        Dict matching the Progress Report JSON schema.
    """
    now = datetime.now(timezone.utc)

    # Compute newly completed
    recently_completed: list[str] = []
    if prev_state:
        prev_closed = {t.id for t in prev_state.tasks if t.status == "closed"}
        recently_completed = [
            t.id for t in state.tasks if t.status == "closed" and t.id not in prev_closed
        ]

    # Discovered issues
    discovered: list[str] = []
    if prev_state:
        prev_ids = {t.id for t in prev_state.tasks}
        discovered = [t.id for t in state.tasks if t.id not in prev_ids]

    # Compute tasks blocked by holes
    hole_ids = {t.id for t in state.tasks if t.is_hole and t.status != "closed"}
    tasks_blocked_by_holes = len([
        t for t in state.tasks
        if not t.is_hole and any(b in hole_ids for b in t.blocked_by)
    ])

    # Risks: tasks on critical path blocked by incomplete work
    risks: list[str] = []
    for t in state.blocked_tasks:
        if t.priority <= 1:
            risks.append(f"high_priority_blocked:{t.id}")

    return {
        "timestamp": now.isoformat(),
        "report_number": report_number,
        "epic_title": epic_title,
        "trigger": trigger_reason,
        "epic_progress": round(state.progress_ratio, 2),
        "tasks": {
            "total": state.total_tasks,
            "completed": state.completed_tasks,
            "in_progress": state.in_progress_tasks,
            "blocked": len(state.blocked_tasks),
            "ready": len(state.ready_tasks),
            "not_started": state.open_tasks,
        },
        "holes": {
            "total": state.total_holes,
            "resolved": len(state.resolved_holes),
            "open_blocking": len(state.open_holes),
            "tasks_blocked_by_holes": tasks_blocked_by_holes,
        },
        "ready_task_ids": [t.id for t in state.ready_tasks],
        "ready_work": [
            {"id": t.id, "title": t.title, "priority": t.priority}
            for t in state.ready_tasks
        ],
        "recently_completed": recently_completed,
        "discovered_issues": discovered,
        "open_holes": [
            {
                "id": h.id,
                "type": h.hole_type,
                "blocks": h.blocked_by,
                "urgency": "high" if h.priority <= 1 else "medium",
            }
            for h in state.open_holes
        ],
        "risks": risks,
        "files_changed": state.git.files_changed[:20],
    }


def write_report(
    state: ProjectState,
    trigger_reason: str = "on_demand",
    report_number: int = 1,
    prev_state: ProjectState | None = None,
    last_report_time: datetime | None = None,
    epic_title: str = "Project",
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Write progress report files.

    Generates a timestamped markdown report and a latest.json.

    Args:
        state: Current project state.
        trigger_reason: Why this report was generated.
        report_number: Sequential report number.
        prev_state: For delta computation.
        last_report_time: When previous report was generated.
        epic_title: Title for report header.
        output_dir: Output directory. Defaults to docs/progress/.

    Returns:
        Tuple of (markdown_path, json_path).
    """
    if output_dir is None:
        output_dir = Path("docs/progress")

    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    slug = trigger_reason.lower().replace(" ", "-")[:30]
    timestamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{timestamp}-{slug}"

    # Write markdown
    md_content = generate_report_markdown(
        state, trigger_reason, report_number, prev_state,
        last_report_time, epic_title,
    )
    md_path = output_dir / f"{filename}.md"
    md_path.write_text(md_content)

    # Update latest.md symlink
    latest_md = output_dir / "latest.md"
    if latest_md.is_symlink() or latest_md.exists():
        latest_md.unlink()
    try:
        latest_md.symlink_to(md_path.name)
    except OSError:
        # Fallback: copy the file if symlinks aren't supported
        latest_md.write_text(md_content)

    # Write JSON
    json_data = generate_report_json(
        state, trigger_reason, prev_state,
        report_number=report_number, epic_title=epic_title,
    )
    json_path = output_dir / "latest.json"
    json_path.write_text(json.dumps(json_data, indent=2))

    return md_path, json_path


def _compute_warnings(state: ProjectState) -> list[str]:
    """Compute warning items from current state."""
    warnings: list[str] = []
    # Tasks stuck in_progress with no recent commits
    in_progress = [t for t in state.tasks if t.status == "in_progress" and not t.is_hole]
    if len(in_progress) > 3:
        warnings.append(
            f"{len(in_progress)} tasks in progress simultaneously — consider focusing"
        )
    return warnings


def _compute_risks(state: ProjectState) -> list[str]:
    """Compute risk items from current state."""
    risks: list[str] = []
    # High-priority blocked tasks are risks
    for t in state.blocked_tasks:
        if t.priority <= 1:
            risks.append(f"High-priority task {t.id} ({t.title}) is blocked")
    # All work blocked by holes
    if state.all_work_hole_blocked:
        risks.append("All remaining work blocked by holes — human intervention required")
    return risks


def _format_duration(
    task: TaskState, reference_time: datetime | None = None
) -> str:
    """Format duration for a completed task."""
    if task.closed_at:
        try:
            closed = datetime.fromisoformat(task.closed_at)
            if reference_time:
                delta = closed - reference_time
                minutes = int(delta.total_seconds() / 60)
                if minutes < 60:
                    return f"{minutes}m"
                return f"{minutes // 60}h {minutes % 60}m"
        except (ValueError, TypeError):
            pass
    return "—"


def _compute_action_items(state: ProjectState) -> list[str]:
    """Compute human action items from current state."""
    items: list[str] = []

    # Open holes needing human attention
    for h in state.open_holes:
        if h.hole_type in ("clarification", "escalation"):
            items.append(f"Resolve {h.id} ({h.title}) -- needs human decision")

    # Ready work
    ready_count = len(state.ready_tasks)
    if ready_count > 0:
        items.append(
            f"{ready_count} tasks ready for execution -- spin up agents?"
        )

    # All work blocked
    if state.all_work_hole_blocked:
        items.append(
            "ALL remaining work is blocked by holes -- urgent human attention needed"
        )

    return items
