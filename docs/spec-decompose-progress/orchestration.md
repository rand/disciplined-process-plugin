# Multi-Agent Orchestration

**Parent:** [README.md](./README.md)  
**Related:** [decomposition.md](./decomposition.md) · [holes.md](./holes.md) · [progress-report.md](./progress-report.md) · [agent-skills.md](./agent-skills.md)

---

## Overview

Multi-agent workflows are first-class in the decomposition. The tool explicitly identifies parallelism opportunities and provides the affordances agents and orchestrators need to coordinate work safely.

Two orchestration models are supported: **push-based** (phased fan-out with verification gates) and **pull-based** (agents self-select work via `bd ready`). Both can be combined.

---

## Parallel Groups

Every decomposition identifies **parallel groups** — sets of tasks with no mutual dependencies that can execute concurrently:

```yaml
parallel_groups:
  - name: "foundation"
    tasks: [1, 2, 9]
    rationale: "No shared dependencies, different modules"
  - name: "post-oauth"
    tasks: [4, 5]
    rationale: "Both depend on token exchange, independent of each other"
  - name: "polish"
    tasks: [7, 11, 12]
    rationale: "All depend on core flow, independent of each other"
```

Parallel groups become **phases** in the orchestration script. Each phase executes its tasks concurrently, then verifies completion before the next phase starts.

---

## Push-Based: Fan-Out Script Generation

When `--orchestrate` is specified, the tool generates an orchestration script:

```bash
spec-decompose ./docs/spec.md --output beads --orchestrate
# Additional output: orchestrate.sh
```

The generated `orchestrate.sh` for Claude Code:

```bash
#!/usr/bin/env bash
set -euo pipefail

PARALLEL_SLOTS=${PARALLEL_SLOTS:-3}

# Phase 1: Foundation (all can start immediately)
echo "=== Phase 1: Foundation (parallel) ==="
parallel_pids=()

claude -p "You are working on task bd-a1b2 (Configure OAuth provider). \
  Run 'bd show bd-a1b2' for full details. \
  Follow the task-executor workflow." \
  --allowedTools 'Bash,Read,Write,Edit' &
parallel_pids+=($!)

claude -p "You are working on task bd-c3d4 (PKCE challenge generation). \
  Run 'bd show bd-c3d4' for full details. \
  Follow the task-executor workflow." \
  --allowedTools 'Bash,Read,Write,Edit' &
parallel_pids+=($!)

# Wait for Phase 1
for pid in "${parallel_pids[@]}"; do
  wait "$pid" || echo "WARNING: Agent $pid exited non-zero"
done

# Verify Phase 1 completion
echo "Verifying Phase 1..."
for task_id in bd-a1b2 bd-c3d4; do
  status=$(bd show "$task_id" --json | jq -r '.status')
  if [ "$status" != "closed" ]; then
    echo "ERROR: $task_id is $status, expected closed. Halting."
    exit 1
  fi
done

# Phase 2: Depends on Phase 1 outputs
echo "=== Phase 2: Core Implementation (parallel) ==="
# ... (pattern continues, respecting dependency phases)
```

For Codex or other agents, the orchestration script generates equivalent task dispatch commands.

---

## Pull-Based: Adaptive Orchestration via `bd ready`

For simpler setups (or when phases don't cleanly separate), agents self-select work in a pull-based loop:

```bash
while true; do
  NEXT=$(bd ready --json --limit 1 | jq -r '.[0].id // empty')
  if [ -z "$NEXT" ]; then
    echo "All tasks complete or blocked."
    break
  fi

  bd update "$NEXT" --status in_progress

  claude -p "You are working on task $NEXT. \
    Run 'bd show $NEXT' for full details. \
    Follow the task-executor workflow." \
    --allowedTools 'Bash,Read,Write,Edit'

  status=$(bd show "$NEXT" --json | jq -r '.status')
  if [ "$status" != "closed" ]; then
    echo "WARNING: $NEXT not closed by agent (status: $status)"
  fi
done
```

Multiple instances of this loop can run concurrently — Beads' hash-based IDs and `--status in_progress` claiming prevents collisions.

### Hole-Aware Pull Loop

When all tasks are blocked by holes, the pull loop can optionally attempt to resolve agent-resolvable holes:

```bash
while true; do
  NEXT=$(bd ready --json --limit 1 | jq -r '.[0].id // empty')

  if [ -z "$NEXT" ]; then
    # No tasks ready — check for agent-resolvable holes
    HOLE=$(bd list --label hole:agent-resolvable --status open --json \
           | jq -r '.[0].id // empty')
    if [ -z "$HOLE" ]; then
      echo "All work complete or blocked on human decisions."
      break
    fi
    NEXT="$HOLE"
  fi

  bd update "$NEXT" --status in_progress
  # ... dispatch to agent as above
done
```

---

## Verification Gates

Between orchestration phases, the generated script verifies:

1. **Task completion** — all tasks in the phase are closed.
2. **Test passage** — `bd show <id> --json` confirms acceptance criteria met.
3. **No new blockers** — check for newly discovered holes that might block the next phase.

If verification fails, the script halts and reports which tasks/holes need attention. This prevents cascading failures where Phase 2 builds on broken Phase 1 output.

---

## Orchestrator Integration Example

A complete orchestration script using both tools:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Decompose the spec
spec-decompose docs/spec/auth.md --output beads --orchestrate
echo "Review decompose-plan.md, then press Enter to proceed."
read -r

# 2. Execute the plan (create work items in Beads)
bash decompose-plan.sh

# 3. Start progress reporter in background
progress-report --watch &
REPORTER_PID=$!
trap "kill $REPORTER_PID 2>/dev/null" EXIT

# 4. Execute tasks via orchestration script
bash orchestrate.sh

# 5. Final report
progress-report --trigger "Epic complete"

echo "Done. See docs/progress/ for full history."
```

---

## Orchestration Metadata

Each task's description includes machine-parseable metadata (see [decomposition.md § Annotate](./decomposition.md#step-5-annotate--generate-agent-context-algo-5)) embedded as an HTML comment:

```html
<!-- ORCHESTRATION METADATA
parallel_group: foundation
estimated_tokens: 14800
estimated_wall_minutes: 5-10
produces: ["src/auth/validation.py", "tests/unit/test_validation.py"]
consumes: []
can_run_with: [2, 9]
blocks: [3, 4]
-->
```

This metadata is invisible to humans reading task descriptions but available to orchestrators for scheduling decisions.
