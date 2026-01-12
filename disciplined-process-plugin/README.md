# Disciplined Process Plugin

A rigorous, traceable AI-assisted development workflow for Claude Code.

Inspired by the [Rue language](https://github.com/rue-language/rue) development process, this plugin enforces specification-first, test-driven development with full traceability.

## Features

- **Specification-first**: Write specs before code, with traceable paragraph IDs
- **Test-driven**: Tests reference specs, run before implementation
- **ADRs**: Document architectural decisions systematically
- **Task tracking**: Dependency-aware work management (Beads default, pluggable)
- **Traceability**: Every line links to specs via `@trace` markers
- **Enforcement**: Configurable hooks enforce the process (or just guide)

## Installation

```bash
# Add the marketplace
/plugin marketplace add rand/disciplined-process-marketplace

# Install the plugin
/plugin install disciplined-process@disciplined-process-marketplace
```

## Quick Start

```bash
# Initialize in your project
/dp:init

# Follow the interactive wizard to configure:
# - Project language and frameworks
# - Task tracking provider
# - Enforcement level
```

## The Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ORIENT   → Check ready work, claim a task                │
├─────────────────────────────────────────────────────────────┤
│ 2. SPECIFY  → Write/update spec with [SPEC-XX.YY] IDs       │
├─────────────────────────────────────────────────────────────┤
│ 3. DECIDE   → Create ADR if architectural choice needed     │
├─────────────────────────────────────────────────────────────┤
│ 4. TEST     → Write tests with @trace SPEC-XX.YY markers    │
├─────────────────────────────────────────────────────────────┤
│ 5. IMPLEMENT → Write minimal code to pass tests             │
├─────────────────────────────────────────────────────────────┤
│ 6. REVIEW   → Run /dp:review checklist                      │
├─────────────────────────────────────────────────────────────┤
│ 7. CLOSE    → Complete task, commit with ID                 │
└─────────────────────────────────────────────────────────────┘
```

## Commands

| Command | Description |
|---------|-------------|
| `/dp:init` | Initialize project with wizard |
| `/dp:task` | Task tracking (ready, create, show, update, close) |
| `/dp:spec` | Specification management (create, add, coverage) |
| `/dp:adr` | Architecture Decision Records |
| `/dp:review` | Code review checklist |
| `/dp:help` | Help and workflow reference |

## Skills (Auto-Invoked)

- **disciplined-workflow**: Core process orchestration
- **spec-tracing**: Specification format and traceability
- **tdd-methodology**: Test-first patterns for all test types
- **adr-authoring**: Decision record format

## Enforcement Levels

| Level | Behavior |
|-------|----------|
| **Strict** | Hooks block commits without tests/traces |
| **Guided** | Hooks warn but don't block |
| **Minimal** | Skills on demand, no enforcement |

Configure in `.claude/dp-config.yaml`.

## Task Tracking Providers

- **Beads** (default): Git-backed, dependency-aware
- **GitHub Issues**: Via `gh` CLI
- **Linear**: Via `linear` CLI  
- **Markdown**: Plain files in `docs/tasks/`
- **None**: Skip tracking

## Project Structure

After initialization:

```
project/
├── .claude/
│   ├── dp-config.yaml      # Configuration
│   └── settings.json       # Hooks
├── docs/
│   ├── spec/               # Specifications
│   │   └── 00-overview.md
│   ├── adr/                # Decision records
│   │   ├── template.md
│   │   └── 0001-adopt-disciplined-process.md
│   └── process/            # Workflow docs
│       └── code-review.md
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── e2e/
├── CLAUDE.md               # Project context
└── .beads/                 # If using Beads
```

## License

MIT
