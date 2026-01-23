"""
Pre-execution plan validation for disciplined-process.

Validates plans before execution to catch issues early.

@trace SPEC-06
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationStatus(Enum):
    """Outcome of plan validation."""

    PASS = "pass"  # No blocking issues
    WARN = "warn"  # Warnings only
    FAIL = "fail"  # Blocking issues found


@dataclass
class CoverageResult:
    """Result of checking if a spec has an implementing task."""

    spec_id: str
    spec_title: str
    is_covered: bool
    task_id: str | None = None


@dataclass
class TaskCompletenessResult:
    """Result of checking if a task has verification criteria."""

    task_id: str
    task_title: str
    has_criteria: bool
    criteria_type: str = ""  # "acceptance criteria", "spec trace", "must_have"


@dataclass
class DependencyResult:
    """Result of checking task dependencies."""

    is_valid: bool
    has_cycles: bool
    missing_refs: list[str] = field(default_factory=list)
    cycles: list[str] = field(default_factory=list)


@dataclass
class PlanValidationResult:
    """Complete plan validation result."""

    status: ValidationStatus
    coverage: list[CoverageResult] = field(default_factory=list)
    completeness: list[TaskCompletenessResult] = field(default_factory=list)
    dependencies: DependencyResult | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# @trace SPEC-06.10, SPEC-06.11
def check_requirement_coverage(
    specs: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> list[CoverageResult]:
    """
    Check if specs have implementing tasks.

    Args:
        specs: List of spec dicts with id, title, file
        tasks: List of task dicts with id, title, description

    Returns:
        List of CoverageResult for each spec
    """
    results: list[CoverageResult] = []

    for spec in specs:
        spec_id = spec.get("id", "")
        spec_title = spec.get("title", "")

        # Look for task that references this spec
        covering_task = None
        for task in tasks:
            task_text = (
                task.get("title", "")
                + " "
                + task.get("description", "")
            ).upper()

            # Check for @trace marker or spec ID mention
            if spec_id.upper() in task_text:
                covering_task = task.get("id")
                break

        results.append(
            CoverageResult(
                spec_id=spec_id,
                spec_title=spec_title,
                is_covered=covering_task is not None,
                task_id=covering_task,
            )
        )

    return results


# @trace SPEC-06.20, SPEC-06.21
def check_task_completeness(
    tasks: list[dict[str, Any]],
) -> list[TaskCompletenessResult]:
    """
    Check if tasks have verification criteria.

    A task is complete if it has:
    - Acceptance criteria bullet points
    - @trace SPEC-XX.YY references
    - @must_have annotations

    Args:
        tasks: List of task dicts

    Returns:
        List of TaskCompletenessResult for each task
    """
    results: list[TaskCompletenessResult] = []

    for task in tasks:
        task_id = task.get("id", "")
        task_title = task.get("title", "")
        description = task.get("description", "")

        has_criteria = False
        criteria_type = ""

        # Check for acceptance criteria
        if re.search(r"acceptance\s+criteria:", description, re.IGNORECASE):
            has_criteria = True
            criteria_type = "Acceptance Criteria"

        # Check for @trace markers
        elif re.search(r"@trace\s+SPEC-\d+\.\d+", description, re.IGNORECASE):
            has_criteria = True
            criteria_type = "Spec Trace"

        # Check for @must_have
        elif re.search(r"@must_have:", description, re.IGNORECASE):
            has_criteria = True
            criteria_type = "Must-Have"

        # Check for success criteria
        elif re.search(r"success\s+criteria:", description, re.IGNORECASE):
            has_criteria = True
            criteria_type = "Success Criteria"

        # Check for done criteria
        elif re.search(r"done\s+(?:when|criteria):", description, re.IGNORECASE):
            has_criteria = True
            criteria_type = "Done Criteria"

        results.append(
            TaskCompletenessResult(
                task_id=task_id,
                task_title=task_title,
                has_criteria=has_criteria,
                criteria_type=criteria_type,
            )
        )

    return results


# @trace SPEC-06.30, SPEC-06.31
def check_dependencies(
    tasks: list[dict[str, Any]],
) -> DependencyResult:
    """
    Check task dependencies for validity.

    Checks:
    - No circular dependencies
    - All referenced tasks exist
    - No self-references

    Args:
        tasks: List of task dicts with blocks/blockedBy

    Returns:
        DependencyResult with validation status
    """
    task_ids = {task.get("id") for task in tasks}
    missing_refs: list[str] = []
    cycles: list[str] = []
    has_cycles = False

    # Build dependency graph
    graph: dict[str, set[str]] = {}
    for task in tasks:
        task_id = task.get("id", "")
        blocked_by = task.get("blockedBy", []) or []
        blocks = task.get("blocks", []) or []

        if task_id not in graph:
            graph[task_id] = set()

        # Check blockedBy references
        for dep_id in blocked_by:
            if dep_id == task_id:
                cycles.append(f"{task_id} references itself")
                has_cycles = True
            elif dep_id not in task_ids:
                missing_refs.append(dep_id)
            else:
                graph[task_id].add(dep_id)

        # Check blocks references
        for dep_id in blocks:
            if dep_id == task_id:
                cycles.append(f"{task_id} references itself")
                has_cycles = True
            elif dep_id not in task_ids:
                missing_refs.append(dep_id)

    # Detect cycles using DFS
    def has_cycle_from(start: str, visited: set[str], path: set[str]) -> bool:
        if start in path:
            return True
        if start in visited:
            return False

        visited.add(start)
        path.add(start)

        for neighbor in graph.get(start, set()):
            if has_cycle_from(neighbor, visited, path):
                cycles.append(f"{start} -> {neighbor} (cycle)")
                return True

        path.remove(start)
        return False

    visited: set[str] = set()
    for task_id in graph:
        if has_cycle_from(task_id, visited, set()):
            has_cycles = True
            break

    is_valid = not has_cycles and len(missing_refs) == 0

    return DependencyResult(
        is_valid=is_valid,
        has_cycles=has_cycles,
        missing_refs=list(set(missing_refs)),
        cycles=cycles,
    )


# @trace SPEC-06.50
def validate_plan(
    specs: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> PlanValidationResult:
    """
    Validate a plan before execution.

    Args:
        specs: List of spec dicts
        tasks: List of task dicts

    Returns:
        PlanValidationResult with overall status
    """
    warnings: list[str] = []
    errors: list[str] = []

    # Check requirement coverage
    coverage = check_requirement_coverage(specs, tasks)
    orphan_specs = [c for c in coverage if not c.is_covered]
    for orphan in orphan_specs:
        warnings.append(f"{orphan.spec_id} has no implementing task")

    # Check task completeness
    completeness = check_task_completeness(tasks)
    incomplete_tasks = [t for t in completeness if not t.has_criteria]
    for task in incomplete_tasks:
        warnings.append(f"Task {task.task_id} missing verification criteria")

    # Check dependencies
    dependencies = check_dependencies(tasks)
    if dependencies.has_cycles:
        errors.append("Circular dependency detected")
    for ref in dependencies.missing_refs:
        errors.append(f"Reference to non-existent task: {ref}")

    # Determine status
    if errors:
        status = ValidationStatus.FAIL
    elif warnings:
        status = ValidationStatus.WARN
    else:
        status = ValidationStatus.PASS

    return PlanValidationResult(
        status=status,
        coverage=coverage,
        completeness=completeness,
        dependencies=dependencies,
        warnings=warnings,
        errors=errors,
    )


# @trace SPEC-06.60
def format_validation_result(result: PlanValidationResult) -> str:
    """Format validation result for display."""
    lines = ["Plan Validation", "===============", ""]

    # Requirement Coverage
    if result.coverage:
        lines.append("Requirement Coverage:")
        for cov in result.coverage:
            if cov.is_covered:
                status = "[ok]"
                task_info = f"→ {cov.task_id}"
            else:
                status = "[WARN]"
                task_info = "→ NO TASK (orphan)"
            lines.append(f"  {status} {cov.spec_id} ({cov.spec_title}) {task_info}")
        lines.append("")

    # Task Completeness
    if result.completeness:
        lines.append("Task Completeness:")
        for comp in result.completeness:
            if comp.has_criteria:
                status = "[ok]"
                criteria = f"has {comp.criteria_type}"
            else:
                status = "[WARN]"
                criteria = "missing verification criteria"
            lines.append(f"  {status} {comp.task_id} ({comp.task_title}) - {criteria}")
        lines.append("")

    # Dependencies
    if result.dependencies:
        lines.append("Dependencies:")
        if result.dependencies.is_valid:
            lines.append("  [ok] No circular dependencies")
            lines.append("  [ok] All references valid")
        else:
            if result.dependencies.has_cycles:
                lines.append("  [FAIL] Circular dependency detected")
                for cycle in result.dependencies.cycles:
                    lines.append(f"    - {cycle}")
            for ref in result.dependencies.missing_refs:
                lines.append(f"  [FAIL] Missing reference: {ref}")
        lines.append("")

    # Warnings
    if result.warnings:
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    # Errors
    if result.errors:
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  - {error}")
        lines.append("")

    # Summary
    total_issues = len(result.warnings) + len(result.errors)
    lines.append(f"Status: {result.status.value.upper()}")
    if total_issues > 0:
        lines.append(
            f"  {len(result.errors)} blocking, {len(result.warnings)} warnings"
        )

    return "\n".join(lines)
