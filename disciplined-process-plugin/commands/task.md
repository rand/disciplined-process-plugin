---
description: Task tracking via configured provider
argument-hint: <ready|create|show|update|close|discover> [options]
---

# Task Command

Unified interface for task tracking, routing to the configured provider.

## Provider Detection

Reads from `.claude/dp-config.yaml`:
```yaml
task_tracker: "beads"  # beads | builtin | chainlink | github | linear | markdown | none
```

## Subcommands

All subcommands route to the underlying provider with consistent interface.

### ready
Show tasks ready for work (no blockers).

```
/dp:task ready [--limit N] [--priority P]
```

**Provider mapping**:
- Beads: `bd ready --json`
- Builtin: Read `~/.claude/tasks/<list>/` JSON files with `status: pending` and no blockers
- Chainlink: `chainlink ready`
- GitHub: `gh issue list --label ready`
- Linear: `linear issue list --state started`
- Markdown: Scan `docs/tasks/*.md` for `status: ready`

**Output**:
```
Ready Work (3 tasks)

bd-a1b2  P1  [task]   Implement type resolution
bd-f14c  P2  [bug]    Fix parser edge case
bd-3e7a  P2  [task]   Add validation tests

Claim with: /dp:task update <id> --status in_progress
```

### create
Create a new task.

```
/dp:task create "<title>" [-t type] [-p priority] [--link <ref>]
```

**Arguments**:
- `-t, --type`: bug | task | feature | epic (default: task)
- `-p, --priority`: 0-4, 0=highest (default: 2)
- `--link`: Link to spec, ADR, or parent task

**Example**:
```
/dp:task create "Implement SPEC-03.07" -t task -p 1 --link SPEC-03.07
→ Created bd-a1b2: Implement SPEC-03.07
→ Linked to SPEC-03.07
```

### show
Show task details.

```
/dp:task show <id>
```

**Output**:
```
bd-a1b2: Implement type resolution
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status:    in_progress
Priority:  P1
Type:      task
Created:   2025-01-10

Description:
  Per SPEC-03.07, types MUST be resolved before codegen.

Links:
  - SPEC-03.07 (implements)
  - bd-f14c (blocks)

Audit Trail:
  2025-01-10 10:00  Created
  2025-01-11 09:30  Status → in_progress
```

### update
Update task fields.

```
/dp:task update <id> [--status S] [--priority P] [--assignee A]
```

**Status values**: open, in_progress, blocked, closed

**Example**:
```
/dp:task update bd-a1b2 --status in_progress
→ Updated bd-a1b2: Status → in_progress
```

### close
Close a completed task.

```
/dp:task close <id> [--reason "<reason>"]
```

**Example**:
```
/dp:task close bd-a1b2 --reason "Implemented per SPEC-03.07, tests passing"
→ Closed bd-a1b2
```

### discover
Create a discovered task linked to current work, with optional deviation classification.

```
/dp:task discover "<title>" [--from <parent-id>] [-p priority] [--type <deviation-type>]
```

**Arguments**:
- `--from`: Parent task ID (links as `discovered-from`)
- `-p, --priority`: 0-4, 0=highest (default: 2)
- `--type, -t`: Deviation classification (see below)

**Deviation Types** (GSD-inspired):

| Type | Description | Example |
|------|-------------|---------|
| `bug` | Bug found during implementation | "Found null pointer in edge case" |
| `scope-creep` | Work outside original scope | "Also need to update admin panel" |
| `dependency` | Missing prerequisite discovered | "Need database migration first" |
| `blocked` | External blocker found | "Waiting on API key from vendor" |
| `refactor` | Technical debt discovered | "Should extract shared utility" |
| `edge-case` | Edge case not in original spec | "Handle empty input array" |

**Behavior**:
1. Create new task with deviation label
2. Link with `discovered-from` dependency to parent
3. Inherit labels/context from parent
4. Add `deviation:<type>` label for tracking

**Examples**:
```
/dp:task discover "Edge case: empty input" --from bd-a1b2 --type edge-case
→ Created bd-3e7a: Edge case: empty input
→ Linked: discovered-from bd-a1b2
→ Labels: deviation:edge-case

/dp:task discover "Need auth refactor first" --from bd-a1b2 --type dependency -p 1
→ Created bd-4f8b: Need auth refactor first
→ Linked: discovered-from bd-a1b2
→ Labels: deviation:dependency
```

