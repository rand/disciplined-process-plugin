#!/usr/bin/env python3
"""Stop command hook: report uncommitted changes and open tasks."""
import json, sys, subprocess

# Read and discard stdin to avoid broken pipe errors
try:
    sys.stdin.read()
except Exception:
    pass

findings = []
try:
    r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0 and r.stdout.strip():
        lines = r.stdout.strip().split("\n")
        findings.append(f"{len(lines)} uncommitted change(s)")
except Exception:
    pass
try:
    r = subprocess.run(["bd", "list", "--status=in_progress", "--brief"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0 and r.stdout.strip() and "No issues" not in r.stdout:
        count = len([l for l in r.stdout.strip().split("\n") if l.strip()])
        findings.append(f"{count} in-progress task(s)")
except Exception:
    pass
try:
    r = subprocess.run(["bd", "ready", "--brief"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0 and r.stdout.strip() and "No issues" not in r.stdout:
        count = len([l for l in r.stdout.strip().split("\n") if l.strip()])
        findings.append(f"{count} ready task(s)")
except Exception:
    pass

if findings:
    json.dump({"decision": "approve", "additionalContext": "Session end: " + "; ".join(findings) + ". Consider committing, syncing (bd sync), and closing tasks."}, sys.stdout)
else:
    json.dump({"decision": "approve"}, sys.stdout)
