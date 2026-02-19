# @trace SPEC-07
"""Beads output generation from decomposition results.

Generates:
- decompose-plan.md: Human-readable plan with graph, holes, coverage
- decompose-plan.sh: Executable bd commands to create work items
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _escape_shell(s: str) -> str:
    """Escape a string for safe inclusion in a shell script."""
    return s.replace("'", "'\\''")


def _format_description_for_bd(task: dict[str, Any]) -> str:
    """Format a task description for bd create --description flag."""
    parts = [task.get("description", "")]

    # Add spec traces
    traces = task.get("spec_traces", [])
    if traces:
        parts.append(f"\nSpec traces: {', '.join(traces)}")

    # Add acceptance criteria
    criteria = task.get("acceptance_criteria", [])
    if criteria:
        parts.append("\nAcceptance criteria:")
        for c in criteria:
            parts.append(f"- {c}")

    # Add context files
    ctx = task.get("context_files", [])
    if ctx:
        parts.append("\nContext files to read:")
        for cf in ctx:
            parts.append(f"- {cf['path']} ({cf.get('reason', '')})")

    # Add orchestration metadata as HTML comment
    orch = task.get("orchestration", {})
    if orch:
        parts.append(f"\n<!-- ORCHESTRATION METADATA")
        for k, v in orch.items():
            parts.append(f"{k}: {v}")
        parts.append("-->")

    return "\n".join(parts)


def generate_plan_markdown(data: dict[str, Any]) -> str:
    """Generate human-readable decomposition plan.

    Args:
        data: Validated decomposition output dict.

    Returns:
        Markdown string for decompose-plan.md.
    """
    epic = data.get("epic", {})
    tasks = data.get("tasks", [])
    holes = data.get("holes", [])
    coverage = data.get("coverage", {})
    groups = data.get("parallel_groups", [])

    lines: list[str] = []
    lines.append(f"# Decomposition Plan: {epic.get('title', 'Untitled')}")
    lines.append("")

    # Summary
    spec_source = data.get("spec_source", [])
    lines.append(f"**Spec:** {', '.join(spec_source)}")
    lines.append(
        f"**Work items:** {len(tasks)} tasks + {len(holes)} holes"
    )

    total_tokens = sum(
        t.get("estimated_tokens", {}).get("total", 0) for t in tasks
    )
    if total_tokens:
        lines.append(f"**Estimated agent effort:** ~{total_tokens:,} tokens")
    lines.append("")

    # Holes section
    if holes:
        lines.append("## Holes (resolve before or during implementation)")
        lines.append("")
        lines.append("| # | Hole | Type | Blocks | Resolution |")
        lines.append("|---|------|------|--------|------------|")
        for h in holes:
            blocks = ", ".join(f"T{t}" for t in h.get("blocks_tasks", []))
            lines.append(
                f"| {h['number']} | {h['title']} | {h['hole_type']} "
                f"| {blocks} | {h.get('resolution_method', '?')} |"
            )
        lines.append("")

    # Tasks table
    lines.append("## Tasks")
    lines.append("")
    lines.append("| # | Task | Depends On | Est. Tokens | Priority |")
    lines.append("|---|------|-----------|-------------|----------|")
    for t in tasks:
        deps: list[str] = []
        for d in t.get("depends_on_tasks", []):
            deps.append(f"T{d}")
        for d in t.get("depends_on_holes", []):
            deps.append(str(d))
        dep_str = ", ".join(deps) if deps else "\u2014"
        est = t.get("estimated_tokens", {}).get("total", 0)
        lines.append(
            f"| {t['number']} | {t['title']} | {dep_str} "
            f"| ~{est:,} | P{t.get('priority', 2)} |"
        )
    lines.append("")

    # Parallel groups
    if groups:
        lines.append("## Parallel Groups")
        lines.append("")
        for g in groups:
            task_list = ", ".join(f"T{t}" for t in g.get("tasks", []))
            lines.append(f"- **{g['name']}**: {task_list}")
            if g.get("rationale"):
                lines.append(f"  {g['rationale']}")
        lines.append("")

    # Critical path analysis
    from tools.spec_decompose.graph import compute_critical_path
    crit_path = compute_critical_path(tasks, holes)
    if crit_path:
        lines.append("## Critical Path Analysis")
        lines.append("")
        lines.append("The longest dependency chain (bottleneck):")
        lines.append("")
        lines.append("| Step | Task | Cumulative Tokens |")
        lines.append("|------|------|-------------------|")
        for i, entry in enumerate(crit_path, 1):
            # Find title
            title = str(entry.task_id)
            for t in tasks:
                if t["number"] == entry.task_id:
                    title = t["title"]
                    break
            for h in holes:
                if h["number"] == entry.task_id:
                    title = f"HOLE: {h['title']}"
                    break
            lines.append(
                f"| {i} | {entry.task_id}: {title} "
                f"| ~{entry.cumulative_tokens:,} |"
            )
        lines.append("")

    # Coverage
    if coverage:
        total = coverage.get("requirements_total", 0)
        covered = coverage.get("requirements_covered", 0)
        uncov = coverage.get("uncovered", [])
        lines.append("## Coverage")
        lines.append("")
        lines.append(f"Requirements: {covered}/{total} covered")
        if uncov:
            lines.append(f"Uncovered: {', '.join(uncov)}")
        lines.append("")

    return "\n".join(lines)


def generate_plan_script(
    data: dict[str, Any], epic_title: str | None = None
) -> str:
    """Generate executable shell script for creating Beads work items.

    Args:
        data: Validated decomposition output dict.
        epic_title: Override for the epic title.

    Returns:
        Shell script string for decompose-plan.sh.
    """
    epic = data.get("epic", {})
    title = epic_title or epic.get("title", "Decomposed Spec")
    issues = data.get("issues", [])
    tasks = data.get("tasks", [])
    holes = data.get("holes", [])

    lines: list[str] = []
    lines.append("#!/usr/bin/env bash")
    lines.append("set -euo pipefail")
    lines.append(
        "# Generated by spec-decompose. Review decompose-plan.md before running."
    )
    lines.append("")

    # Create epic
    lines.append("# Create epic")
    lines.append(
        f"EPIC_ID=$(bd create '{_escape_shell(title)}' "
        f"-t epic -p 1 --json | jq -r '.id')"
    )
    lines.append('echo "Created epic: $EPIC_ID"')
    lines.append("")

    # Create holes first (they may be needed as dependencies)
    if holes:
        lines.append("# Create holes")
        for h in holes:
            labels = ["hole", f"hole:{h['hole_type']}"]
            label_str = ",".join(labels)
            desc = _escape_shell(
                f"Type: {h['hole_type']}\n"
                f"Known: {h.get('known', {})}\n"
                f"Unknown: {h.get('unknown', [])}\n"
                f"Resolution: {h.get('resolution_method', '?')}"
            )
            var_name = h["number"].replace("-", "_").upper()
            lines.append(
                f"{var_name}_ID=$(bd create 'HOLE: {_escape_shell(h['title'])}' "
                f"-t task -p {h.get('priority', 1)} "
                f"-l '{label_str}' "
                f"-d '{desc}' "
                f"--json | jq -r '.id')"
            )
            lines.append(f'echo "Created hole {h["number"]}: ${var_name}_ID"')
        lines.append("")

    # Create tasks
    lines.append("# Create tasks")
    for t in tasks:
        desc = _escape_shell(_format_description_for_bd(t))
        var_name = f"T{t['number']}"
        lines.append(
            f"{var_name}_ID=$(bd create '{_escape_shell(t['title'])}' "
            f"-t task -p {t.get('priority', 2)} "
            f"-d '{desc}' "
            f"--json | jq -r '.id')"
        )
        lines.append(f'echo "Created task {t["number"]}: ${var_name}_ID"')
    lines.append("")

    # Wire dependencies
    has_deps = False
    for t in tasks:
        for dep in t.get("depends_on_tasks", []):
            if not has_deps:
                lines.append("# Wire task dependencies")
                has_deps = True
            lines.append(f'bd dep add "$T{t["number"]}_ID" "$T{dep}_ID"')

        for dep in t.get("depends_on_holes", []):
            if not has_deps:
                lines.append("# Wire task dependencies")
                has_deps = True
            var = dep.replace("-", "_").upper()
            lines.append(f'bd dep add "$T{t["number"]}_ID" "${var}_ID"')

    if has_deps:
        lines.append("")

    # Wire parent-child for issues
    if issues:
        lines.append("# Wire parent-child (epic -> tasks)")
        for t in tasks:
            lines.append(
                f'bd dep add "$T{t["number"]}_ID" "$EPIC_ID" '
                f'--type parent-child 2>/dev/null || true'
            )
        lines.append("")

    lines.append('echo "Decomposition complete. Run bd ready to see available work."')
    lines.append("")

    return "\n".join(lines)


def write_beads_output(
    data: dict[str, Any],
    output_dir: Path | None = None,
    epic_title: str | None = None,
) -> tuple[Path, Path]:
    """Write both plan markdown and shell script.

    Args:
        data: Validated decomposition output dict.
        output_dir: Directory for output files. Defaults to CWD.
        epic_title: Override for the epic title.

    Returns:
        Tuple of (plan_md_path, plan_sh_path).
    """
    if output_dir is None:
        output_dir = Path(".")

    plan_md = output_dir / "decompose-plan.md"
    plan_sh = output_dir / "decompose-plan.sh"

    plan_md.write_text(generate_plan_markdown(data))
    plan_sh.write_text(generate_plan_script(data, epic_title))

    return plan_md, plan_sh