**Tracking Deviations**:
Query discovered work by type for retrospectives:
```
bd list --labels=deviation:bug        # Find all bugs discovered during work
bd list --labels=deviation:scope-creep # Find scope creep patterns
```

## Provider Feature Matrix

Not all features work with all providers. Choose based on your needs:

| Feature | Beads | Builtin | Chainlink | GitHub | Linear | Markdown | None |
|---------|:-----:|:-------:|:---------:|:------:|:------:|:--------:|:----:|
| `ready` - find available work | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `create` - create tasks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `show` - view details | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `update` - change status | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `close` - complete tasks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `discover` - linked discovery | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ |
| Dependency blocking | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Git-tracked | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Auto-sync with remote | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Offline support | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Zero setup required | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Session tracking | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Time tracking | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Hierarchical tree view | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |

**Legend**: ✅ Full support | ⚠️ Partial (creates task, no dependency link) | ❌ Not supported

## Provider Details

### Beads (recommended)
- **CLI**: `bd` (install: `brew install beads`, `npm i -g beads-cli`, or `go install`)
- **Requires**: Git repository
- **Strengths**: Full dependency tracking, discovered-from linking, git-native sync, MCP server, works offline
- **Limitations**: Requires beads CLI installation
- **Note**: Recommended for team projects and git-tracked work

### Builtin (Claude Code Native)
- **CLI**: None required (uses Claude Code's `~/.claude/tasks/` system)
- **Requires**: Claude Code v2.1.16+
- **Strengths**: Zero setup, always available, dependency tracking via blocks/blockedBy
- **Limitations**: Not git-tracked, user-local only, no issue types/priorities
- **Note**: Tasks isolated per-project via `CLAUDE_CODE_TASK_LIST_ID` env var (auto-generated from project path)

### Chainlink
- **CLI**: `chainlink` (requires building from source - not publicly available)
- **Requires**: Private source access or pre-built binary
- **Strengths**: Full dependency tracking, session/time tracking, hierarchical tree view, works offline
- **Limitations**: Not publicly installable; use Beads for similar features
- **Extra commands**: `tree`, `next`, `session`, `blocked`, `timer`
- **Note**: If Chainlink unavailable, disciplined-process gracefully falls back

### GitHub Issues
- **CLI**: `gh` (install: `brew install gh` or https://cli.github.com)
- **Requires**: GitHub repo, authenticated `gh auth login`
- **Strengths**: Native GitHub integration, team collaboration, web UI
- **Limitations**: No dependency blocking, `discover` creates unlinked issues

### Linear
- **CLI**: `linear` (install: see Linear documentation)
- **Requires**: Linear account, authenticated CLI
- **Strengths**: Native priorities, team/project scoping, good UI
- **Limitations**: `discover` creates unlinked issues

### Markdown
- **CLI**: None required
- **Location**: `docs/tasks/*.md` with YAML frontmatter
- **Strengths**: No dependencies, works anywhere, human-readable
- **Limitations**: No auto-sync, no dependency tracking, manual status updates

### None
- Disables task tracking entirely
- All `/dp:task` commands print a reminder
- Use when task tracking is handled externally

## Chainlink-Specific Commands

These commands are only available when using Chainlink as your provider.

### tree
Show issues as a hierarchical tree.

```
/dp:task tree
```

**Output**:
```
Issues Tree
├── [CL-001] Project setup
│   ├── [CL-002] Configure build system
│   └── [CL-003] Setup testing framework
└── [CL-004] Implement feature X
    └── [CL-005] Write tests for X
```

### next
Suggest the next issue to work on based on priority and dependencies.

```
/dp:task next
```

### session
Manage work sessions for time tracking.

```
/dp:task session start    # Start a new session
/dp:task session end      # End current session
/dp:task session status   # Show current session
/dp:task session work <id> # Set active issue
```

### timer
Track time spent on issues.

```
/dp:task timer start <id>  # Start timer for issue
/dp:task timer stop        # Stop current timer
/dp:task timer status      # Show timer status
```

### blocked
Show all blocked issues and what's blocking them.

```
/dp:task blocked
```

## Graceful Degradation

If your configured provider is unavailable (CLI missing, not authenticated, etc.):
- Commands will warn once per session
- Workflow continues without blocking
- Fix with: reinstall CLI, re-authenticate, or change provider in `dp-config.yaml`
