#!/usr/bin/env python3
"""UserPromptSubmit command hook: inject current DP phase and rigor tier as context."""
import json, sys, os, subprocess

PRIORITY_TO_RIGOR = {
    0: "large",    # P0 critical
    1: "large",    # P1 high
    2: "medium",   # P2 medium
    3: "trivial",  # P3 low
    4: "trivial",  # P4 backlog
}

latest = os.path.expanduser("~/.claude/events/disciplined-process-latest.json")
try:
    with open(latest) as f:
        event = json.load(f)
    phase = event.get("to_phase", "")
    task_id = event.get("task_id", "")
    if not phase or phase == "none":
        sys.exit(0)

    parts = [f"DP phase: {phase}"]
    if task_id:
        parts.append(f"task: {task_id}")

    # Try to get priority from beads to determine rigor tier
    rigor = "medium"  # default
    if task_id:
        try:
            result = subprocess.run(
                ["bd", "show", task_id, "--brief"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "priority" in line.lower():
                        # Parse priority number from output
                        for word in line.split():
                            if word.isdigit():
                                rigor = PRIORITY_TO_RIGOR.get(int(word), "medium")
                                break
                        break
        except Exception:
            pass

    parts.append(f"rigor: {rigor}")

    # Write rigor back to the event file so spec-info.py can read it
    event["rigor"] = rigor
    try:
        with open(latest, "w") as f:
            json.dump(event, f)
    except Exception:
        pass

    json.dump({"additionalContext": "[" + ", ".join(parts) + "]"}, sys.stdout)
except Exception:
    pass
