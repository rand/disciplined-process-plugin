---
description: Reset degradation to full mode
argument-hint: [--confirm]
---

# Reset Command

Reset the system to full degradation level, clearing all health state.

## Basic Usage

```
/dp:reset
```

Prompts for confirmation:

```
Disciplined Process Reset
=========================

This will:
  • Reset degradation level to FULL
  • Clear all component health state
  • Clear any locks
  • Clear recovery history

Current state:
  Level: REDUCED
  Locked: No
  Components with issues: 1

Are you sure you want to reset? (yes/no)
```

## Confirm Without Prompt

```
/dp:reset --confirm
```

Skips confirmation and immediately resets.

## When to Use Reset

1. **After manual fixes**: When you've manually resolved issues
2. **Stuck in degraded mode**: When auto-repair isn't working
3. **Fresh start**: When you want to clear all state
4. **Testing**: When testing degradation behavior

## What Gets Reset

- Degradation level → FULL
- All component health states → cleared
- Recovery attempt history → cleared
- Lock status → unlocked
- State file → recreated fresh

## What Doesn't Get Reset

- Configuration (dp-config.yaml)
- Task tracker data
- Git repository state
- Any files or code

## After Reset

After reset, the next action (hook or command) will trigger fresh health checks.
If issues still exist, the system will re-detect and degrade appropriately.

## Caution

Reset doesn't fix underlying issues. If you reset while components are
unhealthy, the system will just re-detect and degrade again.

Use reset when:
- You've fixed the issues manually
- You want to force a fresh health check cycle

Don't use reset as a workaround for persistent issues.

## Implementation

When this command is invoked, execute the following:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts/lib"))
from lib.degradation import reset_to_full, load_state

# Show current state first
state = load_state()
print(f"Current level: {state.level.name}")
print(f"Locked: {state.locked}")

# Confirm unless --confirm flag
if "--confirm" not in args:
    response = input("Reset to FULL mode? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled.")
        return

# Reset
new_state = reset_to_full()
print(f"\n✓ Reset complete. Level: {new_state.level.name}")
print("  Fresh health checks will run on next action.")
```
