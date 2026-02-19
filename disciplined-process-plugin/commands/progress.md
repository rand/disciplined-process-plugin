---
description: Generate structured progress reports with optional broadcasting
argument-hint: [--watch] [--trigger "<reason>"] [--no-broadcast]
---

# /dp:progress — Progress Reporter

Generate structured progress reports from project state (Beads, git). Reports are timestamped Markdown files with a machine-readable JSON companion.

## Usage

```
/dp:progress                              # One-shot report
/dp:progress --trigger "Phase 1 complete" # Manual trigger with reason
/dp:progress --no-broadcast               # File only, no notifications
/dp:progress --watch                      # Daemon mode (polls and reports)
```

## What It Does

1. Extracts current state from Beads (`bd list --json`, `bd stats --json`) and git
2. Generates a progress report with: summary, completed work, holes, ready work, blocked work, files changed
3. Writes to `docs/progress/YYYY-MM-DDTHH-MM-SS-trigger.md`
4. Updates `docs/progress/latest.md` symlink
5. Writes `docs/progress/latest.json` (machine-readable)
6. Optionally broadcasts to configured channels (Slack, Discord, email, webhook)

## Report Sections

- **Summary** — Overall progress percentage and quick status
- **Since Last Report** — Newly completed tasks, new issues discovered
- **Holes** — Open holes blocking work, recently resolved, metrics
- **Current State** — Progress bar, ready work, blocked tasks
- **Files Changed** — Git diff since last report
- **For Agents** — Context loading instructions for fresh sessions
- **For Humans** — Action items requiring human attention

## Configuration

Create `.claude/progress-report.yaml`:

```yaml
triggers:
  interval: 30m
  tasks_completed: 3
  issue_completed: true
  epic_milestone: true
  hole_created: true
  all_work_hole_blocked: true

broadcast:
  file: true
  agent_brief: docs/progress/latest.md
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#project"
```

## Integration with spec-decompose

After running `/dp:decompose` and agents start executing tasks:

1. `/dp:progress` gives you a snapshot of where things stand
2. `/dp:progress --watch` keeps you updated automatically
3. Agents starting fresh sessions read `docs/progress/latest.md` for context
