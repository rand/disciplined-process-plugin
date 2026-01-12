---
description: Show help for disciplined process commands and workflow.
argument-hint: [command]
---

# Help Command

Display help for the disciplined process plugin.

## Without Arguments

Show overview of all commands:

```
Disciplined Process Plugin v1.0
================================

A rigorous, traceable development workflow.

Commands:
  /dp:init      Initialize project with disciplined process
  /dp:task      Task tracking (ready, create, show, update, close)
  /dp:spec      Specification management (create, add, coverage, list)
  /dp:adr       Architecture Decision Records (create, list, status)
  /dp:review    Run code review checklist

Workflow:
  1. Orient    → /dp:task ready
  2. Specify   → /dp:spec add <section> "<requirement>"
  3. Decide    → /dp:adr create "<decision>"
  4. Test      → Write tests with @trace SPEC-XX.YY
  5. Implement → Code until tests pass
  6. Review    → /dp:review
  7. Close     → /dp:task close <id>

Skills (auto-invoked):
  • disciplined-workflow  - Core process orchestration
  • spec-tracing          - Specification format
  • tdd-methodology       - Test-driven development
  • adr-authoring         - Decision record format

Run '/dp:help <command>' for detailed help.
```

## With Command Argument

Show detailed help for specific command:

```
/dp:help task

Task Command
============

Unified interface for task tracking.

Subcommands:
  ready   - Show tasks with no blockers
  create  - Create a new task
  show    - Display task details
  update  - Update task fields
  close   - Close completed task
  discover - Create linked discovered task

Examples:
  /dp:task ready
  /dp:task create "Implement feature" -t task -p 1
  /dp:task update bd-a1b2 --status in_progress
  /dp:task close bd-a1b2 --reason "Done"

Provider: (see dp-config.yaml)
```

## Workflow Reference

```
/dp:help workflow

Disciplined Development Workflow
================================

┌─────────────────────────────────────────────────────────────┐
│ ORIENT                                                       │
│   Check ready work, understand context, claim task           │
│   → /dp:task ready                                           │
│   → /dp:task update <id> --status in_progress               │
├─────────────────────────────────────────────────────────────┤
│ SPECIFY                                                      │
│   Write/update spec with paragraph IDs [SPEC-XX.YY]         │
│   → /dp:spec create <section> <title>                       │
│   → /dp:spec add <section> "<requirement>"                  │
├─────────────────────────────────────────────────────────────┤
│ DECIDE                                                       │
│   Create ADR if architectural choice needed                  │
│   → /dp:adr create "<decision title>"                       │
├─────────────────────────────────────────────────────────────┤
│ TEST                                                         │
│   Write tests referencing spec paragraph IDs                 │
│   Add @trace SPEC-XX.YY markers to tests                    │
│   Run tests: they should FAIL (red phase)                   │
├─────────────────────────────────────────────────────────────┤
│ IMPLEMENT                                                    │
│   Write minimal code to pass tests (green phase)            │
│   Add @trace SPEC-XX.YY comments to implementation          │
│   Refactor while keeping tests green                        │
├─────────────────────────────────────────────────────────────┤
│ REVIEW                                                       │
│   Self-review against checklist                             │
│   → /dp:review                                              │
│   Fix blocking issues, file non-blocking as tasks           │
├─────────────────────────────────────────────────────────────┤
│ CLOSE                                                        │
│   Update task, commit with task ID                          │
│   → /dp:task close <id> --reason "<reason>"                 │
│   → git commit -m "feat: <desc> (bd-<id>)"                  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Reference

```
/dp:help quick

Quick Reference
===============

Start work:
  /dp:task ready              # Find work
  /dp:task update X --status in_progress

Add spec:
  /dp:spec add 03 "X MUST do Y"

Create ADR:
  /dp:adr create "Use X for Y"

Check coverage:
  /dp:spec coverage

Review changes:
  /dp:review --staged

Complete task:
  /dp:task close X --reason "Done"

File discovered work:
  /dp:task discover "Found issue" --from X
```
