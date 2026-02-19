# @trace SPEC-07
"""Diff-based re-decomposition when specs change.

Implements the 4-step diff algorithm [DIFF-1..4]:
1. Snapshot existing state (Beads or Markdown)
2. Re-decompose updated spec (produces target graph)
3. Classify changes: UNCHANGED / MODIFIED / NEW / REMOVED / DEPENDENCY_CHANGED
4. Generate incremental update plan + script
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ChangeCategory(str, Enum):
    """Classification for each work item in a diff."""

    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    NEW = "new"
    REMOVED = "removed"
    DEPENDENCY_CHANGED = "dependency_changed"


@dataclass
class WorkItemSnapshot:
    """Snapshot of an existing work item (task or hole)."""

    id: str  # Beads ID or task number
    title: str
    status: str  # open, in_progress, closed
    spec_traces: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    is_hole: bool = False
    hole_type: str = ""


@dataclass
class DiffItem:
    """A single item in the diff result."""

    category: ChangeCategory
    existing: WorkItemSnapshot | None = None  # None for NEW
    target: dict[str, Any] | None = None  # None for REMOVED
    change_summary: str = ""
    needs_human_review: bool = False
    rework_description: str = ""


@dataclass
class DiffResult:
    """Complete result of diffing existing state vs target decomposition."""

    items: list[DiffItem] = field(default_factory=list)
    hole_changes: list[DiffItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def unchanged(self) -> list[DiffItem]:
        return [i for i in self.items if i.category == ChangeCategory.UNCHANGED]

    @property
    def modified(self) -> list[DiffItem]:
        return [i for i in self.items if i.category == ChangeCategory.MODIFIED]

    @property
    def new(self) -> list[DiffItem]:
        return [i for i in self.items if i.category == ChangeCategory.NEW]

    @property
    def removed(self) -> list[DiffItem]:
        return [i for i in self.items if i.category == ChangeCategory.REMOVED]

    @property
    def dependency_changed(self) -> list[DiffItem]:
        return [
            i
            for i in self.items
            if i.category == ChangeCategory.DEPENDENCY_CHANGED
        ]

    @property
    def needs_review(self) -> list[DiffItem]:
        return [i for i in self.items + self.hole_changes if i.needs_human_review]

    @property
    def has_rework(self) -> bool:
        return any(i.rework_description for i in self.items)


# --- Step 1: Snapshot ---


def snapshot_from_beads_json(
    issues: list[dict[str, Any]],
) -> list[WorkItemSnapshot]:
    """Build snapshots from bd list --json output.

    Args:
        issues: List of Beads issue dicts.

    Returns:
        List of WorkItemSnapshot.
    """
    snapshots: list[WorkItemSnapshot] = []
    for issue in issues:
        is_hole = any(
            label.startswith("hole")
            for label in issue.get("labels", [])
        )
        hole_type = ""
        if is_hole:
            for label in issue.get("labels", []):
                if label.startswith("hole:") and label != "hole:agent-resolvable" and label != "hole:human-required":
                    hole_type = label.split(":", 1)[1]
                    break

        # Extract spec traces from description
        description = issue.get("description", "")
        traces = _extract_traces_from_text(description)

        # Extract produces from description (if orchestration metadata present)
        produces = _extract_produces_from_text(description)

        snapshots.append(
            WorkItemSnapshot(
                id=issue.get("id", ""),
                title=issue.get("title", ""),
                status=issue.get("status", "open"),
                spec_traces=traces,
                depends_on=[d.get("id", "") for d in issue.get("depends_on", [])],
                produces=produces,
                description=description,
                is_hole=is_hole,
                hole_type=hole_type,
            )
        )
    return snapshots


def snapshot_from_state_yaml(state_path: Path) -> list[WorkItemSnapshot]:
    """Build snapshots from a state.yaml file.

    Args:
        state_path: Path to state.yaml.

    Returns:
        List of WorkItemSnapshot.
    """
    content = state_path.read_text()
    state = yaml.safe_load(content)
    if not state:
        return []

    snapshots: list[WorkItemSnapshot] = []

    for task in state.get("tasks", []):
        snapshots.append(
            WorkItemSnapshot(
                id=str(task.get("number", "")),
                title=task.get("title", ""),
                status=task.get("status", "open"),
                spec_traces=task.get("traces", []),
                depends_on=[str(d) for d in task.get("depends_on", [])],
                is_hole=False,
            )
        )

    for hole in state.get("holes", []):
        snapshots.append(
            WorkItemSnapshot(
                id=str(hole.get("number", "")),
                title=hole.get("title", ""),
                status=hole.get("status", "open"),
                spec_traces=hole.get("traces", []),
                is_hole=True,
                hole_type=hole.get("type", ""),
            )
        )

    return snapshots


def _extract_traces_from_text(text: str) -> list[str]:
    """Extract SPEC-XX.YY style IDs from text."""
    import re

    pattern = r"SPEC-\d+\.\d+"
    return sorted(set(re.findall(pattern, text)))


def _extract_produces_from_text(text: str) -> list[str]:
    """Extract file paths from ORCHESTRATION METADATA produces field."""
    import re

    match = re.search(r"produces:\s*\[([^\]]*)\]", text)
    if not match:
        return []
    raw = match.group(1)
    return [p.strip().strip('"').strip("'") for p in raw.split(",") if p.strip()]


# --- Step 3: Match & Classify ---


def _match_score(
    existing: WorkItemSnapshot, target: dict[str, Any]
) -> float:
    """Compute a match score between an existing item and a target item.

    Uses three signals in priority order:
    1. Spec trace IDs (strongest)
    2. Title similarity
    3. File overlap (produces)

    Returns:
        Score from 0.0 (no match) to 1.0 (perfect match).
    """
    score = 0.0

    # Signal 1: Spec trace overlap (strongest signal)
    existing_traces = set(existing.spec_traces)
    target_traces = set(target.get("spec_traces", []))
    if existing_traces and target_traces:
        overlap = existing_traces & target_traces
        union = existing_traces | target_traces
        trace_score = len(overlap) / len(union) if union else 0.0
        score += trace_score * 0.6  # 60% weight

    # Signal 2: Title similarity (simple word overlap)
    existing_words = set(existing.title.lower().split())
    target_words = set(target.get("title", "").lower().split())
    if existing_words and target_words:
        word_overlap = existing_words & target_words
        word_union = existing_words | target_words
        title_score = len(word_overlap) / len(word_union) if word_union else 0.0
        score += title_score * 0.3  # 30% weight

    # Signal 3: File overlap (produces)
    existing_files = set(existing.produces)
    target_files = set(target.get("produces", []))
    if existing_files and target_files:
        file_overlap = existing_files & target_files
        file_union = existing_files | target_files
        file_score = len(file_overlap) / len(file_union) if file_union else 0.0
        score += file_score * 0.1  # 10% weight

    return score


def _has_scope_changed(
    existing: WorkItemSnapshot, target: dict[str, Any]
) -> tuple[bool, str]:
    """Determine if a matched item's scope has materially changed.

    Returns:
        (changed: bool, summary: str)
    """
    changes: list[str] = []

    # Check description change (detect if either side has content and they differ)
    target_desc = target.get("description", "")
    if target_desc != existing.description:
        # Only flag as changed if at least one side has meaningful content
        if target_desc or existing.description:
            changes.append("description updated")

    # Check acceptance criteria change
    target_criteria = target.get("acceptance_criteria", [])
    if target_criteria and existing.acceptance_criteria:
        if set(target_criteria) != set(existing.acceptance_criteria):
            changes.append("acceptance criteria changed")

    # Check spec traces change (new traces added or removed)
    target_traces = set(target.get("spec_traces", []))
    existing_traces = set(existing.spec_traces)
    if target_traces != existing_traces:
        added = target_traces - existing_traces
        removed = existing_traces - target_traces
        if added:
            changes.append(f"new spec refs: {', '.join(sorted(added))}")
        if removed:
            changes.append(f"removed spec refs: {', '.join(sorted(removed))}")

    if not changes:
        return False, ""
    return True, "; ".join(changes)


def _deps_changed(
    existing: WorkItemSnapshot, target: dict[str, Any]
) -> bool:
    """Check if dependency structure changed between existing and target."""
    target_task_deps = set(str(d) for d in target.get("depends_on_tasks", []))
    target_hole_deps = set(str(d) for d in target.get("depends_on_holes", []))
    target_deps = target_task_deps | target_hole_deps
    existing_deps = set(existing.depends_on)
    return target_deps != existing_deps


def compute_diff(
    existing: list[WorkItemSnapshot],
    target_data: dict[str, Any],
    match_threshold: float = 0.3,
) -> DiffResult:
    """Compute diff between existing state and target decomposition.

    Args:
        existing: Current work item snapshots.
        target_data: New decomposition output (full JSON).
        match_threshold: Minimum score to consider a match (0.0-1.0).

    Returns:
        DiffResult with classified items.
    """
    result = DiffResult()

    # Separate existing tasks and holes
    existing_tasks = [s for s in existing if not s.is_hole]
    existing_holes = [s for s in existing if s.is_hole]

    target_tasks = target_data.get("tasks", [])
    target_holes = target_data.get("holes", [])

    # --- Match tasks ---
    matched_existing: set[str] = set()
    matched_target: set[int] = set()

    # Build match matrix
    matches: list[tuple[float, WorkItemSnapshot, dict[str, Any]]] = []
    for ex in existing_tasks:
        for tgt in target_tasks:
            score = _match_score(ex, tgt)
            if score >= match_threshold:
                matches.append((score, ex, tgt))

    # Greedy matching by highest score
    matches.sort(key=lambda x: x[0], reverse=True)
    for score, ex, tgt in matches:
        if ex.id in matched_existing or tgt["number"] in matched_target:
            continue
        matched_existing.add(ex.id)
        matched_target.add(tgt["number"])

        # Classify the match
        scope_changed, change_summary = _has_scope_changed(ex, tgt)
        deps_differ = _deps_changed(ex, tgt)

        if not scope_changed and not deps_differ:
            result.items.append(
                DiffItem(
                    category=ChangeCategory.UNCHANGED,
                    existing=ex,
                    target=tgt,
                )
            )
        elif scope_changed:
            needs_review = ex.status in ("in_progress", "closed")
            rework = ""
            if ex.status == "closed":
                rework = (
                    f"Rework needed for completed task '{ex.title}': "
                    f"{change_summary}"
                )
            result.items.append(
                DiffItem(
                    category=ChangeCategory.MODIFIED,
                    existing=ex,
                    target=tgt,
                    change_summary=change_summary,
                    needs_human_review=needs_review,
                    rework_description=rework,
                )
            )
        else:
            # Only deps changed
            needs_review = ex.status == "closed"
            result.items.append(
                DiffItem(
                    category=ChangeCategory.DEPENDENCY_CHANGED,
                    existing=ex,
                    target=tgt,
                    change_summary="dependency structure changed",
                    needs_human_review=needs_review,
                )
            )

    # Unmatched existing tasks -> REMOVED
    for ex in existing_tasks:
        if ex.id not in matched_existing:
            needs_review = ex.status == "in_progress"
            result.items.append(
                DiffItem(
                    category=ChangeCategory.REMOVED,
                    existing=ex,
                    change_summary="requirement no longer in spec",
                    needs_human_review=needs_review,
                )
            )

    # Unmatched target tasks -> NEW
    for tgt in target_tasks:
        if tgt["number"] not in matched_target:
            result.items.append(
                DiffItem(
                    category=ChangeCategory.NEW,
                    target=tgt,
                )
            )

    # --- Match holes ---
    _diff_holes(existing_holes, target_holes, result, match_threshold)

    return result


def _diff_holes(
    existing_holes: list[WorkItemSnapshot],
    target_holes: list[dict[str, Any]],
    result: DiffResult,
    match_threshold: float,
) -> None:
    """Diff holes and update result.hole_changes."""
    matched_existing: set[str] = set()
    matched_target: set[str] = set()

    # Match holes by title similarity and type
    matches: list[tuple[float, WorkItemSnapshot, dict[str, Any]]] = []
    for ex in existing_holes:
        for tgt in target_holes:
            score = _hole_match_score(ex, tgt)
            if score >= match_threshold:
                matches.append((score, ex, tgt))

    matches.sort(key=lambda x: x[0], reverse=True)
    for score, ex, tgt in matches:
        if ex.id in matched_existing or tgt["number"] in matched_target:
            continue
        matched_existing.add(ex.id)
        matched_target.add(tgt["number"])

        # Hole was open, spec now answers it → check if still needed
        # Hole was open, spec still ambiguous → keep
        if ex.status in ("open", "in_progress"):
            result.hole_changes.append(
                DiffItem(
                    category=ChangeCategory.UNCHANGED,
                    existing=ex,
                    target=tgt,
                    change_summary="hole still present in updated spec",
                )
            )
        elif ex.status == "closed":
            # Hole was resolved — check if spec contradicts resolution
            result.hole_changes.append(
                DiffItem(
                    category=ChangeCategory.MODIFIED,
                    existing=ex,
                    target=tgt,
                    change_summary="resolved hole reappears in updated spec — may contradict resolution",
                    needs_human_review=True,
                )
            )

    # Existing holes no longer in target → auto-resolve (spec answered them)
    for ex in existing_holes:
        if ex.id not in matched_existing:
            if ex.status in ("open", "in_progress"):
                result.hole_changes.append(
                    DiffItem(
                        category=ChangeCategory.REMOVED,
                        existing=ex,
                        change_summary="spec now answers this question — auto-resolve",
                    )
                )
            else:
                # Already closed, nothing to do
                result.hole_changes.append(
                    DiffItem(
                        category=ChangeCategory.UNCHANGED,
                        existing=ex,
                        change_summary="already resolved, no longer in spec",
                    )
                )

    # New holes from target
    for tgt in target_holes:
        if tgt["number"] not in matched_target:
            result.hole_changes.append(
                DiffItem(
                    category=ChangeCategory.NEW,
                    target=tgt,
                    change_summary="new ambiguity in updated spec",
                )
            )


def _hole_match_score(
    existing: WorkItemSnapshot, target: dict[str, Any]
) -> float:
    """Match score for holes — uses title and type similarity."""
    score = 0.0

    # Title similarity
    existing_words = set(existing.title.lower().split())
    target_words = set(target.get("title", "").lower().split())
    if existing_words and target_words:
        overlap = existing_words & target_words
        union = existing_words | target_words
        score += (len(overlap) / len(union)) * 0.7

    # Type match
    if existing.hole_type == target.get("hole_type", ""):
        score += 0.3

    return score


# --- Step 4: Generate Diff Output ---


def generate_diff_markdown(diff: DiffResult, spec_source: str = "") -> str:
    """Generate human-readable diff plan.

    Args:
        diff: Computed DiffResult.
        spec_source: Description of spec source.

    Returns:
        Markdown string for decompose-diff.md.
    """
    lines: list[str] = []
    lines.append("# Decomposition Diff")
    lines.append("")

    if spec_source:
        lines.append(f"**Spec:** {spec_source}")

    n_new = len(diff.new)
    n_removed = len(diff.removed)
    n_modified = len(diff.modified)
    n_dep_changed = len(diff.dependency_changed)
    n_unchanged = len(diff.unchanged)

    lines.append(
        f"**Changes:** {n_new} new, {n_removed} removed, "
        f"{n_modified} modified, {n_dep_changed} dependency changed, "
        f"{n_unchanged} unchanged"
    )
    lines.append("")

    # Unchanged
    if diff.unchanged:
        lines.append(f"## Unchanged ({len(diff.unchanged)} tasks)")
        lines.append("")
        lines.append("| Task | Status | Notes |")
        lines.append("|------|--------|-------|")
        for item in diff.unchanged:
            ex = item.existing
            assert ex is not None
            status_icon = {"open": "⬚", "in_progress": "🔄", "closed": "✅"}.get(
                ex.status, "?"
            )
            lines.append(
                f"| {ex.id}: {ex.title} | {status_icon} {ex.status} | No changes needed |"
            )
        lines.append("")

    # Modified
    if diff.modified:
        lines.append(f"## Modified ({len(diff.modified)} tasks)")
        lines.append("")
        lines.append("| Task | Status | Change | Action |")
        lines.append("|------|--------|--------|--------|")
        for item in diff.modified:
            ex = item.existing
            assert ex is not None
            status_icon = {"open": "⬚", "in_progress": "🔄", "closed": "✅"}.get(
                ex.status, "?"
            )
            action = "Update description"
            if ex.status == "closed":
                action = "⚠️ REWORK"
            elif ex.status == "in_progress":
                action = "⚠️ Review in-progress work"
            lines.append(
                f"| {ex.id}: {ex.title} | {status_icon} {ex.status} "
                f"| {item.change_summary} | {action} |"
            )
        lines.append("")

        # Rework details
        for item in diff.modified:
            if item.rework_description:
                ex = item.existing
                assert ex is not None
                lines.append(f"### Rework: {ex.id} ({ex.title})")
                lines.append("")
                lines.append(item.rework_description)
                lines.append(f"- Links to: discovered-from:{ex.id}")
                lines.append("")

    # New
    if diff.new:
        lines.append(f"## New ({len(diff.new)} tasks)")
        lines.append("")
        lines.append("| Task | Depends On | Est. Tokens | Priority |")
        lines.append("|------|-----------|-------------|----------|")
        for item in diff.new:
            tgt = item.target
            assert tgt is not None
            deps: list[str] = []
            for d in tgt.get("depends_on_tasks", []):
                deps.append(f"T{d}")
            for d in tgt.get("depends_on_holes", []):
                deps.append(str(d))
            dep_str = ", ".join(deps) if deps else "—"
            est = tgt.get("estimated_tokens", {}).get("total", 0)
            lines.append(
                f"| {tgt.get('title', '?')} | {dep_str} "
                f"| ~{est:,} | P{tgt.get('priority', 2)} |"
            )
        lines.append("")

    # Removed
    if diff.removed:
        lines.append(f"## Removed ({len(diff.removed)} tasks)")
        lines.append("")
        lines.append("| Task | Status | Action |")
        lines.append("|------|--------|--------|")
        for item in diff.removed:
            ex = item.existing
            assert ex is not None
            action = "Close as obsolete"
            if ex.status == "in_progress":
                action = "⚠️ Review — currently in progress"
            elif ex.status == "closed":
                action = "Leave as-is (code exists)"
            lines.append(f"| {ex.id}: {ex.title} | {ex.status} | {action} |")
        lines.append("")

    # Dependency changes
    if diff.dependency_changed:
        lines.append(f"## Dependency Changed ({len(diff.dependency_changed)} tasks)")
        lines.append("")
        lines.append("| Task | Status | Change |")
        lines.append("|------|--------|--------|")
        for item in diff.dependency_changed:
            ex = item.existing
            assert ex is not None
            lines.append(
                f"| {ex.id}: {ex.title} | {ex.status} | {item.change_summary} |"
            )
        lines.append("")

    # Hole changes
    new_holes = [h for h in diff.hole_changes if h.category == ChangeCategory.NEW]
    resolved_holes = [
        h
        for h in diff.hole_changes
        if h.category == ChangeCategory.REMOVED and h.existing
    ]
    modified_holes = [
        h for h in diff.hole_changes if h.category == ChangeCategory.MODIFIED
    ]

    if new_holes or resolved_holes or modified_holes:
        lines.append("## Hole Changes")
        lines.append("")
        if resolved_holes:
            lines.append("### Auto-Resolved (spec now answers)")
            for h in resolved_holes:
                ex = h.existing
                assert ex is not None
                lines.append(f"- {ex.id}: {ex.title}")
            lines.append("")
        if new_holes:
            lines.append("### New Holes")
            for h in new_holes:
                tgt = h.target
                assert tgt is not None
                lines.append(
                    f"- {tgt['number']}: {tgt['title']} ({tgt.get('hole_type', '?')})"
                )
            lines.append("")
        if modified_holes:
            lines.append("### ⚠️ Requires Review")
            for h in modified_holes:
                ex = h.existing
                assert ex is not None
                lines.append(f"- {ex.id}: {ex.title} — {h.change_summary}")
            lines.append("")

    # Human review section
    review_items = diff.needs_review
    if review_items:
        lines.append("## ⚠️ Requires Human Review")
        lines.append("")
        for item in review_items:
            if item.existing:
                lines.append(
                    f"- {item.existing.id}: {item.existing.title} — {item.change_summary}"
                )
            elif item.target:
                lines.append(
                    f"- {item.target.get('title', '?')} — {item.change_summary}"
                )
        lines.append("")

    return "\n".join(lines)


def generate_diff_script(
    diff: DiffResult,
    existing_tasks: list[WorkItemSnapshot] | None = None,
) -> str:
    """Generate incremental update script.

    Args:
        diff: Computed DiffResult.
        existing_tasks: Full list of existing snapshots (for ID lookups).

    Returns:
        Shell script string for decompose-diff.sh.
    """
    lines: list[str] = []
    lines.append("#!/usr/bin/env bash")
    lines.append("set -euo pipefail")
    lines.append(
        "# Generated by spec-decompose --diff. Review decompose-diff.md before running."
    )
    lines.append("")

    from tools.spec_decompose.output_beads import _escape_shell, _format_description_for_bd

    has_actions = False

    # Modified tasks: update description (open) or create rework (closed)
    for item in diff.modified:
        ex = item.existing
        tgt = item.target
        if not ex or not tgt:
            continue
        has_actions = True

        if ex.status == "open":
            desc = _escape_shell(_format_description_for_bd(tgt))
            lines.append(f"# Update modified task: {ex.title}")
            lines.append(
                f"bd update '{_escape_shell(ex.id)}' "
                f"-d '{desc}'"
            )
            lines.append("")
        elif ex.status == "closed":
            # Create rework task
            rework_desc = _escape_shell(
                f"Rework for completed task: {item.change_summary}\n\n"
                f"Original task: {ex.id}\n"
                + _format_description_for_bd(tgt)
            )
            lines.append(f"# Rework for completed task: {ex.title}")
            lines.append(
                f"REWORK_ID=$(bd create 'Rework: {_escape_shell(ex.title)}' "
                f"-t task -p {tgt.get('priority', 2)} "
                f"-d '{rework_desc}' "
                f"--json | jq -r '.id')"
            )
            lines.append(
                f'bd dep add "$REWORK_ID" \'{_escape_shell(ex.id)}\' '
                f'--type discovered-from'
            )
            lines.append("")
        elif ex.status == "in_progress":
            lines.append(f"# ⚠️ Task in progress — review manually: {ex.id} ({ex.title})")
            lines.append(f"# Change: {item.change_summary}")
            lines.append("")

    # New tasks
    for item in diff.new:
        tgt = item.target
        if not tgt:
            continue
        has_actions = True
        desc = _escape_shell(_format_description_for_bd(tgt))
        var_name = f"NEW_T{tgt['number']}"
        lines.append(f"# New task: {tgt['title']}")
        lines.append(
            f"{var_name}_ID=$(bd create '{_escape_shell(tgt['title'])}' "
            f"-t task -p {tgt.get('priority', 2)} "
            f"-d '{desc}' "
            f"--json | jq -r '.id')"
        )
        lines.append(f'echo "Created new task: ${var_name}_ID"')
        lines.append("")

    # Removed tasks (close open ones)
    for item in diff.removed:
        ex = item.existing
        if not ex:
            continue
        if ex.status == "open":
            has_actions = True
            lines.append(f"# Close obsolete task: {ex.title}")
            lines.append(
                f"bd close '{_escape_shell(ex.id)}' "
                f"--reason 'Obsolete: requirement removed from spec'"
            )
            lines.append("")
        elif ex.status == "in_progress":
            lines.append(f"# ⚠️ Task in progress but requirement removed — review: {ex.id}")
            lines.append("")

    # Dependency changes
    for item in diff.dependency_changed:
        ex = item.existing
        tgt = item.target
        if not ex or not tgt:
            continue
        has_actions = True
        lines.append(f"# Update dependencies for: {ex.title}")
        lines.append(f"# Manual review needed — dependency structure changed for {ex.id}")
        lines.append("")

    # Hole changes
    for item in diff.hole_changes:
        if item.category == ChangeCategory.REMOVED and item.existing:
            if item.existing.status in ("open", "in_progress"):
                has_actions = True
                lines.append(f"# Auto-resolve hole: {item.existing.title}")
                lines.append(
                    f"bd close '{_escape_shell(item.existing.id)}' "
                    f"--reason 'Auto-resolved: spec update answers this question'"
                )
                lines.append("")
        elif item.category == ChangeCategory.NEW and item.target:
            has_actions = True
            tgt = item.target
            labels = ["hole"]
            if tgt.get("hole_type"):
                labels.append(f"hole:{tgt['hole_type']}")
            label_str = ",".join(labels)
            lines.append(f"# New hole: {tgt['title']}")
            lines.append(
                f"bd create 'HOLE: {_escape_shell(tgt['title'])}' "
                f"-t task -p {tgt.get('priority', 1)} "
                f"-l '{label_str}' "
                f"--json > /dev/null"
            )
            lines.append("")

    if not has_actions:
        lines.append("echo 'No changes needed — decomposition is up to date.'")
        lines.append("")
    else:
        lines.append('echo "Diff applied. Run bd ready to see available work."')
        lines.append("")

    return "\n".join(lines)


def write_diff_output(
    diff: DiffResult,
    spec_source: str = "",
    output_dir: Path | None = None,
    existing_tasks: list[WorkItemSnapshot] | None = None,
) -> tuple[Path, Path]:
    """Write diff plan markdown and shell script.

    Args:
        diff: Computed DiffResult.
        spec_source: Spec source description.
        output_dir: Output directory (defaults to CWD).
        existing_tasks: For ID lookups in script generation.

    Returns:
        Tuple of (diff_md_path, diff_sh_path).
    """
    if output_dir is None:
        output_dir = Path(".")

    diff_md = output_dir / "decompose-diff.md"
    diff_sh = output_dir / "decompose-diff.sh"

    diff_md.write_text(generate_diff_markdown(diff, spec_source))
    diff_sh.write_text(generate_diff_script(diff, existing_tasks))

    return diff_md, diff_sh
