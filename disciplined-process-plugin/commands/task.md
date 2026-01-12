---
description: Task tracking wrapper. Routes to configured provider (beads, github, linear, markdown). Subcommands: ready, create, show, update, close.
argument-hint: <ready|create|show|update|close> [options]
---

# Task Command

Unified interface for task tracking, routing to the configured provider.

## Provider Detection

Reads from `.claude/dp-config.yaml`:
```yaml
tracking:
  provider: "beads"  # beads | github | linear | markdown | none
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
Create a discovered task linked to current work.

```
/dp:task discover "<title>" [--from <parent-id>] [-p priority]
```

**Behavior**:
1. Create new task
2. Link with `discovered-from` dependency to parent
3. Inherit labels/context from parent

**Example**:
```
/dp:task discover "Edge case: empty input" --from bd-a1b2 -p 2
→ Created bd-3e7a: Edge case: empty input
→ Linked: discovered-from bd-a1b2
```

## Provider-Specific Notes

### Beads (default)
- Full feature support
- Uses `bd` CLI directly
- Dependency tracking built-in

### GitHub Issues
- Uses `gh issue` CLI
- Labels for type/priority
- Milestones for epics

### Linear
- Uses `linear` CLI
- Native priority support
- Team/project scoping

### Markdown
- Files in `docs/tasks/`
- YAML frontmatter for metadata
- Manual dependency tracking

## None Provider

When `provider: none`:
- Commands print reminder to track work manually
- No automatic task creation
- Workflow skills still function

```
/dp:task ready
→ Task tracking disabled. Consider enabling a provider in .claude/dp-config.yaml
```
