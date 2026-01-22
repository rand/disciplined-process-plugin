#!/usr/bin/env python3
"""
PreToolUse hook - block protected files and enforce spec-first workflow.

Runs before Edit/Write/MultiEdit operations to:
1. Block modifications to protected files
2. Enforce spec-first in strict mode
3. Warn about missing @trace markers
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import DPConfig, EnforcementLevel, get_config
from lib.providers import feedback, get_project_dir


# Default protected file patterns
DEFAULT_PROTECTED_PATTERNS = [
    r"\.env$",
    r"\.env\.\w+$",
    r"secrets?\.(json|yaml|yml|toml)$",
    r"credentials?\.(json|yaml|yml|toml)$",
    r"\.ssh/",
    r"\.aws/",
    r"\.claude/settings\.json$",  # Don't auto-modify Claude settings
]


def get_tool_input() -> dict:
    """Read tool input from environment or stdin."""
    # Claude Code passes tool info via environment
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if tool_input:
        try:
            return json.loads(tool_input)
        except json.JSONDecodeError:
            pass

    # Fallback to stdin
    if not sys.stdin.isatty():
        try:
            return json.loads(sys.stdin.read())
        except json.JSONDecodeError:
            pass

    return {}


def get_file_path_from_input(tool_input: dict) -> str | None:
    """Extract file path from tool input."""
    # Different tools use different field names
    return (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("filePath")
    )


def is_protected_file(file_path: str, config: DPConfig) -> tuple[bool, str]:
    """Check if a file is protected from modification."""
    # Get custom patterns from config or use defaults
    patterns = DEFAULT_PROTECTED_PATTERNS

    for pattern in patterns:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True, f"File matches protected pattern: {pattern}"

    return False, ""


def check_spec_first(file_path: str, project_dir: Path, config: DPConfig) -> tuple[bool, str]:
    """Check if spec-first workflow is being followed."""
    if config.enforcement != EnforcementLevel.STRICT:
        return True, ""

    # Only enforce for source code files
    code_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}
    ext = Path(file_path).suffix.lower()

    if ext not in code_extensions:
        return True, ""

    # Check if file has linked spec
    full_path = project_dir / file_path
    if not full_path.exists():
        # New file - check if there's a spec for this area
        # For now, just warn
        return True, ""

    try:
        content = full_path.read_text()
        # Check for @trace markers
        if "@trace SPEC-" not in content and "# @trace" not in content:
            return False, (
                f"No @trace markers found in {file_path}. "
                "In strict mode, code must reference specs."
            )
    except (OSError, UnicodeDecodeError):
        pass

    return True, ""


def check_has_trace_for_new_code(
    file_path: str, new_content: str, config: DPConfig
) -> tuple[bool, str]:
    """Check if new code has @trace markers (in strict mode)."""
    if config.enforcement != EnforcementLevel.STRICT:
        return True, ""

    # Only check for function definitions without trace markers
    code_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"}
    ext = Path(file_path).suffix.lower()

    if ext not in code_extensions:
        return True, ""

    # Look for function definitions
    function_patterns = [
        r"^\s*def\s+\w+\s*\(",  # Python
        r"^\s*async\s+def\s+\w+\s*\(",  # Python async
        r"^\s*function\s+\w+\s*\(",  # JavaScript
        r"^\s*(?:async\s+)?(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\(",  # JS arrow
        r"^\s*func\s+\w+\s*\(",  # Go
        r"^\s*(?:pub\s+)?fn\s+\w+\s*\(",  # Rust
    ]

    lines = new_content.split("\n")
    warnings = []

    for i, line in enumerate(lines):
        for pattern in function_patterns:
            if re.match(pattern, line):
                # Check if previous lines have @trace
                has_trace = False
                for j in range(max(0, i - 5), i):
                    if "@trace" in lines[j].lower():
                        has_trace = True
                        break

                if not has_trace:
                    # Extract function name
                    name_match = re.search(r"(?:def|function|func|fn)\s+(\w+)", line)
                    func_name = name_match.group(1) if name_match else "unknown"
                    warnings.append(f"Function '{func_name}' at line {i + 1}")
                break

    if warnings:
        return False, (
            f"New functions without @trace markers in {file_path}:\n"
            + "\n".join(f"  - {w}" for w in warnings[:3])
            + ("\n  ..." if len(warnings) > 3 else "")
        )

    return True, ""


def main() -> int:
    """Main entry point."""
    try:
        project_dir = get_project_dir()
        config = get_config()
        tool_input = get_tool_input()

        file_path = get_file_path_from_input(tool_input)
        if not file_path:
            return 0  # No file path, allow operation

        # Check if file is protected
        is_protected, reason = is_protected_file(file_path, config)
        if is_protected:
            print(
                json.dumps({
                    "decision": "deny",
                    "reason": f"Protected file: {reason}",
                })
            )
            return 2  # Block operation

        # Check spec-first workflow
        spec_ok, spec_reason = check_spec_first(file_path, project_dir, config)
        if not spec_ok:
            if config.enforcement == EnforcementLevel.STRICT:
                print(
                    json.dumps({
                        "decision": "deny",
                        "reason": spec_reason,
                    })
                )
                return 2  # Block operation
            else:
                feedback(f"Warning: {spec_reason}")

        # Check new content for @trace markers (if available)
        new_content = tool_input.get("new_content") or tool_input.get("content", "")
        if new_content:
            trace_ok, trace_reason = check_has_trace_for_new_code(
                file_path, new_content, config
            )
            if not trace_ok:
                if config.enforcement == EnforcementLevel.STRICT:
                    print(
                        json.dumps({
                            "decision": "deny",
                            "reason": trace_reason,
                        })
                    )
                    return 2
                else:
                    feedback(f"Warning: {trace_reason}")

        # Allow operation
        print(json.dumps({"decision": "allow"}))
        return 0

    except Exception as e:
        # Hooks should never crash - allow operation on error
        feedback(f"Warning: Pre-edit hook error: {e}")
        print(json.dumps({"decision": "allow"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
