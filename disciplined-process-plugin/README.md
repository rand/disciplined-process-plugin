# Disciplined Process Plugin

A rigorous, traceable AI-assisted development workflow for Claude Code.

## Why Use This?

AI coding assistants are powerful but can produce inconsistent results. This plugin brings discipline to AI-assisted development by enforcing a proven workflow:

- **Specify before you code** — Write requirements with traceable IDs before implementation
- **Test before you implement** — Tests reference specs and must exist before code
- **Document decisions** — Architecture Decision Records capture the "why"
- **Track dependencies** — Know what's ready to work on and what's blocked
- **Enforce or guide** — Strict mode blocks bad commits; guided mode just warns

Inspired by the [Rue language](https://github.com/rue-language/rue) development process.

## Features

- **Specification-first**: Write specs before code, with traceable paragraph IDs (`[SPEC-01.03]`)
- **Test-driven**: Tests reference specs via `@trace` markers, run before implementation
- **ADRs**: Document architectural decisions systematically
- **Task tracking**: Dependency-aware work management (Beads default, or GitHub/Linear/Markdown)
- **Traceability**: Every line links to specs — know why code exists
- **Enforcement**: Configurable hooks enforce the process (strict), warn (guided), or stay out of the way (minimal)

## The Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ORIENT   → Check ready work, claim a task                │
│    /dp:task ready                                           │
│    /dp:task update <id> --status in_progress                │
├─────────────────────────────────────────────────────────────┤
│ 2. SPECIFY  → Write/update spec with [SPEC-XX.YY] IDs       │
│    /dp:spec create <section> "<title>"                      │
│    /dp:spec add <section> "<requirement>"                   │
├─────────────────────────────────────────────────────────────┤
│ 3. DECIDE   → Create ADR if architectural choice needed     │
│    /dp:adr create "<decision title>"                        │
├─────────────────────────────────────────────────────────────┤
│ 4. TEST     → Write tests with @trace SPEC-XX.YY markers    │
│    Tests should FAIL initially (red phase)                  │
├─────────────────────────────────────────────────────────────┤
│ 5. IMPLEMENT → Write minimal code to pass tests             │
│    Add @trace SPEC-XX.YY comments to implementation         │
├─────────────────────────────────────────────────────────────┤
│ 6. REVIEW   → Run /dp:review checklist                      │
│    Fix blocking issues, file non-blocking as tasks          │
├─────────────────────────────────────────────────────────────┤
│ 7. CLOSE    → Complete task, commit with ID                 │
│    /dp:task close <id> --reason "Done"                      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Add the plugin repository
/plugin marketplace add rand/disciplined-process-plugin

# 2. Install the plugin
/plugin install disciplined-process@disciplined-process-plugin

# 3. Initialize your project (interactive wizard)
/dp:init

# 4. Start working
/dp:task ready
```

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

## Installation

### Prerequisites

- **Claude Code** version 2.0.0 or higher
- **Git** (required for Beads task tracking)
- For GitHub Issues: `gh` CLI installed and authenticated
- For Linear: `linear` CLI installed and authenticated

### Step-by-Step

1. **Add the plugin repository:**
   ```bash
   /plugin marketplace add rand/disciplined-process-plugin
   ```

2. **Install the plugin:**
   ```bash
   /plugin install disciplined-process@disciplined-process-plugin
   ```

3. **Verify installation:**
   ```bash
   /plugin list
   ```
   You should see `disciplined-process` listed.

4. **Initialize your project:**
   ```bash
   /dp:init
   ```
   The wizard configures language, task tracking, test frameworks, and enforcement level.

5. **Validate setup:**
   ```bash
   /dp:help                      # Should show command reference
   cat .claude/dp-config.yaml    # Should show your configuration
   ```

## Configuration

### Enforcement Levels

| Level | Behavior |
|-------|----------|
| **Strict** | Hooks block commits without tests/traces |
| **Guided** | Hooks warn but don't block |
| **Minimal** | Skills on demand, no enforcement |

### Task Tracking Providers

| Provider | Description | Requirements |
|----------|-------------|--------------|
| **Beads** (default) | Git-backed, dependency-aware | Git |
| **GitHub Issues** | GitHub issue integration | `gh` CLI |
| **Linear** | Linear app integration | `linear` CLI |
| **Markdown** | Plain files in `docs/tasks/` | None |
| **None** | Skip task tracking | None |

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

## Updating

```bash
/plugin marketplace update rand/disciplined-process-plugin
/plugin update disciplined-process@disciplined-process-plugin
```

Check for updates: `/plugin outdated`

## Uninstalling

```bash
/plugin uninstall disciplined-process@disciplined-process-plugin
/plugin marketplace remove rand/disciplined-process-plugin
```

To fully clean up project files:
```bash
rm -rf .claude/dp-config.yaml docs/spec docs/adr docs/process tests/ CLAUDE.md .beads/
```

## Troubleshooting

### Commands not recognized
1. Verify installation: `/plugin list`
2. Restart Claude Code
3. Reinstall the plugin

### `/dp:init` fails
- Ensure you're in a valid project directory
- Check write permissions
- Use `/dp:init --force` to overwrite existing files

### Hooks not triggering
1. Check enforcement level isn't "minimal"
2. Verify `.claude/settings.json` exists
3. Run `chmod +x .claude/scripts/*.sh`

### Beads commands fail
1. Ensure Git is initialized: `git status`
2. Check `.beads/` directory exists
3. Run `bd init` manually

### Trace markers not found

Trace markers must follow `@trace SPEC-XX.YY` format:

```typescript
// @trace SPEC-01.03
function validateInput(data: string): boolean {
  // ...
}
```

## License

MIT

## Support

- [Commands Documentation](./commands/)
- [Skills Documentation](./skills/)
- [GitHub Issues](https://github.com/rand/disciplined-process-plugin/issues)
- [Discussions](https://github.com/rand/disciplined-process-plugin/discussions)
