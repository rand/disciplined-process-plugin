"""
Tests for lib/plan_validation module.

Pre-execution plan validation for disciplined-process.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

# Import module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.plan_validation import (
    ValidationStatus,
    CoverageResult,
    TaskCompletenessResult,
    DependencyResult,
    PlanValidationResult,
    check_requirement_coverage,
    check_task_completeness,
    check_dependencies,
    validate_plan,
    format_validation_result,
)


# @trace SPEC-06.01
class TestValidationStatus:
    """Tests for ValidationStatus enum."""

    def test_has_expected_statuses(self):
        """Should have PASS, WARN, FAIL statuses."""
        statuses = list(ValidationStatus)
        assert ValidationStatus.PASS in statuses
        assert ValidationStatus.WARN in statuses
        assert ValidationStatus.FAIL in statuses


# @trace SPEC-06.10, SPEC-06.11
class TestRequirementCoverage:
    """Tests for requirement coverage validation."""

    def test_spec_with_task_is_covered(self):
        """Spec with implementing task should be marked covered."""
        specs = [
            {"id": "SPEC-01.01", "title": "User login", "file": "spec/01.md"}
        ]
        tasks = [
            {
                "id": "task-001",
                "title": "Implement login",
                "description": "@trace SPEC-01.01",
            }
        ]

        results = check_requirement_coverage(specs, tasks)
        assert len(results) == 1
        assert results[0].is_covered is True
        assert results[0].task_id == "task-001"

    def test_spec_without_task_is_orphan(self):
        """Spec without implementing task should be marked orphan."""
        specs = [
            {"id": "SPEC-01.01", "title": "User login", "file": "spec/01.md"},
            {"id": "SPEC-01.02", "title": "User logout", "file": "spec/01.md"},
        ]
        tasks = [
            {
                "id": "task-001",
                "title": "Implement login",
                "description": "@trace SPEC-01.01",
            }
        ]

        results = check_requirement_coverage(specs, tasks)
        covered = [r for r in results if r.is_covered]
        orphans = [r for r in results if not r.is_covered]

        assert len(covered) == 1
        assert len(orphans) == 1
        assert orphans[0].spec_id == "SPEC-01.02"

    def test_coverage_via_title_mention(self):
        """Spec mentioned in task title should count as covered."""
        specs = [
            {"id": "SPEC-02.01", "title": "Password validation", "file": "spec/02.md"}
        ]
        tasks = [
            {
                "id": "task-002",
                "title": "Implement SPEC-02.01 password validation",
                "description": "Add password validation logic",
            }
        ]

        results = check_requirement_coverage(specs, tasks)
        assert results[0].is_covered is True


# @trace SPEC-06.20, SPEC-06.21
class TestTaskCompleteness:
    """Tests for task completeness validation."""

    def test_task_with_acceptance_criteria_is_complete(self):
        """Task with acceptance criteria should be marked complete."""
        tasks = [
            {
                "id": "task-001",
                "title": "Implement feature",
                "description": dedent("""
                    Build the feature.

                    Acceptance Criteria:
                    - Feature works correctly
                    - Tests pass
                """),
            }
        ]

        results = check_task_completeness(tasks)
        assert len(results) == 1
        assert results[0].has_criteria is True
        assert "acceptance criteria" in results[0].criteria_type.lower()

    def test_task_with_trace_is_complete(self):
        """Task with @trace marker should be marked complete."""
        tasks = [
            {
                "id": "task-002",
                "title": "Implement login",
                "description": "@trace SPEC-01.01\n\nImplement the login feature.",
            }
        ]

        results = check_task_completeness(tasks)
        assert results[0].has_criteria is True
        assert "spec" in results[0].criteria_type.lower()

    def test_task_without_criteria_is_incomplete(self):
        """Task without criteria should be marked incomplete."""
        tasks = [
            {
                "id": "task-003",
                "title": "Do something",
                "description": "Just a vague description.",
            }
        ]

        results = check_task_completeness(tasks)
        assert results[0].has_criteria is False

    def test_task_with_must_have_is_complete(self):
        """Task with @must_have should be marked complete."""
        tasks = [
            {
                "id": "task-004",
                "title": "Build chat",
                "description": dedent("""
                    @must_have:
                      truth: User can send messages
                      artifact: src/Chat.tsx
                """),
            }
        ]

        results = check_task_completeness(tasks)
        assert results[0].has_criteria is True


# @trace SPEC-06.30, SPEC-06.31
class TestDependencyCorrectness:
    """Tests for dependency validation."""

    def test_no_dependencies_is_valid(self):
        """Tasks with no dependencies should pass."""
        tasks = [
            {"id": "task-001", "blocks": [], "blockedBy": []},
            {"id": "task-002", "blocks": [], "blockedBy": []},
        ]

        result = check_dependencies(tasks)
        assert result.is_valid is True
        assert result.has_cycles is False

    def test_linear_dependencies_valid(self):
        """Linear dependency chain should be valid."""
        tasks = [
            {"id": "task-001", "blocks": ["task-002"], "blockedBy": []},
            {"id": "task-002", "blocks": ["task-003"], "blockedBy": ["task-001"]},
            {"id": "task-003", "blocks": [], "blockedBy": ["task-002"]},
        ]

        result = check_dependencies(tasks)
        assert result.is_valid is True
        assert result.has_cycles is False

    def test_circular_dependency_detected(self):
        """Circular dependencies should be detected."""
        tasks = [
            {"id": "task-001", "blocks": ["task-002"], "blockedBy": ["task-002"]},
            {"id": "task-002", "blocks": ["task-001"], "blockedBy": ["task-001"]},
        ]

        result = check_dependencies(tasks)
        assert result.is_valid is False
        assert result.has_cycles is True

    def test_missing_reference_detected(self):
        """Reference to non-existent task should be detected."""
        tasks = [
            {"id": "task-001", "blocks": ["task-999"], "blockedBy": []},
        ]

        result = check_dependencies(tasks)
        assert result.is_valid is False
        assert "task-999" in str(result.missing_refs)

    def test_self_reference_detected(self):
        """Self-referencing task should be detected."""
        tasks = [
            {"id": "task-001", "blocks": ["task-001"], "blockedBy": []},
        ]

        result = check_dependencies(tasks)
        assert result.is_valid is False


# @trace SPEC-06.50
class TestValidatePlan:
    """Tests for full plan validation."""

    def test_validates_complete_plan(self):
        """Should return PASS for well-formed plan."""
        specs = [
            {"id": "SPEC-01.01", "title": "Login", "file": "spec/01.md"}
        ]
        tasks = [
            {
                "id": "task-001",
                "title": "Implement login",
                "description": "@trace SPEC-01.01\n\nAcceptance Criteria:\n- Works",
                "blocks": [],
                "blockedBy": [],
            }
        ]

        result = validate_plan(specs, tasks)
        assert result.status == ValidationStatus.PASS

    def test_warns_for_missing_criteria(self):
        """Should return WARN for tasks missing criteria."""
        specs = []
        tasks = [
            {
                "id": "task-001",
                "title": "Do something",
                "description": "Vague task",
                "blocks": [],
                "blockedBy": [],
            }
        ]

        result = validate_plan(specs, tasks)
        assert result.status in (ValidationStatus.WARN, ValidationStatus.PASS)

    def test_fails_for_circular_deps(self):
        """Should return FAIL for circular dependencies."""
        specs = []
        tasks = [
            {
                "id": "task-001",
                "title": "Task A",
                "description": "Acceptance Criteria:\n- Done",
                "blocks": ["task-002"],
                "blockedBy": ["task-002"],
            },
            {
                "id": "task-002",
                "title": "Task B",
                "description": "Acceptance Criteria:\n- Done",
                "blocks": ["task-001"],
                "blockedBy": ["task-001"],
            },
        ]

        result = validate_plan(specs, tasks)
        assert result.status == ValidationStatus.FAIL


# @trace SPEC-06.60, SPEC-06.61
class TestValidationOutput:
    """Tests for validation output formatting."""

    def test_format_includes_sections(self):
        """Output should include all validation sections."""
        result = PlanValidationResult(
            status=ValidationStatus.PASS,
            coverage=[
                CoverageResult("SPEC-01.01", "Login", True, "task-001")
            ],
            completeness=[
                TaskCompletenessResult("task-001", "Impl login", True, "acceptance criteria")
            ],
            dependencies=DependencyResult(True, False, [], []),
            warnings=[],
            errors=[],
        )

        output = format_validation_result(result)
        assert "Requirement Coverage" in output
        assert "Task Completeness" in output
        assert "Dependencies" in output
        assert "PASS" in output

    def test_format_shows_orphan_specs(self):
        """Output should highlight orphan specs."""
        result = PlanValidationResult(
            status=ValidationStatus.WARN,
            coverage=[
                CoverageResult("SPEC-01.01", "Login", True, "task-001"),
                CoverageResult("SPEC-01.02", "Logout", False, None),
            ],
            completeness=[],
            dependencies=DependencyResult(True, False, [], []),
            warnings=["SPEC-01.02 has no implementing task"],
            errors=[],
        )

        output = format_validation_result(result)
        assert "SPEC-01.02" in output
        assert "NO TASK" in output or "orphan" in output.lower()

    def test_format_shows_cycles(self):
        """Output should show circular dependencies."""
        result = PlanValidationResult(
            status=ValidationStatus.FAIL,
            coverage=[],
            completeness=[],
            dependencies=DependencyResult(
                False, True, [], ["task-001 -> task-002 -> task-001"]
            ),
            warnings=[],
            errors=["Circular dependency detected"],
        )

        output = format_validation_result(result)
        assert "circular" in output.lower() or "cycle" in output.lower()
