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

## Prerequisites

- **Claude Code** version 2.0.0 or higher
- **Git** (required for Beads task tracking)
- For GitHub Issues: `gh` CLI installed and authenticated
- For Linear: `linear` CLI installed and authenticated

## Installation

### Step 1: Add the Plugin Repository

```bash
/plugin marketplace add rand/disciplined-process-plugin
```

### Step 2: Install the Plugin

```bash
/plugin install disciplined-process@disciplined-process-plugin
```

### Step 3: Verify Installation

```bash
/plugin list
```

You should see `disciplined-process` listed.

## Quick Start

### Initialize Your Project

```bash
/dp:init
```

The interactive wizard will guide you through:
1. **Project basics** - Name and language detection
2. **Task tracking** - Choose Beads (recommended), GitHub Issues, Linear, Markdown, or None
3. **Test frameworks** - Configure unit, integration, property, and e2e tests
4. **Enforcement level** - Strict, Guided, or Minimal

### Validate Setup

After initialization, confirm everything is working:

```bash
# 1. Check help works
/dp:help

# 2. Verify configuration was created
cat .claude/dp-config.yaml

# 3. Check the created directory structure
ls -la docs/spec docs/adr tests/

# 4. If using Beads, verify task tracking
bd stats
```

**Expected output from `/dp:help`:**
```
Disciplined Process Plugin v1.0
================================

Commands:
  /dp:init      Initialize project with disciplined process
  /dp:task      Task tracking (ready, create, show, update, close)
  /dp:spec      Specification management (create, add, coverage, list)
  /dp:adr       Architecture Decision Records (create, list, status)
  /dp:review    Run code review checklist
...
```

### Your First Workflow

```bash
# 1. See what work is available
/dp:task ready

# 2. Create a specification
/dp:spec create 01-core "Core Functionality"

# 3. Add a requirement to the spec
/dp:spec add 01 "The system MUST validate user input"

# 4. Check specification coverage
/dp:spec coverage
```

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

## Commands Reference

| Command | Description |
|---------|-------------|
| `/dp:init` | Initialize project with wizard |
| `/dp:task` | Task tracking (ready, create, show, update, close) |
| `/dp:spec` | Specification management (create, add, coverage) |
| `/dp:adr` | Architecture Decision Records |
| `/dp:review` | Code review checklist |
| `/dp:help` | Help and workflow reference |

### Task Command Examples

```bash
/dp:task ready                          # Show available work
/dp:task create "Fix bug" -t bug        # Create a task
/dp:task show bd-a1b2                   # View task details
/dp:task update bd-a1b2 --status in_progress
/dp:task close bd-a1b2 --reason "Fixed"
```

### Spec Command Examples

```bash
/dp:spec create 02-auth "Authentication"
/dp:spec add 02 "Users MUST authenticate before access"
/dp:spec coverage                       # Check trace coverage
/dp:spec list                           # List all specs
```

### ADR Command Examples

```bash
/dp:adr create "Use JWT for authentication"
/dp:adr list                            # List all ADRs
/dp:adr status                          # Show ADR statuses
```

## Skills (Auto-Invoked)

These skills activate automatically based on context:

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

Configure in `.claude/dp-config.yaml`:

```yaml
enforcement:
  level: "strict"  # strict | guided | minimal
```

## Task Tracking Providers

| Provider | Description | Requirements |
|----------|-------------|--------------|
| **Beads** (default) | Git-backed, dependency-aware | Git |
| **GitHub Issues** | GitHub issue integration | `gh` CLI |
| **Linear** | Linear app integration | `linear` CLI |
| **Markdown** | Plain files in `docs/tasks/` | None |
| **None** | Skip task tracking | None |

## Project Structure

After initialization, your project will have:

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
│   └── process/            # Workflow documentation
│       └── code-review.md
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── e2e/
├── CLAUDE.md               # Project context for Claude
└── .beads/                 # Task tracker (if using Beads)
```

## Updating the Plugin

When new versions are released:

```bash
# Update plugin repository metadata
/plugin marketplace update rand/disciplined-process-plugin

# Update the plugin
/plugin update disciplined-process@disciplined-process-plugin

# Verify the update
/dp:help
```

Check for updates:
```bash
/plugin outdated
```

## Uninstalling

```bash
# Remove the plugin
/plugin uninstall disciplined-process@disciplined-process-plugin

# Optionally remove the plugin repository
/plugin marketplace remove rand/disciplined-process-plugin
```

Note: This does not remove project files created by `/dp:init`. To fully clean up:
```bash
rm -rf .claude/dp-config.yaml docs/spec docs/adr docs/process tests/ CLAUDE.md .beads/
```

## Troubleshooting

### Commands not recognized

1. Verify installation: `/plugin list`
2. Restart Claude Code
3. Reinstall: `/plugin install disciplined-process@disciplined-process-plugin`

### `/dp:init` fails

- Ensure you're in a valid project directory
- Check you have write permissions
- If files already exist, use `/dp:init --force` to overwrite

### Hooks not triggering

1. Check enforcement level isn't "minimal"
2. Verify `.claude/settings.json` exists and contains hook definitions
3. Ensure scripts have execute permissions: `chmod +x .claude/scripts/*.sh`

### Beads commands fail

1. Verify Git is initialized: `git status`
2. Check `.beads/` directory exists
3. Manually initialize: `bd init`

### Tests not being detected

The plugin looks for test files in `tests/{unit,integration,property,e2e}/`. Ensure your test files are in these directories or update your `dp-config.yaml` with custom paths.

### Trace markers not found

Trace markers must follow the format `@trace SPEC-XX.YY` where:
- `XX` is the spec section number (01, 02, etc.)
- `YY` is the paragraph number

Example in code:
```typescript
// @trace SPEC-01.03
function validateInput(data: string): boolean {
  // ...
}
```

## Configuration Reference

Full `dp-config.yaml` example:

```yaml
# Disciplined Process Configuration
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

## License

MIT

## Support

- **Documentation**: See `commands/` and `skills/` directories for detailed docs
- **Issues**: [GitHub Issues](https://github.com/rand/disciplined-process-plugin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rand/disciplined-process-plugin/discussions)
