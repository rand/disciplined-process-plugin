# CLI Reference

**Parent:** [README.md](./README.md)  
**Related:** All other documents

---

## spec-decompose

```
spec-decompose [options] <spec-files...>

Core Options:
  --output, -o        Output format: beads (default), markdown
  --dir               Output directory for markdown (default: ./docs/tasks/)
  --context-window    Target context window in tokens (default: 200000)
  --constitution      Path to constitution/principles file for context

Decomposition Mode:
  --diff              Diff against existing state instead of fresh decompose
  --strict            Fail on ambiguities (equivalent to --holes-strategy strict)
  --best-effort       Assume on ambiguities (equivalent to --holes-strategy assume)

Holes:
  --holes-strategy    How to handle ambiguities:
                        graph (default) — create holes as blocking work items
                        warn — log as warnings only (legacy behavior)
                        strict — fail on any ambiguity
                        assume — assume and note, never create holes
  --auto-resolve      Let agents attempt validation/research holes during
                      decomposition (adds time, may reduce hole count)

Multi-Agent:
  --orchestrate       Generate orchestration script (orchestrate.sh)
  --parallel-slots N  Max concurrent agents for orchestration (default: 3)

Advanced:
  --model             Model for decomposition subagent (default: opus)
  --existing-code     Path to codebase for better file size estimates
  --epic-title        Override the generated epic title
  --dry-run           Show plan without generating output files
```

### Output Files

| File | When Generated | Contents |
|------|---------------|----------|
| `decompose-plan.md` | Always | Human-readable plan with graph, holes, coverage |
| `decompose-plan.sh` | `--output beads` | `bd` commands to execute |
| `decompose-diff.md` | `--diff` | Change analysis |
| `decompose-diff.sh` | `--diff --output beads` | Incremental `bd` commands |
| `orchestrate.sh` | `--orchestrate` | Fan-out script |
| `docs/tasks/` | `--output markdown` | Task files, hole files, state.yaml |

### Examples

```bash
# Fresh decomposition into Beads
spec-decompose docs/spec/auth.md
cat decompose-plan.md && bash decompose-plan.sh

# Re-decompose after spec change
spec-decompose --diff docs/spec/auth.md
cat decompose-diff.md && bash decompose-diff.sh

# Parallel fan-out with 4 agents
spec-decompose docs/spec/auth.md --orchestrate --parallel-slots 4
bash decompose-plan.sh && bash orchestrate.sh

# Smaller context window for Codex
spec-decompose docs/spec/auth.md --context-window 128000

# Markdown output, holes as warnings only
spec-decompose docs/spec/auth.md -o markdown --holes-strategy warn

# Auto-resolve validation holes during decomposition
spec-decompose docs/spec/auth.md --auto-resolve

# Dry run (plan only, no output files)
spec-decompose docs/spec/auth.md --dry-run
```

---

## progress-report

```
progress-report [options]

Core Options:
  --config            Path to config file (default: .claude/progress-report.yaml)
  --trigger           Override trigger reason for this report
  --format            Output format: markdown (default), json, both

Watch Mode:
  --watch             Run as daemon, generate reports on trigger conditions
  --poll-interval     Seconds between state checks (default: 60)

Broadcast:
  --broadcast         Channels to notify: file,agent,email,slack,discord,webhook
  --no-broadcast      Generate report file only, skip notifications
  --slack-webhook     Slack webhook URL (overrides config)
  --discord-webhook   Discord webhook URL (overrides config)
  --email-to          Email recipient(s) (overrides config)

Output:
  --dir               Report output directory (default: docs/progress/)
```

### Examples

```bash
# Generate report now, broadcast to all configured channels
progress-report

# Watch mode with Slack notifications
progress-report --watch --broadcast slack

# Quick status check, no broadcast
progress-report --no-broadcast

# Custom trigger from orchestrator
progress-report --trigger "Phase 1 complete"

# JSON output only
progress-report --format json --no-broadcast
```

---

## Configuration File

Both tools read from `.claude/progress-report.yaml` when present. The full schema is in [schemas.md § Configuration](./schemas.md#configuration-yaml).

```yaml
# .claude/progress-report.yaml
triggers:
  interval: 30m
  tasks_completed: 3
  issue_completed: true
  epic_milestone: true
  on_failure: true
  on_rework: true
  on_blocker: true
  hole_created: true
  hole_resolved: true
  all_work_hole_blocked: true
  on_demand: true

broadcast:
  file: true
  agent_brief: docs/progress/latest.md
  email:
    enabled: false
    to: []
    on_triggers: [issue_completed, epic_milestone, on_failure]
  slack:
    enabled: false
    webhook_url: "${SLACK_WEBHOOK_URL}"
    on_triggers: [issue_completed, epic_milestone, on_failure]
    format: summary
  discord:
    enabled: false
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
