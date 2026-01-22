---
description: Unlock degradation level
argument-hint:
---

# Unlock Command

Remove the manual lock on degradation level, allowing automatic transitions.

## Basic Usage

```
/dp:unlock
```

Unlocks the degradation level:

```
Disciplined Process Unlock
==========================

Previous state:
  Level: MANUAL
  Locked: Yes
  Lock reason: User requested manual override

Unlocking...

✓ Degradation level unlocked.
  Automatic transitions are now enabled.
  Use '/dp:health' to check current state.
```

## When Levels Get Locked

Degradation levels can be locked:

1. **Manually**: User runs a command to lock at current level
2. **Safety**: Some critical issues auto-lock to prevent oscillation
3. **Recovery**: During repair operations

## Why Lock Exists

Locking prevents:
- Rapid oscillation between levels
- Premature upgrades before issues are verified fixed
- Accidental degradation during sensitive operations

## Unlocking Considerations

Before unlocking:

1. Check if the underlying issues are resolved (`/dp:health`)
2. Understand why the lock was set (`/dp:status`)
3. Be prepared for automatic level changes after unlock

## Related Commands

- `/dp:status` - See current lock status and reason
- `/dp:health` - Check component health
- `/dp:repair` - Fix issues before unlocking
- `/dp:reset` - Full reset (also unlocks)

## Lock Command

To manually lock at current level:

```python
from lib.degradation import lock_level
lock_level("Manual override for deployment")
```

This is typically done programmatically, not via slash command.

## Implementation

When this command is invoked, execute the following:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts/lib"))
from lib.degradation import unlock_level, load_state

# Show current state
state = load_state()
if not state.locked:
    print("System is not locked. No action needed.")
    return

print(f"Current level: {state.level.name}")
print(f"Lock reason: {state.lock_reason}")

# Unlock
unlock_level()
print("\n✓ Degradation level unlocked.")
print("  Automatic transitions are now enabled.")
```
