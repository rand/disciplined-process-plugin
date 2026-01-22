# Disciplined Process Plugin

A rigorous, traceable AI-assisted development workflow for Claude Code. Inspired by the [Rue language](https://github.com/rue-language/rue) development process.

**Version:** 2.0.0

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
| 6. Review | Self-review + adversarial review | `/dp:review` |
| 7. Close | Complete task, commit | `/dp:task close` |

See [references/workflow.md](./references/workflow.md) for detailed phase descriptions.

## Commands

| Command | Description |
|---------|-------------|
| `/dp:init` | Initialize project with wizard |
| `/dp:task` | Task tracking (ready, create, show, update, close, discover) |
| `/dp:spec` | Specification management (create, add, link, coverage) |
| `/dp:adr` | Architecture Decision Records (create, list, status, link) |
| `/dp:review` | Run code review (with optional adversarial mode) |
| `/dp:session` | Session management (Chainlink only) |
| `/dp:migrate` | Migrate between task trackers |
| `/dp:trace` | Traceability validation |
| `/dp:help` | Show help and workflow reference |

### Task Commands

```bash
/dp:task ready                          # Show available work
/dp:task create "Fix bug" -t bug        # Create a task
/dp:task show <id>                      # View task details
/dp:task update <id> --status in_progress
/dp:task close <id> --reason "Fixed"
/dp:task discover "Edge case" --from <id>  # File discovered work
/dp:task tree                           # Dependency visualization (Chainlink)
/dp:task blocked                        # Show blocked issues
```

### Session Commands (Chainlink only)

```bash
/dp:session start "Working on auth"     # Start tracked session
/dp:session work <id>                   # Claim task and start timer
/dp:session status                      # Show current session
/dp:session end --notes "Handoff notes" # End session with context
```

### Migration Commands

```bash
/dp:migrate beads-to-chainlink          # Migrate from Beads to Chainlink
/dp:migrate chainlink-to-beads          # Migrate from Chainlink to Beads
/dp:migrate --dry-run                   # Preview without changes
```

### Traceability Commands

```bash
/dp:trace coverage                      # Show spec-to-code coverage
/dp:trace validate                      # Verify all traces resolve
/dp:trace find SPEC-01.03               # Find code implementing spec
```

### Spec Commands

```bash
/dp:spec create 02 "Authentication"     # Create spec section
/dp:spec add 02 "Users MUST authenticate before access"
/dp:spec coverage                       # Check trace coverage
/dp:spec list                           # List all specs
```

### ADR Commands

```bash
/dp:adr create "Use JWT for authentication"
/dp:adr list                            # List all ADRs
/dp:adr status 0001 accepted            # Update ADR status
/dp:adr link 0001 SPEC-05.12            # Link ADR to spec/task
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
| **Chainlink** (recommended) | `chainlink` CLI | Sessions, milestones, time tracking, dependencies |
| **Beads** | Git, `bd` CLI | Git-backed, distributed, offline-first |
| **GitHub Issues** | `gh` CLI | Team collaboration, web UI |
| **Linear** | `linear` CLI | Native priorities, projects |
| **Markdown** | None | No dependencies, human-readable |
| **None** | None | External tracking |

See [commands/task.md](./commands/task.md) for the full feature matrix and provider details.

### Adversarial Review

Enable VDD-style adversarial code review with a fresh-context model:

```bash
/dp:review --adversarial               # Run adversarial review
/dp:review --adversarial --max-iterations 3
```

The adversarial reviewer (Sarcasmotron) uses Gemini with fresh context to:
- Detect hallucinations (invalid line numbers, missing functions)
- Find logic errors and edge cases
- Challenge assumptions
- Iterate until issues are resolved or accepted

See [commands/review.md](./commands/review.md) for configuration options.

### Project Structure After Init

```
project/
├── .claude/
│   ├── dp-config.yaml      # Plugin configuration
│   ├── settings.json       # Hooks configuration
│   ├── rules/              # Language-specific rules
│   │   ├── python.md
│   │   └── typescript.md
│   └── traceability/       # Auto-generated trace index
│       └── index.json
├── docs/
│   ├── spec/               # Specifications
│   │   └── 00-overview.md
│   └── adr/                # Architecture Decision Records
│       ├── template.md
│       └── 0001-adopt-disciplined-process.md
├── CLAUDE.md               # Project context for Claude
├── .chainlink/             # Task tracker (if using Chainlink)
└── .beads/                 # Task tracker (if using Beads)
```

### Configuration File

Full `dp-config.yaml` example:

```yaml
version: "2.0"

project:
  name: "my-project"
  languages:
    - typescript
    - python

# Issue tracker selection
task_tracker: chainlink  # chainlink | beads | github | linear | markdown | none

# Chainlink-specific configuration
chainlink:
  features:
    sessions: true
    milestones: true
    time_tracking: true
  rules_path: .claude/rules/

# Beads-specific configuration (when task_tracker: beads)
beads:
  auto_sync: true
  daemon: true

# Enforcement level
enforcement: guided  # strict | guided | minimal

# Adversarial review configuration
adversarial_review:
  enabled: true
  model: gemini-2.5-flash
  max_iterations: 5

# Spec configuration
specs:
  directory: docs/spec/
  id_format: "SPEC-{section:02d}.{item:02d}"

# ADR configuration
adrs:
  directory: docs/adr/
  template: .claude/templates/adr.md

# Degradation behavior
degradation:
  on_tracker_unavailable: warn  # warn | skip | fail
  on_hook_failure: warn
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
- **Chainlink**: `chainlink --version` (requires `.chainlink/` initialized)
- **Beads**: `bd --version` (requires git repo with `.beads/`)
- **GitHub**: `gh auth status`
- **Linear**: `linear --version`

### Adversarial review not working

- Ensure `adversarial_review.enabled: true` in dp-config.yaml
- Check that Gemini API access is configured in rlm-claude-code
- Use `/dp:status` to check component health

### Migration issues

- Use `--dry-run` first to preview changes
- Check `.claude/dp-migration-map.json` for ID mappings after migration
- Spec references are updated automatically

## More Information

- [Commands Reference](./commands/)
- [Skills Reference](./skills/)
- [Workflow Reference](./references/workflow.md)
- [Enforcement Config](./references/enforcement-config.md)
- [Adversarial Review](./commands/review.md)
- [Migration Guide](./commands/migrate.md)
