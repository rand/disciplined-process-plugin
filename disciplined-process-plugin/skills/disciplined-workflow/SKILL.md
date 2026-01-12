---
name: disciplined-workflow
description: Core orchestration for disciplined AI-assisted development. Auto-invokes when starting new features, implementing tasks, or working on any development that should follow the spec-first, test-driven process. Triggers on task planning, feature implementation, bug fixes, refactoring work, or when beads/bd tasks are referenced.
---

# Disciplined Development Workflow

This skill enforces a rigorous, traceable development process inspired by the Rue language project. Every implementation traces back to specifications, every specification has tests, and every decision is recorded.

## Core Principles

1. **Specification-First**: Write specs before code. Specs define WHAT, not HOW.
2. **Test-Driven**: Tests verify specs are met. Write tests before implementation.
3. **Traceable**: Every line of implementation traces to a spec paragraph.
4. **Documented Decisions**: ADRs capture WHY we chose an approach.
5. **Managed Work**: Tasks tracked with dependencies, ready work identified.

## The Development Loop

For any non-trivial work, follow this sequence:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ORIENT: Check ready work (bd ready), understand context      │
├─────────────────────────────────────────────────────────────────┤
│ 2. SPECIFY: Write/update spec with paragraph IDs                │
├─────────────────────────────────────────────────────────────────┤
│ 3. DECIDE: Create ADR if architectural choice needed            │
├─────────────────────────────────────────────────────────────────┤
│ 4. TEST: Write tests that reference spec paragraph IDs          │
├─────────────────────────────────────────────────────────────────┤
│ 5. IMPLEMENT: Write code, run tests, iterate                    │
├─────────────────────────────────────────────────────────────────┤
│ 6. REVIEW: Self-review against code-review checklist            │
├─────────────────────────────────────────────────────────────────┤
│ 7. CLOSE: Update task status, file discovered work              │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Integration

### Starting Work

Before implementing anything:

```bash
# Check what's ready to work on
bd ready --json

# Claim a task
bd update <task-id> --status in_progress

# Review the task context
bd show <task-id>
```

### During Implementation

When you discover related work:

```bash
# File discovered issues, linked to parent
bd create "Discovered: <issue>" -t <type> -p <priority>
bd dep add <new-id> <parent-id> --type discovered-from
```

### Completing Work

```bash
# Run quality gates (tests, lint, build)
# Close the task
bd close <task-id> --reason "Implemented per spec [SPEC-ID]"

# Export and commit
bd sync
git add -A && git commit -m "feat: <description> (bd-<id>)"
```

## Project Structure

The disciplined process expects this structure:

```
project/
├── CLAUDE.md                    # Project-specific adaptations
├── .claude/
│   └── settings.json            # Hooks and permissions
├── .beads/                      # Task tracking (or alternative)
├── docs/
│   ├── spec/                    # Specifications with paragraph IDs
│   │   ├── 00-overview.md
│   │   ├── 01-<domain>.md
│   │   └── ...
│   ├── adr/                     # Architecture Decision Records
│   │   ├── 0001-<decision>.md
│   │   └── template.md
│   └── process/                 # Process documentation
│       ├── code-review.md
│       └── workflow.md
├── tests/                       # Test suites by type
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── e2e/
└── src/                         # Implementation
```

## Enforcement Modes

This workflow supports three enforcement levels (configured in `.claude/settings.json`):

1. **Strict** (default): Hooks block commits without passing tests and spec references
2. **Guided**: Hooks warn but don't block; skills suggest best practices
3. **Minimal**: Skills available but no enforcement; for exploratory work

See `references/enforcement-config.md` for configuration details.

## Quick Reference

| Phase | Key Actions |
|-------|-------------|
| Orient | `bd ready`, review context, claim task |
| Specify | Create/update spec with `[SPEC-XX.YY]` IDs |
| Decide | Create ADR if needed via `/dp:adr` |
| Test | Write tests with `@trace SPEC-XX.YY` markers |
| Implement | Code until tests pass |
| Review | Run `/dp:review` checklist |
| Close | `bd close`, commit with task ID |

## Related Skills

- **spec-tracing**: Detailed specification format and traceability
- **tdd-methodology**: Test-first patterns for different test types  
- **adr-authoring**: Architecture Decision Record format and process
