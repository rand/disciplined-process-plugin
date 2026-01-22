---
description: Show help and workflow reference
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

Diagnostics:
  /dp:health    Show system health and component status
  /dp:status    Show current degradation level
  /dp:repair    Attempt automatic repair of issues
  /dp:reset     Reset degradation to full mode
  /dp:unlock    Unlock degradation level

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
```

Displays the full 7-phase workflow from `references/workflow.md`:

**Orient → Specify → Decide → Test → Implement → Review → Close**

| Phase | Key Action |
|-------|------------|
| Orient | `/dp:task ready`, claim task |
| Specify | Add `[SPEC-XX.YY]` requirements |
| Decide | Create ADR if needed |
| Test | Write tests with `@trace` markers |
| Implement | Code until tests pass |
| Review | `/dp:review` checklist |
| Close | `/dp:task close`, commit |

## Quick Reference

```
/dp:help quick
```

| Action | Command |
|--------|---------|
| Find work | `/dp:task ready` |
| Claim task | `/dp:task update <id> --status in_progress` |
| Add requirement | `/dp:spec add <section> "<requirement>"` |
| Create ADR | `/dp:adr create "<title>"` |
| Check coverage | `/dp:spec coverage` |
| Review changes | `/dp:review --staged` |
| Complete task | `/dp:task close <id> --reason "Done"` |
| File discovered work | `/dp:task discover "<issue>" --from <id>` |
