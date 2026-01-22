---
description: Show system health and diagnostics
argument-hint: [--verbose]
---

# Health Command

Display the health status of all disciplined process components.

## Basic Usage

```
/dp:health
```

Shows a summary of system health:

```
Disciplined Process Health Check
================================

Level: FULL ✓
Status: All features working normally

Components:
  ✓ config       - Configuration loaded successfully
  ✓ git          - Git repository is healthy
  ✓ task_tracker - beads is healthy
  ✓ beads_daemon - Beads daemon is running

Features Available:
  ✓ task_tracking
  ✓ adversarial_review
  ✓ auto_sync
  ✓ pre_commit_checks
  ✓ trace_markers
  ✓ git_operations
```

## Verbose Mode

```
/dp:health --verbose
```

Shows detailed information including last check timestamps and any recovery attempts.

## Understanding Degradation Levels

| Level | Description |
|-------|-------------|
| FULL | All features working normally |
| REDUCED | Non-critical features disabled |
| MANUAL | Requires manual intervention |
| SAFE | Minimal safe operation mode |
| RECOVERY | Actively attempting repair |

## Component Health

### Config
- Checks if dp-config.yaml can be loaded
- Recovery: Attempts to reload configuration

### Git
- Checks if git status works
- Recovery: Limited (checks repository access)

### Task Tracker
- Checks if configured provider (beads, github, etc.) is available
- Recovery: For beads, attempts `bd init` if .beads/ missing

### Beads Daemon
- Checks if beads daemon is running (if applicable)
- Recovery: Attempts `bd daemon start`

## Troubleshooting

If health shows issues:

1. Run `/dp:repair` to attempt automatic repair
2. Check specific component messages
3. Run `/dp:status` for current degradation info
4. Use `/dp:unlock` if manually locked

## Implementation

When this command is invoked, execute the following:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts/lib"))
from lib.degradation import run_health_checks, get_status_report
import json

# Run fresh health checks
state = run_health_checks()
report = get_status_report()

# Display results
print(f"Level: {report['level']}")
print(f"Status: {report['level_description']}")
print()
print("Components:")
for name, comp in report['components'].items():
    status = "✓" if comp['healthy'] else "✗"
    print(f"  {status} {name:14} - {comp['message']}")
print()
print("Features Available:")
for feature, available in report['available_features'].items():
    status = "✓" if available else "✗"
    print(f"  {status} {feature}")
```
