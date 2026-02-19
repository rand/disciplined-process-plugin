# Agent Skills

**Parent:** [README.md](./README.md)  
**Related:** [holes.md](./holes.md) · [orchestration.md](./orchestration.md) · [progress-report.md](./progress-report.md)

---

## Overview

Two skills teach agents how to work within the decomposition system: `task-executor` for consuming work items, and the hole-handling behaviors embedded within it. These skills are packaged as `.claude/agents/` definitions or as prompt templates for other agent systems.

---

## Skill: task-executor

```markdown
---
name: task-executor
description: >
  Use when working from decomposed task files or Beads issues created by
  spec-decompose. Guides proper task pickup, context loading, implementation,
  and handoff.
---

# Working from Decomposed Tasks

## Finding Work

If using Beads:
  Run `bd ready --json` to see unblocked tasks.
  Pick the highest priority task.
  Run `bd update <id> --status in_progress`

If using Markdown task files:
  Check docs/tasks/README.md for the dependency graph.
  Find a task with status "open" whose dependencies are all "complete."

## Before Starting

1. Read the task description fully.
2. Read every file listed in "Context files to read."
3. Read the spec sections referenced in "Spec Traces."
4. Do NOT read the entire spec — only the sections listed.
   (The task description is self-contained by design.)

## Implementation

1. Write tests FIRST based on the acceptance criteria.
2. Implement the minimal code to pass the tests.
3. Add @trace SPEC-XX.YY comments to your implementation.
4. Run the full test suite, not just your new tests.

## Completion

1. All acceptance criteria met (tests passing).
2. Commit with a message referencing the task.
3. If using Beads: `bd close <id> --reason "Implemented: <brief summary>"`
4. If using Markdown: Update the task file status to `complete`
5. Run `bd sync` or commit task file changes.

## Discovering New Work

If you find work not covered by existing tasks:
- Beads: `bd create "Title" -p 2 --deps discovered-from:<current-task> --json`
- Markdown: Create a new task file, note the discovery source, add to graph.
- Do NOT expand your current task's scope. File it and move on.

## Discovering Unknowns During Implementation

If you encounter something you cannot resolve:

1. Do NOT guess and proceed.
2. Do NOT expand your task scope to include the investigation.
3. Create a hole:

   Beads:
     bd create "HOLE: <concise description of unknown>" \
       -t task -p 1 -l "hole,escalation" \
       -d "<what's known, what's unknown, what's blocked>" \
       --deps discovered-from:<current-task-id> \
       --json

4. If the hole blocks YOUR current task:
   - Implement everything you can that doesn't depend on the answer.
   - Document what remains with clear markers.
   - Leave the task as in_progress (not closed).
   - Note in the task: "Blocked on <hole-id>: <description>"
   - Move on to the next ready task.

5. If the hole does NOT block your current task:
   - Create it, link it, continue your work.
   - Another agent or human will handle it.

## When No Tasks Are Ready

If `bd ready` returns nothing:
1. Check for agent-resolvable holes:
   `bd list --label hole:agent-resolvable --status open --json`
2. If a validation or research hole exists, pick it up and investigate.
3. If only human-required holes remain, report status and stop.
```

---

## Hole Resolution Behaviors

### Agent Self-Resolution (validation, research)

```bash
# Agent picks up a resolvable hole
HOLE=$(bd list --label hole:agent-resolvable --status open --json \
       | jq -r '.[0].id')
bd update "$HOLE" --status in_progress

# Agent investigates (reads docs, checks APIs, runs experiments)

# Agent resolves
bd close "$HOLE" --reason "Validated: S3 provider supports If-None-Match \
  via ETag headers. See https://docs.provider.com/conditional-requests"
```

### Human Resolution (clarification, escalation)

```bash
# Human sees hole in progress report or Slack notification
# Human reviews context, makes decision
bd close "$HOLE" --reason "Decision: Use eager session invalidation. \
  Push revocation events via WebSocket."

# Optionally trigger re-decomposition to update blocked tasks
spec-decompose --diff docs/spec/auth.md
```

### Progressive Refinement (research → clarification)

An agent narrows a research hole, then a human makes the final call:

```
H003: Rate limit algorithm
  Type: research → Agent narrows to 2 options → Type changed to: clarification
  → Human decides: Sliding window + Redis → H003 resolved
  → T009 updated with specific implementation guidance
```

The orchestrator can be configured to automatically assign `validation` and `research` holes to agents, while routing `clarification` and `escalation` holes to humans via broadcast notifications.

---

## Context Loading for Fresh Agents

When an agent starts a new session and needs to orient quickly:

1. Read `docs/progress/latest.md` for high-level state (~2K tokens).
2. Run `bd ready --json` for the next task.
3. Run `bd show <task-id>` for full task details including context files.
4. Do NOT read the full spec, git log, or all task files.

The progress report's "For Agents" section is deliberately terse and directive — it enables orientation in <2K tokens rather than requiring the agent to reconstruct state from raw project artifacts.
