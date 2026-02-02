#!/usr/bin/env python3
"""PreToolUse command hook: check spec references in edited files. Never blocks."""
import json, sys, os, re

try:
    inp = json.load(sys.stdin)
    tool_input = json.loads(inp.get("toolInput", "{}")) if isinstance(inp.get("toolInput"), str) else inp.get("toolInput", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)
    # Skip test/spec/doc/config files
    skip = ["/test", "/spec/", "/docs/", ".test.", ".spec.", "_test.", ".json", ".toml", ".yaml", ".yml", ".md", ".lock"]
    if any(x in file_path for x in skip):
        sys.exit(0)
    # Check if file exists and has SPEC references
    if os.path.exists(file_path):
        with open(file_path, errors="replace") as f:
            content = f.read(50000)  # cap read size
        specs = set(re.findall(r"SPEC-\d+\.\d+", content))
        if specs:
            json.dump({"decision": "approve", "reason": f"Spec refs in file: {', '.join(sorted(specs))}"}, sys.stdout)
        else:
            json.dump({"decision": "approve", "reason": "No SPEC refs in this file."}, sys.stdout)
    else:
        # New file
        json.dump({"decision": "approve", "reason": "New file (no existing spec refs)."}, sys.stdout)
except Exception:
    # Never fail, never block
    pass
