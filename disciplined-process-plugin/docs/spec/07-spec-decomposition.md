# Spec Decomposition
[SPEC-07]

## Overview

[SPEC-07.01] The spec decomposition system SHALL transform specifications into dependency-aware, context-window-sized work items suitable for AI agent execution.

[SPEC-07.02] Decomposition bridges the gap between high-level specifications and executable tasks by:
- Partitioning specs into right-sized work items
- Identifying dependencies between items
- Surfacing ambiguities as first-class "holes" that block downstream work
- Generating executable task plans (Beads commands or markdown files)

## Core Concepts

### Work Items

[SPEC-07.10] A **work item** is a unit of implementation derived from one or more spec paragraphs.

[SPEC-07.11] Each work item SHALL include:
- Title and description
- Spec references (`[SPEC-XX.YY]`) it implements
- Estimated context size (tokens)
- File paths it will create or modify
- Dependencies on other work items

[SPEC-07.12] Work items SHALL be sized to fit within a configurable context window (default: 200,000 tokens) including the spec text, existing code context, and implementation space.

### Holes

[SPEC-07.20] A **hole** is an ambiguity or missing information discovered during decomposition.

[SPEC-07.21] Holes SHALL be categorized by type:
- `clarification` — requires human decision (blocks until resolved)
- `validation` — can be resolved by checking existing code
- `research` — can be resolved by reading documentation or APIs
- `design` — requires architectural decision

[SPEC-07.22] Holes SHALL be tracked as Beads issues with the `hole` label and appropriate sub-label (e.g., `hole:clarification`).

[SPEC-07.23] The `--holes-strategy` option SHALL control hole handling:
- `graph` (default) — holes become blocking dependencies in the task graph
- `warn` — holes logged as warnings, work proceeds
- `strict` — decomposition fails if any holes found
- `assume` — agent makes best-effort assumptions, documents them

### Dependency Graph

[SPEC-07.30] Decomposition output SHALL form a valid directed acyclic graph (DAG).

[SPEC-07.31] The system SHALL validate the DAG for:
- No circular dependencies
- All dependency references resolve to existing items
- No orphan items (items with no path to the root epic)

[SPEC-07.32] Work items blocked by holes SHALL NOT be marked as ready until the hole is resolved.

## Modes

### Fresh Decomposition

[SPEC-07.40] Fresh mode (default) SHALL produce a complete task graph from spec files.

[SPEC-07.41] Output artifacts:
- `decompose-plan.md` — human-readable plan
- `decompose-plan.sh` — executable Beads commands (when `--output beads`)
- Task files in `docs/tasks/` (when `--output markdown`)

### Diff Mode

[SPEC-07.50] Diff mode (`--diff`) SHALL compare new decomposition against existing state.

[SPEC-07.51] The system SHALL detect:
- New tasks not present in current state
- Modified tasks (spec changes affecting existing work)
- Completed tasks that can be skipped
- Obsolete tasks no longer needed

[SPEC-07.52] Diff output SHALL be incremental commands that update rather than replace.

### Orchestrate Mode

[SPEC-07.60] Orchestrate mode (`--orchestrate`) SHALL generate a fan-out script for multi-agent parallel execution.

[SPEC-07.61] The script SHALL:
- Respect dependency ordering (only start items whose deps are complete)
- Limit concurrency to `--parallel-slots` (default: 3)
- Use separate git worktrees per agent
- Poll for completion and dispatch newly unblocked items

## Subagent Architecture

[SPEC-07.70] Decomposition SHALL be performed by a dedicated `decomposer` subagent invoked with a clean context.

[SPEC-07.71] The subagent receives:
- Combined spec text
- Context window target
- Holes strategy
- Constitution/principles (if provided)
- Existing codebase structure (if `--existing-code` provided)

[SPEC-07.72] The subagent returns structured JSON containing tasks, holes, and dependency edges.

[SPEC-07.73] The CLI validates subagent output against the expected schema before generating artifacts.

## Command Interface

### /dp:decompose

[SPEC-07.80] The `/dp:decompose` command SHALL accept spec files and options:

```
/dp:decompose <spec-files...>                         # Fresh decomposition
/dp:decompose --diff <spec-files...>                  # Incremental update
/dp:decompose <spec-files...> --orchestrate           # With fan-out script
/dp:decompose <spec-files...> --dry-run               # Plan without output
/dp:decompose <spec-files...> --output markdown       # Markdown tasks
```

[SPEC-07.81] The command SHALL return non-zero exit code on:
- No spec files found
- Validation errors in decomposition output
- DAG validation failures
- Strict mode with holes present

## Integration

### With Specifications (SPEC-02)

[SPEC-07.90] Decomposition SHALL preserve `[SPEC-XX.YY]` references from source specs into generated work items.

### With Task Tracking (SPEC-01)

[SPEC-07.91] When `--output beads`, generated commands SHALL create Beads issues with proper dependencies via `bd create` and `bd dep add`.

### With Progress Reporting (SPEC-08)

[SPEC-07.92] Progress reporting SHALL track decomposed work items and report completion against the original decomposition plan.

### With Task Executor Skill

[SPEC-07.93] Generated work items SHALL follow the format expected by the `task-executor` skill for agent execution.

## Sizing

[SPEC-07.95] Post-decomposition validation SHALL warn when:
- Any single task exceeds the target context window
- Total decomposition size suggests the spec should be sharded
- File estimates suggest overlapping work between tasks

## Configuration

[SPEC-07.99] Decomposition behavior is configured via CLI arguments. No persistent configuration file is required, though `--constitution` allows injecting project-specific principles.
