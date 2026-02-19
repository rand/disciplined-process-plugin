# Progress Report

**Parent:** [README.md](./README.md)  
**Related:** [orchestration.md](./orchestration.md) · [holes.md](./holes.md) · [cli-reference.md](./cli-reference.md) · [schemas.md](./schemas.md)

---

## Overview

In multi-agent, multi-session development, both humans and agents lose track of what's happened. Agents in fresh context windows have no memory of overall project state. Humans checking in after hours of agent work face a wall of git log entries and scattered file modifications.

`progress-report` periodically extracts a structured summary of changes, decisions, progress, holes, and new issues from project state, persists it as a Markdown file, and optionally broadcasts it to agents, email, Slack, or Discord.

```
project state  ──→  progress-report  ──→  timestamped markdown file
(git, beads, files)      │                  + broadcast to channels
                   (extract, summarize,
                    format, distribute)
```

---

## Trigger Conditions

The tool runs based on configurable conditional logic. Multiple triggers can be active simultaneously. If a time trigger and a completion trigger fire within 5 minutes of each other, only one report is generated.

```yaml
# .claude/progress-report.yaml
triggers:
  # Time-based
  interval: 30m              # Every 30 minutes while agents are active

  # Completion-based
  tasks_completed: 3         # After every N tasks completed
  issue_completed: true      # When an entire issue completes
  epic_milestone: true       # At 25%, 50%, 75%, 100% of epic completion

  # Event-based
  on_failure: true           # When a task fails or agent errors out
  on_rework: true            # When a diff creates rework tasks
  on_blocker: true           # When all ready work is exhausted

  # Hole-specific
  hole_created: true         # New hole discovered
  hole_resolved: true        # Hole resolved
  all_work_hole_blocked: true  # ALL remaining work blocked by holes
                               # (critical — human attention urgently needed)

  # Manual
  on_demand: true            # Always available via CLI
```

---

## Report Format

Each report is a self-contained Markdown file in `docs/progress/`:

```
docs/progress/
├── 2026-02-19T14-30-00-initial.md
├── 2026-02-19T15-00-00-3-tasks-complete.md
├── 2026-02-19T15-45-00-issue-oauth-complete.md
├── 2026-02-19T16-15-00-blocker-detected.md
└── latest.md  →  (symlink to most recent)
```

The filename encodes timestamp and trigger reason for scanning.

### Report Structure

```markdown
# Progress Report: User Authentication System

**Generated:** 2026-02-19T15:45:00Z
**Trigger:** Issue "OAuth Integration" completed
**Report #:** 3 of this epic

---

## Summary

OAuth integration complete. 4 of 12 tasks done (33%).
Token exchange and PKCE working end-to-end. Session management
now unblocked — 3 new tasks ready for parallel execution.

## Since Last Report (45 min ago)

### Completed
| Task | Agent | Duration | Tokens Used |
|------|-------|----------|-------------|
| bd-e5f6: Token exchange endpoint | session-7a2b | 18 min | ~28K |
| bd-g7h8: Wire upload to S3 | session-9c4d | 12 min | ~14K |

### Key Decisions Made
- Token exchange returns both access and refresh tokens in a single
  response. See commit a1b2c3d.
- PKCE verifier length set to 64 chars (above RFC min of 43).

### New Issues Discovered
| Issue | Priority | Source |
|-------|----------|--------|
| bd-x1y2: Handle OAuth timeout | P2 | discovered-from:bd-e5f6 |

### Warnings
- Token estimate for bd-e5f6 was 25K, actual 28K (+12%).

## Holes

### Open (blocking work)
| Hole | Type | Blocks | Urgency |
|------|------|--------|---------|
| H001: Session on token revocation | clarification | T005, T006 | ⚠️ HIGH |
| H003: Rate limit algorithm | research | T009 | MEDIUM |

### Recently Resolved
| Hole | Resolution | Resolved By | Impact |
|------|-----------|-------------|--------|
| H002: S3 conditional PUT | Yes, If-None-Match supported | Agent | T003 unblocked |

### Hole Metrics
- Total: 4 | Resolved: 2 (50%) | Open blocking: 2 (3 tasks)
- Avg resolution time: 22 min

## Current State

### Progress
  ██████████░░░░░░░░░░░░░░░░░░░░ 33% (4/12 tasks)

  ✅ Issue: OAuth Integration (4/4) — COMPLETE
  🔄 Issue: Session Management (0/4) — IN PROGRESS
  ⬜ Issue: Rate Limiting & Security (0/4) — NOT STARTED

### Ready Work
| Task | Priority | Est. Tokens | Parallel Group |
|------|----------|-------------|----------------|
| bd-m1n2: Create session from token | P1 | ~20K | post-oauth |
| bd-o3p4: Session expiry and cleanup | P2 | ~15K | post-oauth |
| bd-q5r6: Sliding window rate limiter | P1 | ~22K | independent |

### Blocked
| Task | Blocked By | Est. Unblock |
|------|-----------|--------------|
| bd-s7t8: "Remember me" sessions | bd-m1n2 | After session creation |

### Risks
- bd-w1x2 (Security audit logging) depends on both session AND
  rate limiting — on the critical path.

## Files Changed Since Last Report
 M src/api/auth/token_exchange.py    (+142 lines)
 A tests/integration/test_oauth.py   (+95 lines)

## For Agents: Context Loading Instructions

If you're starting a new session:
1. Read this file for high-level context.
2. Run `bd ready --json` for your next task.
   ⚠️ If ready list is empty, check for agent-resolvable holes:
   `bd list --label hole:agent-resolvable --status open --json`
3. Run `bd show <task-id>` for full task details.
4. Do NOT read the full spec or git log — task descriptions are self-contained.

## For Humans: Action Items
- [ ] Review discovered issue bd-x1y2 — confirm priority
- [ ] Resolve H001 (session on token revocation) — blocks 2 tasks
- [ ] 3 tasks ready for parallel execution — spin up agents?
```

