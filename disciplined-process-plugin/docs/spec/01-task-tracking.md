# Task Tracking
[SPEC-01]

## Overview

[SPEC-01.01] The plugin SHALL provide unified task tracking across multiple providers.

[SPEC-01.02] Supported task tracking providers:
- **Beads** - Git-backed distributed tracker (recommended)
- **Builtin** - Claude Code native task system
- **Chainlink** - SQLite-based local tracker with sessions
- **GitHub** - GitHub Issues integration
- **Linear** - Linear.app integration
- **Markdown** - File-based tracking in `docs/tasks/`
- **None** - Disabled (guidance only)

## Provider Detection

[SPEC-01.10] The plugin SHALL detect the configured provider from `dp-config.yaml`:

```yaml
task_tracker: beads  # or: builtin, chainlink, github, linear, markdown, none
```

[SPEC-01.11] When no config exists, the plugin SHALL detect available providers:
1. Check for `.beads/` directory → Beads
2. Check for `.chainlink/` directory → Chainlink
3. Check for `docs/tasks/` directory → Markdown
4. Fall back to Builtin

[SPEC-01.12] Provider availability checks SHALL verify:
- CLI is installed and executable
- Required directories/files exist
- Authentication is valid (for cloud providers)

## Command Interface

### /dp:task ready

[SPEC-01.20] The `ready` command SHALL show tasks with no blockers.

```
/dp:task ready [--limit N] [--priority P]
```

[SPEC-01.21] Output format:
```
Ready Work (N tasks)

<id>  <priority>  [<type>]  <title>
...

Claim with: /dp:task update <id> --status in_progress
```

### /dp:task create

[SPEC-01.30] The `create` command SHALL create a new task.

```
/dp:task create "<title>" [-t type] [-p priority] [--link <ref>]
```

[SPEC-01.31] Arguments:
- `-t, --type`: bug | task | feature | epic (default: task)
- `-p, --priority`: 0-4 where 0=critical (default: 2)
- `--link`: Link to spec, ADR, or parent task

### /dp:task show

[SPEC-01.40] The `show` command SHALL display task details.

```
/dp:task show <id>
```

[SPEC-01.41] Output SHALL include:
- Status, priority, type
- Description
- Dependencies (blocks/blocked-by)
- Linked specs and ADRs
- Audit trail (if supported by provider)

### /dp:task update

[SPEC-01.50] The `update` command SHALL modify task fields.

```
/dp:task update <id> [--status S] [--priority P] [--assignee A]
```

[SPEC-01.51] Status values: open, in_progress, blocked, closed

### /dp:task close

[SPEC-01.60] The `close` command SHALL complete a task.

```
/dp:task close <id> [--reason "<reason>"] [--summary]
```

[SPEC-01.61] With `--summary`, the command SHALL generate:
- Specs implemented (from @trace markers)
- Files changed (from git diff)
- Tests added
- Discovered work (linked tasks)

### /dp:task discover

[SPEC-01.70] The `discover` command SHALL create linked discovered work.

```
/dp:task discover "<title>" [--from <parent-id>] [-p priority] [--type <deviation>]
```

[SPEC-01.71] Deviation types (GSD-inspired):
- `bug` - Bug found during implementation
- `scope-creep` - Work outside original scope
- `dependency` - Missing prerequisite discovered
- `blocked` - External blocker found
- `refactor` - Technical debt discovered
- `edge-case` - Edge case not in original spec

[SPEC-01.72] Behavior:
1. Create new task with deviation label
2. Link with `discovered-from` dependency
3. Inherit context from parent

## Provider Feature Matrix

[SPEC-01.80] Not all features work with all providers:

| Feature | Beads | Builtin | Chainlink | GitHub | Linear | Markdown | None |
|---------|:-----:|:-------:|:---------:|:------:|:------:|:--------:|:----:|
| ready | Yes | Yes | Yes | Yes | Yes | Yes | No |
| create | Yes | Yes | Yes | Yes | Yes | Yes | No |
| show | Yes | Yes | Yes | Yes | Yes | Yes | No |
| update | Yes | Yes | Yes | Yes | Yes | Yes | No |
| close | Yes | Yes | Yes | Yes | Yes | Yes | No |
| discover | Yes | Yes | Yes | Partial | Partial | No | No |
| Dependencies | Yes | Yes | Yes | No | Yes | No | No |
| Git-tracked | Yes | No | Yes | Yes | Yes | Yes | No |

## Graceful Degradation

[SPEC-01.90] If the configured provider is unavailable:
- Commands SHALL warn once per session
- Workflow SHALL continue without blocking
- Clear guidance SHALL be provided for recovery

[SPEC-01.91] Recovery guidance format:
```
Warning: Beads CLI not found. Task tracking degraded.
Fix: Install beads (pip install beads-cli) or change provider in dp-config.yaml
```
