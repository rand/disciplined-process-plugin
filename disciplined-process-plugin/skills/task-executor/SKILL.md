---
name: task-executor
description: >
  Use when working from decomposed task files or Beads issues created by
  spec-decompose. Guides proper task pickup, context loading, implementation,
  and handoff. Triggers when working with decomposed tasks, task files in
  docs/tasks/, or Beads issues with hole labels.
---

# Working from Decomposed Tasks

## Finding Work

If using Beads:
```bash
bd ready --json           # See unblocked tasks
bd show <id>              # Full task details
bd update <id> --status in_progress  # Claim it
```

If ready list is empty, check for agent-resolvable holes:
```bash
bd list --label hole:agent-resolvable --status open --json
```

If using Markdown task files:
1. Read `docs/tasks/README.md` for the dependency graph
2. Find a task with status "open" whose dependencies are all "complete"

## Before Starting

1. Read the task description fully
2. Read every file listed in "Context files to read"
3. Read the spec sections referenced in "Spec Traces"
4. Do NOT read the entire spec — only the sections listed
   (Task descriptions are self-contained by design)

## Implementation

1. Write tests FIRST based on the acceptance criteria
2. Implement the minimal code to pass the tests
3. Add `@trace SPEC-XX.YY` comments to your implementation
4. Run the full test suite, not just your new tests

## Completion

1. All acceptance criteria met (tests passing)
2. Commit with a message referencing the task
3. Beads: `bd close <id> --reason "Implemented: <brief summary>"`
4. Markdown: Update the task file status to `complete`

## Discovering New Work

If you find work not covered by existing tasks:
```bash
bd create "Title" -p 2 --deps discovered-from:<current-task> --json
```
Do NOT expand your current task's scope. File it and move on.

## Discovering Unknowns During Implementation

If you encounter something you cannot resolve:

1. Do NOT guess and proceed
2. Do NOT expand your task scope to include the investigation
3. Create a hole:
```bash
bd create "HOLE: <concise description>" \
  -t task -p 1 -l "hole,escalation" \
  -d "<what's known, what's unknown, what's blocked>" \
  --deps discovered-from:<current-task-id> \
  --json
```

4. If the hole blocks YOUR current task:
   - Implement everything you can that doesn't depend on the answer
   - Document what remains with clear markers
   - Leave the task as in_progress (not closed)
   - Note: "Blocked on <hole-id>: <description>"
   - Move on to the next ready task

5. If the hole does NOT block your current task:
   - Create it, link it, continue your work
   - Another agent or human will handle it

## Hole Resolution (agent-resolvable types)

For `validation` holes: check docs, APIs, codebase. Binary answer.
For `research` holes: investigate options, synthesize recommendation.

```bash
bd update "$HOLE" --status in_progress
# ... investigate ...
bd close "$HOLE" --reason "Validated: <finding>"
```

## Context Loading for Fresh Agents

When starting a new session:
1. Read `docs/progress/latest.md` for high-level state (~2K tokens)
2. Run `bd ready --json` for your next task
3. Run `bd show <task-id>` for full details including context files
4. Do NOT read the full spec, git log, or all task files
