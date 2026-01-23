# Disciplined Process Plugin

## Project Overview

Claude Code plugin for enforcing disciplined, traceable AI-assisted development workflows with spec-first development, ADRs, goal-backward verification, and adversarial review.

**Primary Language**: Python
**Domain**: Developer tooling (Claude Code plugin)

## Architecture

```
disciplined-process-plugin/
├── commands/           # /dp:* command definitions (markdown)
├── scripts/            # Hook implementations (Python)
│   └── lib/            # Core library (tested)
│       ├── config.py       # Configuration v1/v2 with migration
│       ├── degradation.py  # Graceful degradation framework
│       ├── providers.py    # Task tracker detection
│       ├── verification.py # Goal-backward verification
│       ├── plan_validation.py
│       ├── builtin_provider.py
│       └── traceability.py
├── docs/
│   ├── spec/           # Specifications [SPEC-XX.YY]
│   └── adr/            # Architecture Decision Records
├── agents/             # Agent definitions (adversary.md)
├── skills/             # Skill definitions
├── assets/templates/   # Project templates
└── tests/              # Pytest + Hypothesis
```

## Key Commands

```bash
# Test (all)
cd disciplined-process-plugin && source .venv/bin/activate && pytest tests/ -v

# Test (with coverage)
cd disciplined-process-plugin && source .venv/bin/activate && pytest tests/ --cov=scripts

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
- `05-verification.md` - Goal-backward verification system
- `06-plan-validation.md` - Pre-execution plan validation

**Missing** (tracked in beads):
- SPEC-01: Task Tracking
- SPEC-02: Specifications and Traceability
- SPEC-03: Architecture Decision Records
- SPEC-04: Code Review

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
| Hook scripts | - | - | Needs tests (0% coverage) |

**Current Status**: 197 tests passing, 33% overall coverage.
Hook scripts (pre_commit, session_start, etc.) have 0% coverage and need tests.

## Important Notes

- **Graceful Degradation**: Plugin never blocks on errors; degrades gracefully
- **Provider Support**: Beads (primary), Builtin, Chainlink, GitHub, Linear, Markdown, None
- **Python Version**: 3.12+
- **Dependencies**: See `pyproject.toml` (hypothesis, pytest, etc.)

---

> **Note**: This project dogfoods its own plugin. The `.claude/dp-config.yaml` configures Beads as the task tracker.
