# Disciplined Process Plugin

## Project Overview

Claude Code plugin for enforcing disciplined, traceable AI-assisted development workflows with spec-first development, ADRs, goal-backward verification, and adversarial review.

**Primary Language**: Python
**Domain**: Developer tooling (Claude Code plugin)

## Architecture

```
disciplined-process-plugin/
├── commands/           # /dp:* command definitions (17 markdown files)
├── scripts/            # Hook implementations (Python)
│   ├── lib/            # Core library (tested)
│   │   ├── config.py       # Configuration v1/v2 with migration
│   │   ├── degradation.py  # Graceful degradation framework
│   │   ├── providers.py    # Task tracker detection
│   │   ├── verification.py # Goal-backward verification
│   │   ├── plan_validation.py
│   │   ├── builtin_provider.py
│   │   └── traceability.py
│   ├── events/         # Cross-plugin event emission/consumption
│   └── legacy/         # v1 Python hooks (preserved)
├── tools/              # CLI tools
│   ├── spec_decompose/ # Spec decomposition engine
│   ├── progress_report/# Progress reporting tool
│   └── shared/         # Shared utilities
├── bin/                # Pre-compiled Go binaries (cross-platform)
├── cmd/                # Go source for binaries
├── docs/
│   ├── spec/           # Specifications [SPEC-XX.YY]
│   └── adr/            # Architecture Decision Records
├── agents/             # Agent definitions (3 agents)
├── skills/             # Skill definitions (5 skills)
├── schemas/            # JSON schemas for events
├── references/         # Workflow and config guides
├── assets/templates/   # Project templates
└── tests/              # Pytest + Hypothesis
```

## Key Commands

```bash
# Test (all)
cd disciplined-process-plugin && source .venv/bin/activate && pytest tests/ -v

# Test (with coverage)
cd disciplined-process-plugin && source .venv/bin/activate && pytest tests/ --cov=scripts --cov=tools

# Lint
ruff check disciplined-process-plugin/

# Type check
mypy disciplined-process-plugin/scripts/
```

## Development Workflow

This project uses the **disciplined process** workflow (dogfooding):

1. **Orient**: Check ready work with `bd ready`
2. **Specify**: Update specs in `docs/spec/` with `[SPEC-XX.YY]` IDs
3. **Decide**: Create ADRs in `docs/adr/` for architectural choices
4. **Test**: Write tests first with `@trace SPEC-XX.YY` markers
5. **Implement**: Write minimal code to pass tests
6. **Review**: Verify tests pass before committing
7. **Close**: Close task with `bd close <id>`

## Specifications

Specifications are in `disciplined-process-plugin/docs/spec/`:
- `00-overview.md` - Meta-specification and terminology
- `01-task-tracking.md` - Task tracking integration
- `02-specifications.md` - Specification format and traceability
- `03-architecture-decisions.md` - ADR system
- `04-code-review.md` - Code review requirements
- `05-verification.md` - Goal-backward verification system
- `06-plan-validation.md` - Pre-execution plan validation
- `07-spec-decomposition.md` - Spec decomposition into dependency-aware work items
- `08-progress-reporting.md` - Structured progress reporting and broadcasting

## Task Tracking

This project uses **Beads** (`bd`) for task tracking.

```bash
# See ready work
bd ready

# Claim a task
bd update <id> --status in_progress

# Complete work
bd close <id>

# Sync with git
bd sync
```

## Testing Strategy

| Type | Framework | Location | Coverage |
|------|-----------|----------|----------|
| Unit | pytest | `tests/` | Core lib well-tested |
| Property | hypothesis | `tests/` | Traceability, config |
| Hook scripts | pytest | `tests/` | spec-info.py tested (23 tests) |

**Current Status**: 776 tests passing.
Hook scripts partially tested (spec-info.py has full coverage; others need tests).

## Important Notes

- **Graceful Degradation**: Plugin never blocks on errors; degrades gracefully
- **Provider Support**: Beads (primary), Builtin, Chainlink, GitHub, Linear, Markdown, None
- **Python Version**: 3.10+
- **Dependencies**: See `pyproject.toml` (hypothesis, pytest, etc.)

---

> **Note**: This project dogfoods its own plugin. The `.claude/dp-config.yaml` configures Beads as the task tracker.
