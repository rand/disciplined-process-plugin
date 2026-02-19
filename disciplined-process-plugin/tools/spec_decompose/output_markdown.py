# @trace SPEC-07
"""Markdown output generation from decomposition results.

Generates a docs/tasks/ directory with:
- README.md: Plan overview + dependency graph
- tasks/NNN-title.md: Individual task files
- holes/HXXX-title.md: Individual hole files
- state.yaml: Machine-readable state for diffing
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _slugify(title: str) -> str:
    """Convert a title to a filesystem-safe slug."""
    slug = title.lower()
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    slug = slug.strip().replace(" ", "-")
    # Collapse multiple dashes
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:60]


def generate_task_markdown(task: dict[str, Any]) -> str:
    """Generate markdown for a single task file."""
    lines: list[str] = []
    num = task["number"]
    lines.append(f"# T{num:03d}: {task['title']}")
    lines.append("")
    lines.append(f"**Status:** open")
    lines.append(f"**Priority:** P{task.get('priority', 2)}")

    # Dependencies
    deps: list[str] = []
    for d in task.get("depends_on_tasks", []):
        deps.append(f"T{d:03d}")
    for d in task.get("depends_on_holes", []):
        deps.append(str(d))
    dep_str = ", ".join(deps) if deps else "(none)"
    lines.append(f"**Depends on:** {dep_str}")

    # Blocks
    blocks = task.get("orchestration", {}).get("blocks", [])
    if blocks:
        lines.append(f"**Blocks:** {', '.join(f'T{b:03d}' for b in blocks)}")

    # Spec traces
    traces = task.get("spec_traces", [])
    if traces:
        lines.append(f"**Spec traces:** {', '.join(traces)}")

    lines.append("")
    lines.append("## Description")
    lines.append("")
    lines.append(task.get("description", "No description provided."))
    lines.append("")

    # Context files
    ctx = task.get("context_files", [])
    if ctx:
        lines.append("## Context Files to Read")
        lines.append("")
        lines.append("| File | Reason | Est. Tokens |")
        lines.append("|------|--------|-------------|")
        for cf in ctx:
            lines.append(
                f"| {cf['path']} | {cf.get('reason', '')} "
                f"| ~{cf.get('estimated_tokens', '?')} |"
            )
        lines.append("")

    # Acceptance criteria
    criteria = task.get("acceptance_criteria", [])
    if criteria:
        lines.append("## Acceptance Criteria")
        lines.append("")
        for c in criteria:
            lines.append(f"- [ ] {c}")
        lines.append("")

    # Orchestration metadata
    orch = task.get("orchestration", {})
    if orch:
        lines.append("## Orchestration")
        lines.append("")
        lines.append("<!-- ORCHESTRATION METADATA")
        for k, v in orch.items():
            lines.append(f"{k}: {v}")
        lines.append("-->")
        lines.append("")

    lines.append("## Completion Notes")
    lines.append("")
    lines.append("_Not yet completed._")
    lines.append("")

    return "\n".join(lines)


def generate_hole_markdown(hole: dict[str, Any]) -> str:
    """Generate markdown for a single hole file."""
    lines: list[str] = []
    lines.append(f"# {hole['number']}: {hole['title']}")
    lines.append("")
    lines.append(f"**Type:** {hole['hole_type']}")
    lines.append(f"**Priority:** P{hole.get('priority', 1)}")
    lines.append(f"**Status:** open")

    blocks = hole.get("blocks_tasks", [])
    if blocks:
        lines.append(f"**Blocks:** {', '.join(f'T{t:03d}' for t in blocks)}")

    lines.append("")

    # Known
    known = hole.get("known", {})
    lines.append("## Known")
    lines.append("")
    if known.get("input"):
        lines.append(f"- Input: {known['input']}")
    if known.get("output"):
        lines.append(f"- Output: {known['output']}")
    for c in known.get("constraints", []):
        lines.append(f"- Constraint: {c}")
    lines.append("")

    # Unknown
    unknown = hole.get("unknown", [])
    lines.append("## Unknown")
    lines.append("")
    for u in unknown:
        lines.append(f"- {u}")
    lines.append("")

    # Resolution
    lines.append("## Resolution Method")
    lines.append("")
    method = hole.get("resolution_method", "unknown")
    lines.append(f"{method}")
    lines.append("")
    lines.append("## Resolution")
    lines.append("")
    lines.append("_Not yet resolved._")
    lines.append("")

    return "\n".join(lines)


def generate_readme(data: dict[str, Any]) -> str:
    """Generate the overview README.md for the tasks directory."""
    from tools.spec_decompose.output_beads import generate_plan_markdown
    return generate_plan_markdown(data)


def generate_state_yaml(
    data: dict[str, Any], spec_files: list[str] | None = None
) -> str:
    """Generate state.yaml for diffing.

    Args:
        data: Validated decomposition output dict.
        spec_files: List of spec file paths for hash computation.

    Returns:
        YAML string.
    """
    # Compute spec hash
    spec_hash = ""
    if spec_files:
        h = hashlib.sha256()
        for sf in sorted(spec_files):
            try:
                h.update(Path(sf).read_bytes())
            except OSError:
                pass
        spec_hash = f"sha256:{h.hexdigest()[:16]}"

    state: dict[str, Any] = {
        "version": 1,
        "spec_source": data.get("spec_source", []),
        "spec_hash": spec_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "epic": data.get("epic", {}),
        "tasks": [],
        "holes": [],
        "parallel_groups": data.get("parallel_groups", []),
        "dependencies": [],
    }

    # Tasks
    for t in data.get("tasks", []):
        task_entry: dict[str, Any] = {
            "number": t["number"],
            "title": t["title"],
            "status": "not_started",
            "priority": t.get("priority", 2),
            "depends_on": t.get("depends_on_tasks", []),
            "blocks": t.get("orchestration", {}).get("blocks", []),
            "traces": t.get("spec_traces", []),
            "estimated_tokens": t.get("estimated_tokens", {}).get("total", 0),
        }
        # Enrichment fields per schemas.md
        if t.get("description"):
            task_entry["description"] = t["description"]
        if t.get("produces"):
            task_entry["produces"] = t["produces"]
        if t.get("orchestration", {}).get("consumes"):
            task_entry["consumes"] = t["orchestration"]["consumes"]
        if t.get("acceptance_criteria"):
            task_entry["acceptance_criteria"] = t["acceptance_criteria"]
        state["tasks"].append(task_entry)

    # Holes
    for h in data.get("holes", []):
        state["holes"].append({
            "number": h["number"],
            "title": h["title"],
            "type": h["hole_type"],
            "status": "not_started",
            "blocks": h.get("blocks_tasks", []),
            "traces": h.get("traces", []),
        })

    # Dependencies
    for t in data.get("tasks", []):
        for dep in t.get("depends_on_tasks", []):
            state["dependencies"].append({
                "from": t["number"],
                "to": dep,
                "type": "blocks",
            })
        for dep in t.get("depends_on_holes", []):
            state["dependencies"].append({
                "from": t["number"],
                "to": dep,
                "type": "blocks",
            })

    return yaml.dump(state, default_flow_style=False, sort_keys=False)


def write_markdown_output(
    data: dict[str, Any],
    output_dir: Path | None = None,
    spec_files: list[str] | None = None,
) -> Path:
    """Write full markdown output directory.

    Args:
        data: Validated decomposition output dict.
        output_dir: Root directory for output. Defaults to docs/tasks/.
        spec_files: Spec file paths for state hash.

    Returns:
        Path to the output directory.
    """
    if output_dir is None:
        output_dir = Path("docs/tasks")

    tasks_dir = output_dir / "tasks"
    holes_dir = output_dir / "holes"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    holes_dir.mkdir(parents=True, exist_ok=True)

    # README
    (output_dir / "README.md").write_text(generate_readme(data))

    # Task files
    for task in data.get("tasks", []):
        num = task["number"]
        slug = _slugify(task["title"])
        filename = f"{num:03d}-{slug}.md"
        (tasks_dir / filename).write_text(generate_task_markdown(task))

    # Hole files
    for hole in data.get("holes", []):
        slug = _slugify(hole["title"])
        filename = f"{hole['number']}-{slug}.md"
        (holes_dir / filename).write_text(generate_hole_markdown(hole))

    # State file
    (output_dir / "state.yaml").write_text(
        generate_state_yaml(data, spec_files)
    )

    return output_dir
