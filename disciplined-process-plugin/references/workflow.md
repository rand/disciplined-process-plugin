# Disciplined Development Workflow

The canonical reference for the 7-phase development loop.

## The Loop

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ORIENT   → Check ready work, claim a task                │
│    /dp:task ready                                           │
│    /dp:task update <id> --status in_progress                │
├─────────────────────────────────────────────────────────────┤
│ 2. SPECIFY  → Write/update spec with [SPEC-XX.YY] IDs       │
│    /dp:spec create <section> "<title>"                      │
│    /dp:spec add <section> "<requirement>"                   │
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
│ 6. REVIEW   → Run /dp:review checklist                      │
│    Fix blocking issues, file non-blocking as tasks          │
├─────────────────────────────────────────────────────────────┤
│ 7. CLOSE    → Complete task, commit with ID                 │
│    /dp:task close <id> --reason "Done"                      │
│    git commit -m "feat: <desc> (<task-id>)"                 │
└─────────────────────────────────────────────────────────────┘
```

## Phase Details

### 1. Orient

Before starting any work:
- Run `/dp:task ready` to see available work
- Review task context with `/dp:task show <id>`
- Claim with `/dp:task update <id> --status in_progress`

### 2. Specify

Define WHAT, not HOW:
- Create specs with traceable paragraph IDs: `[SPEC-XX.YY]`
- Each requirement is a single, testable statement
- Use `/dp:spec create` and `/dp:spec add`

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

### 6. Review

Self-review with `/dp:review`:
- Fix all blocking issues before commit
- File non-blocking issues as tasks for later
- Verify spec coverage with `/dp:spec coverage`

### 7. Close

Complete the work:
- Close task: `/dp:task close <id> --reason "<reason>"`
- Commit with task reference: `git commit -m "feat: <desc> (<task-id>)"`
- File any discovered work: `/dp:task discover "<title>" --from <id>`

## Quick Reference

| Phase | Command | Purpose |
|-------|---------|---------|
| Orient | `/dp:task ready` | Find available work |
| Orient | `/dp:task update <id> --status in_progress` | Claim task |
| Specify | `/dp:spec add <section> "<req>"` | Add requirement |
| Decide | `/dp:adr create "<title>"` | Record decision |
| Test | Write tests with `@trace SPEC-XX.YY` | Verify specs |
| Implement | Code with `@trace SPEC-XX.YY` | Fulfill specs |
| Review | `/dp:review` | Quality check |
| Close | `/dp:task close <id>` | Complete work |
