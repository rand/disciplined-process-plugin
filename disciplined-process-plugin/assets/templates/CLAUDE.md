# {Project Name}

## Project Overview

{Brief description of the project - 1-2 sentences}

**Primary Language**: {language}  
**Domain**: {domain - e.g., compiler, web app, CLI tool, library}

## Architecture

{High-level architecture overview. Key components and their relationships.}

## Key Commands

```bash
# Build
{build-command}

# Test (all)
{test-command}

# Test (unit only)
{unit-test-command}

# Lint
{lint-command}

# Format
{format-command}
```

## Development Workflow

This project uses the **disciplined process** workflow:

1. **Orient**: Check ready work with `bd ready`
2. **Specify**: Update specs in `docs/spec/` with `[SPEC-XX.YY]` IDs
3. **Decide**: Create ADRs in `docs/adr/` for architectural choices
4. **Test**: Write tests first with `@trace SPEC-XX.YY` markers
5. **Implement**: Write minimal code to pass tests
6. **Review**: Run `/dp:review` before committing
7. **Close**: Close task and commit with task ID

## Specifications

Specifications are in `docs/spec/`:
- `00-overview.md` - Meta-specification and terminology
- {List other spec sections as they're created}

Every implementation file should have `@trace SPEC-XX.YY` comments linking to specs.

## Architecture Decisions

ADRs are in `docs/adr/`:
- `0001-adopt-disciplined-process.md` - Workflow adoption
- {List other ADRs as they're created}

## Testing Strategy

| Type | Framework | Location | Marker |
|------|-----------|----------|--------|
| Unit | {framework} | `tests/unit/` | `@trace SPEC-XX.YY` |
| Integration | {framework} | `tests/integration/` | `@trace SPEC-XX.YY` |
| Property | {framework} | `tests/property/` | `@trace SPEC-XX.YY` |
| E2E | {framework} | `tests/e2e/` | `@trace SPEC-XX.YY` |

## Important Directories

```
{project}/
├── docs/
│   ├── spec/           # Specifications
│   ├── adr/            # Architecture Decision Records
│   └── process/        # Workflow documentation
├── src/                # Source code
├── tests/              # Test suites
└── .claude/            # Claude Code configuration
```

## Domain-Specific Guidance

{Add project-specific guidance here:
- Key abstractions and their purpose
- Common patterns used
- Things to watch out for
- Performance-sensitive areas
- External dependencies and how to work with them}

## Task Tracking

This project uses **{provider}** for task tracking.

```bash
# See ready work
bd ready

# Claim a task
bd update <id> --status in_progress

# File discovered work
bd create "Found issue" -t bug -p 2
bd dep add <new-id> <current-id> --type discovered-from

# Complete work
bd close <id> --reason "Implemented per SPEC-XX.YY"
```

---

> **Note**: Keep this file updated as the project evolves. It's loaded at the start of every Claude session.