### Machine-Readable Companion

The tool also generates `docs/progress/latest.json` for orchestrators and agents. See [schemas.md § Progress Report JSON](./schemas.md#progress-report-json).

---

## Broadcast Channels

```yaml
# .claude/progress-report.yaml
broadcast:
  file: true                  # Always write to docs/progress/
  agent_brief: docs/progress/latest.md  # Symlink to most recent

  email:
    enabled: true
    to: ["rand@example.com"]
    on_triggers: [issue_completed, epic_milestone, on_failure, on_blocker]

  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#project-auth"
    on_triggers: [issue_completed, epic_milestone, on_failure]
    format: summary  # summary | full

  discord:
    enabled: true
    webhook_url: "${DISCORD_WEBHOOK_URL}"
    on_triggers: [issue_completed, on_failure]
    format: summary

  webhook:
    enabled: false
    url: "${CUSTOM_WEBHOOK_URL}"
    method: POST
    payload: json
    on_triggers: [all]
```

### Implementation

No heavy dependencies. Each channel is a function that takes report content and delivers it:

| Channel | Method |
|---------|--------|
| File | Write markdown to `docs/progress/` |
| Agent | Update symlink at `docs/progress/latest.md` |
| Email | Shell out to `sendmail`, `mailx`, or configured SMTP command |
| Slack | POST to webhook URL (single curl command) |
| Discord | POST to webhook URL (single curl command) |
| Webhook | POST JSON to configured URL |

Slack summary format:

```
📊 *Progress Report: User Authentication System*
*Trigger:* Issue "OAuth Integration" completed

✅ 4/12 tasks complete (33%)
🆕 3 tasks ready for parallel execution
⚠️ 1 new issue discovered
🕳️ 2 open holes (1 needs human decision)

*Ready work:* Create session (P1), Session expiry (P2), Rate limiter (P1)
*Full report:* <link>
```

---

## Running the Reporter

```bash
progress-report                    # One-shot
progress-report --watch            # Daemon mode
progress-report --trigger "Phase 1 complete"  # Manual trigger
progress-report --no-broadcast     # File only, no notifications
```

In daemon/watch mode, the reporter:

1. Polls Beads state (`bd stats --json`, `bd list --json`) at the configured interval (default: 60s — cheap local SQLite query).
2. Diffs against the last report's state snapshot.
3. If any trigger condition is met, generates a new report.
4. Broadcasts to configured channels.
5. Sleeps until next check.
