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

For any non-trivial work, follow the 7-phase loop:

**Orient → Specify → Decide → Test → Implement → Review → Close**

See `references/workflow.md` for the full workflow reference with commands.

## Workflow Integration

### Starting Work

Before implementing anything:

```bash
# Check what's ready to work on
/dp:task ready

# Claim a task
/dp:task update <task-id> --status in_progress

# Review the task context
/dp:task show <task-id>
```

### During Implementation

When you discover related work:

```bash
# File discovered issues, linked to parent
/dp:task discover "Found: <issue>" --from <parent-id> -p <priority>
```

### Completing Work

```bash
# Run quality gates (tests, lint, build)
# Close the task
/dp:task close <task-id> --reason "Implemented per spec [SPEC-ID]"

# Commit with task reference
git add -A && git commit -m "feat: <description> (<task-id>)"
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

## Related Skills

- **spec-tracing**: Detailed specification format and traceability
- **tdd-methodology**: Test-first patterns for different test types  
- **adr-authoring**: Architecture Decision Record format and process
