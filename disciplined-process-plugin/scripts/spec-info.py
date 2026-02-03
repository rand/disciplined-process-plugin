#!/usr/bin/env python3
"""PreToolUse command hook: check spec references in edited files.

Phase-aware: blocks implementation files without spec refs when the project
uses specs and the DP phase is 'implement' or 'review'.
"""
import json, sys, os, re
from pathlib import Path

SKIP_PATTERNS = [
    "/test", "/tests/", "/spec/", "/docs/", "/migrations/",
    ".test.", ".spec.", "_test.", ".json", ".toml", ".yaml", ".yml",
    ".md", ".lock", ".csv", ".svg", ".png", ".jpg", ".gif",
    "/generated/", ".generated.", ".g.", "__pycache__",
    "conftest.py", "setup.py", "setup.cfg", "pyproject.toml",
    "Makefile", "Dockerfile", ".gitignore", ".env",
]

IMPL_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".zig",
    ".java", ".kt", ".swift", ".c", ".cpp", ".h",
}


def get_phase_and_rigor():
    """Read current DP phase and rigor from the latest event file."""
    latest = os.path.expanduser("~/.claude/events/disciplined-process-latest.json")
    try:
        with open(latest) as f:
            event = json.load(f)
        phase = event.get("to_phase", "")
        rigor = event.get("rigor", "")
        return phase, rigor
    except Exception:
        return "", ""


def project_has_specs(file_path: str) -> bool:
    """Check if any SPEC-XX.YY files exist in docs/spec/ relative to the file's project."""
    p = Path(file_path).resolve()
    # Walk up to find a docs/spec/ directory
    for parent in [p.parent] + list(p.parents):
        spec_dir = parent / "docs" / "spec"
        if spec_dir.is_dir():
            for spec_file in spec_dir.iterdir():
                if spec_file.suffix == ".md":
                    try:
                        content = spec_file.read_text(errors="replace")[:50000]
                        if re.search(r"SPEC-\d+\.\d+", content):
                            return True
                    except Exception:
                        continue
            return False
        # Stop at git root
        if (parent / ".git").exists():
            break
    return False


def is_skip_file(file_path: str) -> bool:
    """Check if this file should skip spec enforcement."""
    lower = file_path.lower()
    if any(pat in lower for pat in SKIP_PATTERNS):
        return True
    ext = Path(file_path).suffix
    if ext and ext not in IMPL_EXTENSIONS:
        return True
    return False


def file_has_spec_refs(file_path: str) -> set[str]:
    """Check if file has SPEC references."""
    if os.path.exists(file_path):
        try:
            with open(file_path, errors="replace") as f:
                content = f.read(50000)
            return set(re.findall(r"SPEC-\d+\.\d+", content))
        except Exception:
            pass
    return set()


def approve(reason: str):
    json.dump({"decision": "approve", "reason": reason}, sys.stdout)


def deny(reason: str):
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, sys.stdout)


def main():
    try:
        inp = json.load(sys.stdin)
        tool_input = json.loads(inp.get("toolInput", "{}")) if isinstance(inp.get("toolInput"), str) else inp.get("toolInput", {})
        file_path = tool_input.get("file_path", "")
        if not file_path:
            approve("No file path")
            return

        if is_skip_file(file_path):
            approve("Skipped file (test/doc/config/non-impl)")
            return

        specs = file_has_spec_refs(file_path)
        if specs:
            approve(f"Spec refs in file: {', '.join(sorted(specs))}")
            return

        # Check phase
        phase, rigor = get_phase_and_rigor()

        # Only enforce during implement/review phases
        if phase not in ("implement", "review"):
            if specs:
                approve(f"Spec refs: {', '.join(sorted(specs))}")
            else:
                approve(f"No SPEC refs (phase: {phase or 'unknown'}, not enforcing)")
            return

        # Trivial rigor → don't block
        if rigor == "trivial":
            approve("No SPEC refs (trivial rigor, not enforcing)")
            return

        # Check if project uses specs at all
        if not project_has_specs(file_path):
            approve("No SPEC refs (project has no specs yet)")
            return

        # Project has specs, we're in implement/review, file is impl with no refs → deny
        deny(
            "This project uses specs but this implementation file has no SPEC references. "
            "To proceed, pick one: "
            "(1) Add a SPEC reference comment to the file (e.g. `# @trace SPEC-XX.YY`), "
            "(2) Create a spec with `/dp:spec add` if this is a new feature, "
            "(3) Ask the user if this is a trivial change that can skip spec tracing — "
            "if they confirm, set rigor to trivial with "
            "`/dp:task update <id> --priority 3` and retry."
        )
    except Exception:
        # Never crash, approve on error
        approve("Error in spec-info hook (approving)")


if __name__ == "__main__":
    main()
