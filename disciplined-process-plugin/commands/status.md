---
description: Show current degradation status
argument-hint: [--json]
---

# Status Command

Display the current degradation level and system status.

## Basic Usage

```
/dp:status
```

Shows current system status:

```
Disciplined Process Status
==========================

Degradation Level: FULL
Description: All features working normally

Last Transition: 2026-01-22T09:41:12
Reason: All components healthy

Locked: No

Active Components: 4
  • config
  • git
  • task_tracker
  • beads_daemon
```

## JSON Output

```
/dp:status --json
```

Returns machine-readable JSON:

```json
{
  "level": "FULL",
  "level_description": "All features working normally",
  "locked": false,
  "lock_reason": "",
  "last_transition": "2026-01-22T09:41:12",
  "transition_reason": "All components healthy",
  "component_count": 4,
  "unhealthy_count": 0
}
```

## Understanding Status

### Level
The current degradation level (FULL, REDUCED, MANUAL, SAFE, RECOVERY)

### Locked
If true, the level is manually locked and won't auto-transition.
Use `/dp:unlock` to release the lock.

### Last Transition
When the system last changed degradation levels.

### Components
Number of monitored components and their health.

## Quick Status

For a quick one-line status, check the session start message.
If running in degraded mode, you'll see a warning on session start.

## Related Commands

- `/dp:health` - Detailed component health
- `/dp:repair` - Attempt automatic repair
- `/dp:unlock` - Unlock degradation level
- `/dp:reset` - Reset to full mode

## Implementation

When this command is invoked, execute the following:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts/lib"))
from lib.degradation import load_state, get_status_report

state = load_state()
report = get_status_report()

print(f"Degradation Level: {report['level']}")
print(f"Description: {report['level_description']}")
print()
print(f"Last Transition: {report['last_transition']}")
print(f"Reason: {report['transition_reason'] or 'N/A'}")
print()
print(f"Locked: {'Yes - ' + state.lock_reason if state.locked else 'No'}")
print()
healthy = sum(1 for c in report['components'].values() if c['healthy'])
total = len(report['components'])
print(f"Components: {healthy}/{total} healthy")
```
