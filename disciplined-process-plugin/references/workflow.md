# Disciplined Development Workflow

The canonical reference for the 7-phase development loop.

## The Loop

```
┌─────────────────────────────────────────────────────────────┐
│ 0. SESSION  → Start tracked session (Chainlink only)        │
│    /dp:session start "Working on feature X"                 │
├─────────────────────────────────────────────────────────────┤
│ 1. ORIENT   → Check ready work, claim a task                │
│    /dp:task ready                                           │
│    /dp:task update <id> --status in_progress                │
│    /dp:session work <id>  (Chainlink: claim + start timer)  │
├─────────────────────────────────────────────────────────────┤
│ 2. SPECIFY  → Write/update spec with [SPEC-XX.YY] IDs       │
│    /dp:spec create <section> "<title>"                      │
│    /dp:spec add <section> "<requirement>"                   │
│    /dp:spec link <spec-id> <issue-id>                       │
├─────────────────────────────────────────────────────────────┤
│ 3. DECIDE   → Create ADR if architectural choice needed     │
│    /dp:adr create "<decision title>"                        │
├─────────────────────────────────────────────────────────────┤
│ 4. TEST     → Write tests with @trace SPEC-XX.YY markers    │
│    Tests should FAIL initially (red phase)                  │
├─────────────────────────────────────────────────────────────┤
│ 5. IMPLEMENT → Write minimal code to pass tests             │
│    Add @trace SPEC-XX.YY comments to implementation         │
├─────────────────────────────────────────────────────────────┤
│ 6. REVIEW   → Run /dp:review + adversarial review           │
│    /dp:review                     (standard checklist)      │
│    /dp:review --adversarial       (VDD-style deep review)   │
│    /dp:trace coverage             (verify spec coverage)    │
├─────────────────────────────────────────────────────────────┤
│ 7. CLOSE    → Complete task, commit with ID                 │
│    /dp:task close <id> --reason "Done"                      │
│    git commit -m "feat: <desc> (<task-id>)"                 │
│    /dp:session end --notes "Handoff context"  (Chainlink)   │
└─────────────────────────────────────────────────────────────┘
```

## Phase Details

### 0. Session (Chainlink only)

Start a tracked work session:
- `/dp:session start "Description"` to begin session
- Sessions preserve context across Claude Code restarts
- Handoff notes help future sessions pick up where you left off

### 1. Orient

Before starting any work:
- Run `/dp:task ready` to see available work (no blockers)
- Review task context with `/dp:task show <id>`
- Claim with `/dp:task update <id> --status in_progress`
- Or use `/dp:session work <id>` (Chainlink) to claim and start timer

Check for blocked work:
- `/dp:task blocked` shows issues waiting on dependencies
- `/dp:task tree` visualizes dependency graph (Chainlink)

### 2. Specify

Define WHAT, not HOW:
- Create specs with traceable paragraph IDs: `[SPEC-XX.YY]`
- Each requirement is a single, testable statement
- Use `/dp:spec create` and `/dp:spec add`
- Link specs to issues: `/dp:spec link SPEC-01.03 <issue-id>`

### 3. Decide

For architectural choices:
- Create an ADR with `/dp:adr create "<title>"`
- Document context, options considered, decision, consequences
- Link ADR to relevant specs

### 4. Test

Write tests BEFORE implementation:
- Add `@trace SPEC-XX.YY` markers linking to specs
- Tests should FAIL initially (red phase)
- Cover unit, integration, property, and e2e as appropriate

### 5. Implement

Write minimal code:
- Make tests pass (green phase)
- Add `@trace SPEC-XX.YY` comments to implementation
- Refactor while keeping tests green
- Post-edit hooks auto-format and update traceability index

### 6. Review

Self-review with `/dp:review`:
- Fix all blocking issues before commit
- File non-blocking issues as tasks for later
- Verify spec coverage with `/dp:trace coverage`

Adversarial review with `/dp:review --adversarial`:
- Fresh-context Gemini review (VDD-style)
- Detects hallucinations, logic errors, edge cases
- Iterates until issues resolved or explicitly accepted

### 7. Close

Complete the work:
- Close task: `/dp:task close <id> --reason "<reason>"`
- Commit with task reference: `git commit -m "feat: <desc> (<task-id>)"`
- File any discovered work: `/dp:task discover "<title>" --from <id>`
- End session: `/dp:session end --notes "Handoff context"` (Chainlink)

## Quick Reference

| Phase | Command | Purpose |
|-------|---------|---------|
| Session | `/dp:session start "desc"` | Start tracked session (Chainlink) |
| Orient | `/dp:task ready` | Find available work |
| Orient | `/dp:task update <id> --status in_progress` | Claim task |
| Orient | `/dp:session work <id>` | Claim + start timer (Chainlink) |
| Specify | `/dp:spec add <section> "<req>"` | Add requirement |
| Specify | `/dp:spec link <spec> <issue>` | Link spec to issue |
| Decide | `/dp:adr create "<title>"` | Record decision |
| Test | Write tests with `@trace SPEC-XX.YY` | Verify specs |
| Implement | Code with `@trace SPEC-XX.YY` | Fulfill specs |
| Review | `/dp:review` | Standard checklist |
| Review | `/dp:review --adversarial` | VDD-style deep review |
| Review | `/dp:trace coverage` | Verify spec coverage |
| Close | `/dp:task close <id>` | Complete work |
| Close | `/dp:session end --notes "..."` | Save handoff context (Chainlink) |

## Traceability

The `@trace` marker links code to specifications:

```python
# @trace SPEC-01.03
def validate_input(data: str) -> bool:
    """Validates input per SPEC-01.03 requirements."""
    ...
```

Commands:
- `/dp:trace coverage` — Show which specs have code coverage
- `/dp:trace validate` — Verify all @trace markers resolve to real specs
- `/dp:trace find SPEC-01.03` — Find code implementing a spec

## Migration

Moving between task trackers:
- `/dp:migrate beads-to-chainlink` — Migrate Beads → Chainlink
- `/dp:migrate chainlink-to-beads` — Migrate Chainlink → Beads
- `/dp:migrate --dry-run` — Preview changes without applying

Migration preserves:
- Issue content (title, description, status)
- Dependencies and relationships
- Spec references (auto-updated to new IDs)
