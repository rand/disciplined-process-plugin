---
description: Session management for work context preservation
argument-hint: <start|work|status|end> [options]
---

# Session Command

Manage work sessions to preserve context across Claude Code restarts.

**Note**: This command requires Chainlink as your task tracker. When using Beads or other providers, session commands are unavailable (Beads doesn't support session management).

## Provider Check

This command checks `.claude/dp-config.yaml`:
```yaml
tracking:
  provider: "chainlink"  # Sessions only work with chainlink
```

If provider is not `chainlink`, all session commands will display:
```
Session management requires Chainlink as task tracker.
Current provider: beads
To enable: set tracking.provider to "chainlink" in dp-config.yaml
```

## Subcommands

### start
Start a new work session.

```
/dp:session start [--description "session focus"]
```

**Executes**: `chainlink session start`

**Behavior**:
1. Creates a new session with timestamp
2. Clears previous session's working issue
3. Returns session ID for reference

**Example**:
```
/dp:session start --description "Implementing feature X"
-> Started session #42 at 2026-01-22T10:30:00
-> Focus: Implementing feature X
```

### work
Set the issue you're currently working on.

```
/dp:session work <issue-id>
```

**Executes**: `chainlink session work <issue-id>`

**Behavior**:
1. Associates the issue with the current session
2. Starts time tracking for the issue
3. Updates issue status to `in_progress` if not already

**Example**:
```
/dp:session work CL-123
-> Now working on: CL-123 (Implement authentication)
-> Timer started
```

### status
Show current session status.

```
/dp:session status
```

**Executes**: `chainlink session status`

**Output**:
```
Session #42 (active)
Started: 2026-01-22T10:30:00 (2h 15m ago)
Focus: Implementing feature X
Working on: CL-123 (Implement authentication)
Time on issue: 1h 45m
Issues touched: CL-123, CL-124, CL-125
```

### end
End the current session with handoff notes.

```
/dp:session end [--notes "handoff notes"]
```

**Executes**: `chainlink session end --notes "..."`

**Behavior**:
1. Stops any active timers
2. Records session duration
3. Saves handoff notes for the next session
4. Clears working issue

**Example**:
```
/dp:session end --notes "Completed auth flow, need to add tests for edge cases"
-> Ended session #42
-> Duration: 2h 30m
-> Handoff notes saved
```

## Hook Integration

### SessionStart Hook

The `session_start.py` hook automatically:
1. Checks for previous session handoff notes
2. Displays them to provide context
3. Optionally starts a new session

```
Previous session ended: 2026-01-22T08:00:00
Handoff notes: "Completed auth flow, need to add tests for edge cases"

Start new session? Use /dp:session start
```

### Stop Hook

The `stop` hook (when implemented) will:
1. Prompt for session end if active session exists
2. Request handoff notes before closing
3. Automatically sync session state

## Session Context Preservation

Sessions preserve context across Claude Code restarts by storing:
- **Active issue**: What you were working on
- **Handoff notes**: Context for the next session
- **Time tracking**: Duration spent on issues
- **Issues touched**: All issues modified in the session

This enables seamless context handoff between sessions, reducing the need to re-explain project state.

## Graceful Degradation

If Chainlink is unavailable or not configured:
- Commands display a helpful message about enabling sessions
- Workflow continues without blocking
- Use `/dp:task` commands directly for basic task management
