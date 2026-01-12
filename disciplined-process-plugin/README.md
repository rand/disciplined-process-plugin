# Disciplined Process Plugin

A rigorous, traceable AI-assisted development workflow for Claude Code. Inspired by the [Rue language](https://github.com/rue-language/rue) development process.

See the [project README](../README.md) for overview and installation.

## The Workflow

A 7-phase loop: **Orient → Specify → Decide → Test → Implement → Review → Close**

| Phase | Action | Command |
|-------|--------|---------|
| 1. Orient | Find and claim work | `/dp:task ready` |
| 2. Specify | Write requirements with `[SPEC-XX.YY]` IDs | `/dp:spec add` |
| 3. Decide | Record architectural choices | `/dp:adr create` |
| 4. Test | Write failing tests with `@trace` markers | — |
| 5. Implement | Make tests pass, add `@trace` to code | — |
| 6. Review | Self-review against checklist | `/dp:review` |
| 7. Close | Complete task, commit | `/dp:task close` |

See [references/workflow.md](./references/workflow.md) for detailed phase descriptions.

## Commands

| Command | Description |
|---------|-------------|
| `/dp:init` | Initialize project with interactive wizard |
| `/dp:task` | Task tracking (ready, create, show, update, close) |
| `/dp:spec` | Specification management (create, add, coverage) |
| `/dp:adr` | Architecture Decision Records |
| `/dp:review` | Code review checklist |
| `/dp:help` | Help and workflow reference |

### Task Commands

```bash
/dp:task ready                          # Show available work
/dp:task create "Fix bug" -t bug        # Create a task
/dp:task show bd-a1b2                   # View task details
/dp:task update bd-a1b2 --status in_progress
/dp:task close bd-a1b2 --reason "Fixed"
```

### Spec Commands

```bash
/dp:spec create 02-auth "Authentication"
/dp:spec add 02 "Users MUST authenticate before access"
/dp:spec coverage                       # Check trace coverage
/dp:spec list                           # List all specs
```

### ADR Commands

```bash
/dp:adr create "Use JWT for authentication"
/dp:adr list                            # List all ADRs
/dp:adr status                          # Show ADR statuses
```

## Configuration

### Enforcement Levels

| Level | Behavior |
|-------|----------|
| **Strict** | Hooks block commits without tests/traces |
| **Guided** | Hooks warn but don't block |
| **Minimal** | Skills on demand, no enforcement |

See [references/enforcement-config.md](./references/enforcement-config.md) for per-hook overrides and team recommendations.

### Task Tracking Providers

| Provider | Requirements | Key Features |
|----------|--------------|--------------|
| **Beads** (recommended) | Git, `bd` CLI | Dependencies, offline, discovered-from |
| **GitHub Issues** | `gh` CLI | Team collaboration, web UI |
| **Linear** | `linear` CLI | Native priorities, projects |
| **Markdown** | None | No dependencies, human-readable |
| **None** | None | External tracking |

See [commands/task.md](./commands/task.md) for the full feature matrix and provider details.

### Project Structure After Init

```
project/
├── .claude/
│   ├── dp-config.yaml      # Plugin configuration
│   └── settings.json       # Hooks configuration
├── docs/
│   ├── spec/               # Specifications
│   │   └── 00-overview.md
│   ├── adr/                # Architecture Decision Records
│   │   ├── template.md
│   │   └── 0001-adopt-disciplined-process.md
│   └── process/
│       └── code-review.md
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── e2e/
├── CLAUDE.md               # Project context for Claude
└── .beads/                 # Task tracker (if using Beads)
```

### Configuration File

Full `dp-config.yaml` example:

```yaml
version: "1.0"

project:
  name: "my-project"
  language: "typescript"

tracking:
  provider: "beads"  # beads | github | linear | markdown | none

testing:
  frameworks:
    unit: "vitest"
    integration: "vitest"
    property: "fast-check"
    e2e: "playwright"

enforcement:
  level: "strict"  # strict | guided | minimal

hooks:
  pre_commit:
    - "run_tests"
    - "check_traces"
  post_commit:
    - "sync_tasks"
```

## Skills (Auto-Invoked)

These skills activate automatically based on context:

- **disciplined-workflow**: Core process orchestration
- **spec-tracing**: Specification format and traceability
- **tdd-methodology**: Test-first patterns for all test types
- **adr-authoring**: Decision record format

## Troubleshooting

See the [project README](../README.md) for installation and update issues.

### `/dp:init` fails
- Ensure you're in a valid project directory
- Check write permissions
- Use `/dp:init --force` to overwrite existing files

### Trace markers not found

Trace markers must follow `@trace SPEC-XX.YY` format:

```typescript
// @trace SPEC-01.03
function validateInput(data: string): boolean {
  // ...
}
```

### Provider CLI issues

If task commands fail, check your provider's CLI:
- **Beads**: `bd --version` (requires git repo with `.beads/`)
- **GitHub**: `gh auth status`
- **Linear**: `linear --version`

## More Information

- [Commands Reference](./commands/)
- [Skills Reference](./skills/)
- [Workflow Reference](./references/workflow.md)
- [Enforcement Config](./references/enforcement-config.md)
