# Plan Validation
[SPEC-06]

## Overview

[SPEC-06.01] The plan validation system SHALL verify plans before execution to catch issues early.

[SPEC-06.02] Plan validation prevents wasted context by checking:
- Requirement coverage (specs have implementing tasks)
- Task completeness (tasks have verification criteria)
- Dependency correctness (no cycles, valid references)
- Orphan detection (specs without tasks, tasks without specs)

## Validation Dimensions

### Requirement Coverage

[SPEC-06.10] The system SHALL verify that specs have corresponding tasks.

[SPEC-06.11] For each spec in the current scope:
- Check if any task references the spec (via `@trace` or description)
- Flag specs with no implementing task as "orphan specs"

[SPEC-06.12] Coverage status indicators:
- `[ok]` - Spec has implementing task(s)
- `[WARN]` - Spec has no task (orphan)

### Task Completeness

[SPEC-06.20] The system SHALL verify tasks have verification criteria.

[SPEC-06.21] A task is considered complete if it has:
- Acceptance criteria (bullet points describing done state)
- OR linked specs (`@trace SPEC-XX.YY` references)
- OR explicit `@must_have` annotations

[SPEC-06.22] Task completeness status:
- `[ok]` - Task has verification criteria
- `[WARN]` - Task missing verification criteria

### Dependency Correctness

[SPEC-06.30] The system SHALL verify task dependencies are valid.

[SPEC-06.31] Dependency checks:
- No circular dependencies (A blocks B blocks A)
- All referenced tasks exist
- No self-references

[SPEC-06.32] Dependency status:
- `[ok]` - Dependencies valid
- `[FAIL]` - Circular dependency detected
- `[FAIL]` - Reference to non-existent task

### Scope Assessment

[SPEC-06.40] The system MAY warn about scope concerns.

[SPEC-06.41] Scope warnings include:
- Large number of tasks (>10) without phasing
- Many files listed without clear organization
- Missing acceptance criteria across multiple tasks

## Command Interface

### /dp:review --plan

[SPEC-06.50] The `/dp:review` command SHALL accept a `--plan` flag for plan validation.

```
/dp:review --plan              # Validate current plan/tasks
/dp:review --plan --spec SPEC-03  # Validate specific spec section
```

[SPEC-06.51] Plan validation MAY also be invoked via `/dp:plan check` alias.

### Output Format

[SPEC-06.60] Plan validation output SHALL include:

```
Plan Validation
===============

Requirement Coverage:
  [status] SPEC-XX.YY (<title>) → <task-id or "NO TASK">
  ...

Task Completeness:
  [status] <task-id> (<title>) - <criteria found or "missing criteria">
  ...

Dependencies:
  [status] <check description>
  ...

Summary: N issues found (X blocking, Y warnings)
```

[SPEC-06.61] Validation outcomes:
- **PASS**: No blocking issues
- **WARN**: Warnings only (can proceed with caution)
- **FAIL**: Blocking issues (should resolve before execution)

## Integration

### With Plan Mode

[SPEC-06.70] When Claude Code enters plan mode, plan validation MAY run automatically if configured.

### With Task Tracking

[SPEC-06.71] Plan validation SHALL use the configured task tracker to:
- Fetch task list and dependencies
- Check for circular dependencies
- Verify task references

### With Specs

[SPEC-06.72] Plan validation SHALL scan spec files to:
- Find all `[SPEC-XX.YY]` definitions
- Match with `@trace` markers in tasks/code
- Report orphan specs

## Configuration

[SPEC-06.80] Plan validation behavior configurable in `dp-config.yaml`:

```yaml
plan_validation:
  auto_on_plan_mode: false  # Run when entering plan mode
  require_acceptance_criteria: true
  max_tasks_warning: 10
  check_dependencies: true  # Requires Beads/Chainlink
```
