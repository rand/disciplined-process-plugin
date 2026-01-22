---
description: Attempt automatic repair of system issues
argument-hint: [--force]
---

# Repair Command

Attempt to automatically repair any detected system issues.

## Basic Usage

```
/dp:repair
```

Runs health checks and attempts recovery for any unhealthy components:

```
Disciplined Process Repair
==========================

Checking system health...

Found 2 issues:
  ✗ task_tracker - .beads/ not initialized
  ✗ beads_daemon - Beads daemon not running

Attempting repairs...

  task_tracker: Running 'bd init'...
    ✓ Repair successful

  beads_daemon: Running 'bd daemon start'...
    ✓ Repair successful

Re-checking health...

Level: FULL ✓
All issues resolved.
```

## Force Mode

```
/dp:repair --force
```

Forces repair attempts even for components that appear healthy. Useful when:
- Health checks report healthy but behavior seems wrong
- After manual fixes to verify state

## What Gets Repaired

### Task Tracker
- **Beads**: Runs `bd init` if .beads/ directory missing
- **GitHub**: Verifies gh CLI authentication
- **Markdown**: Creates docs/tasks/ if missing

### Beads Daemon
- Runs `bd daemon start` if not running
- Restarts daemon if unresponsive

### Configuration
- Reloads configuration from disk
- Creates default config if missing

### Git
- Limited repair capability
- Checks repository access

## When Repair Fails

If automatic repair fails:

1. Check the error messages
2. Try manual fixes:
   - For beads: `bd init`, `bd sync`
   - For git: `git status`, check .git/ directory
   - For config: Check dp-config.yaml syntax
3. Reset to clean state with `/dp:reset`
4. Contact support if issues persist

## Implementation

When this command is invoked, execute the following:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts/lib"))
from lib.degradation import (
    run_health_checks, attempt_recovery, load_state, save_state
)

# Run health checks first
state = run_health_checks()

# Find unhealthy components
unhealthy = [c for c in state.components.values() if not c.healthy]

if not unhealthy:
    print("All components healthy. No repairs needed.")
else:
    print(f"Found {len(unhealthy)} issues:")
    for comp in unhealthy:
        print(f"  ✗ {comp.component} - {comp.message}")

    print("\nAttempting repairs...")
    for comp in unhealthy:
        print(f"\n  {comp.component}: ", end="")
        success = attempt_recovery(comp.component, state)
        if success:
            print("✓ Repair successful")
        else:
            print("✗ Repair failed")

    # Re-run health checks
    state = run_health_checks()
    print(f"\nFinal level: {state.level.name}")
```
