#!/usr/bin/env python3
"""UserPromptSubmit command hook: inject current DP phase as context."""
import json, sys, os

latest = os.path.expanduser("~/.claude/events/disciplined-process-latest.json")
try:
    with open(latest) as f:
        event = json.load(f)
    phase = event.get("to_phase", "")
    task_id = event.get("task_id", "")
    if phase and phase != "none":
        parts = [f"DP phase: {phase}"]
        if task_id:
            parts.append(f"task: {task_id}")
        json.dump({"additionalContext": "[" + ", ".join(parts) + "]"}, sys.stdout)
except Exception:
    pass
