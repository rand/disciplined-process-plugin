#!/usr/bin/env python3
"""
PostToolUse hook - run formatters and update traceability.

Runs after Edit/Write/MultiEdit operations to:
1. Run code formatters (prettier, black, gofmt, etc.)
2. Update traceability index
3. Validate @trace markers
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import DPConfig, get_config
from lib.providers import feedback, get_project_dir


# Formatter configurations by file extension
FORMATTERS = {
    ".py": {
        "commands": [
            ["black", "--quiet", "{file}"],
            ["ruff", "format", "--quiet", "{file}"],
        ],
        "check_installed": ["black", "--version"],
    },
    ".ts": {
        "commands": [["prettier", "--write", "{file}"]],
        "check_installed": ["prettier", "--version"],
    },
    ".tsx": {
        "commands": [["prettier", "--write", "{file}"]],
        "check_installed": ["prettier", "--version"],
    },
    ".js": {
        "commands": [["prettier", "--write", "{file}"]],
        "check_installed": ["prettier", "--version"],
    },
    ".jsx": {
        "commands": [["prettier", "--write", "{file}"]],
        "check_installed": ["prettier", "--version"],
    },
    ".json": {
        "commands": [["prettier", "--write", "{file}"]],
        "check_installed": ["prettier", "--version"],
    },
    ".go": {
        "commands": [["gofmt", "-w", "{file}"]],
        "check_installed": ["gofmt", "-h"],
    },
    ".rs": {
        "commands": [["rustfmt", "{file}"]],
        "check_installed": ["rustfmt", "--version"],
    },
}


def get_tool_input() -> dict:
    """Read tool input from environment or stdin."""
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if tool_input:
        try:
            return json.loads(tool_input)
        except json.JSONDecodeError:
            pass

    if not sys.stdin.isatty():
        try:
            return json.loads(sys.stdin.read())
        except json.JSONDecodeError:
            pass

    return {}


def get_file_path_from_input(tool_input: dict) -> str | None:
    """Extract file path from tool input."""
    return (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("filePath")
    )


def is_formatter_available(check_cmd: list[str]) -> bool:
    """Check if a formatter is installed."""
    try:
        subprocess.run(
            check_cmd,
            capture_output=True,
            timeout=5,
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def run_formatter(file_path: str, project_dir: Path) -> bool:
    """Run the appropriate formatter for a file."""
    ext = Path(file_path).suffix.lower()

    if ext not in FORMATTERS:
        return True  # No formatter needed

    formatter_config = FORMATTERS[ext]

    # Check if formatter is available
    if not is_formatter_available(formatter_config["check_installed"]):
        return True  # Formatter not installed, skip silently

    full_path = project_dir / file_path
    if not full_path.exists():
        return True

    # Try each formatter command
    for cmd_template in formatter_config["commands"]:
        cmd = [part.replace("{file}", str(full_path)) for part in cmd_template]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                cwd=project_dir,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue

    return False


def extract_trace_markers(file_path: str, project_dir: Path) -> list[str]:
    """Extract @trace markers from a file."""
    full_path = project_dir / file_path
    if not full_path.exists():
        return []

    markers = []
    try:
        content = full_path.read_text()
        import re

        pattern = r"@trace\s+(SPEC-\d+\.\d+(?:\.\w+)?)"
        matches = re.findall(pattern, content, re.IGNORECASE)
        markers.extend(matches)
    except (OSError, UnicodeDecodeError):
        pass

    return markers


def update_traceability_index(
    file_path: str, markers: list[str], project_dir: Path
) -> None:
    """Update the traceability index file."""
    index_dir = project_dir / ".claude" / "traceability"
    index_file = index_dir / "index.json"

    # Load existing index
    index: dict = {}
    if index_file.exists():
        try:
            index = json.loads(index_file.read_text())
        except (json.JSONDecodeError, OSError):
            index = {}

    # Update index
    if "files" not in index:
        index["files"] = {}

    if markers:
        index["files"][file_path] = {
            "markers": markers,
            "updated": __import__("datetime").datetime.now().isoformat(),
        }
    elif file_path in index["files"]:
        # Remove file if no markers
        del index["files"][file_path]

    # Save index
    try:
        index_dir.mkdir(parents=True, exist_ok=True)
        index_file.write_text(json.dumps(index, indent=2))
    except OSError:
        pass


def validate_trace_markers(markers: list[str], project_dir: Path) -> list[str]:
    """Validate that traced specs exist."""
    invalid = []
    spec_dir = project_dir / "docs" / "spec"

    if not spec_dir.is_dir():
        return []  # No spec dir, can't validate

    for marker in markers:
        found = False
        for md_file in spec_dir.glob("**/*.md"):
            try:
                content = md_file.read_text()
                if f"[{marker}]" in content:
                    found = True
                    break
            except (OSError, UnicodeDecodeError):
                continue

        if not found:
            invalid.append(marker)

    return invalid


def main() -> int:
    """Main entry point."""
    try:
        project_dir = get_project_dir()
        config = get_config()
        tool_input = get_tool_input()

        file_path = get_file_path_from_input(tool_input)
        if not file_path:
            return 0

        # Run formatter
        if not run_formatter(file_path, project_dir):
            feedback(f"Warning: Formatter failed for {file_path}")

        # Extract and update trace markers
        markers = extract_trace_markers(file_path, project_dir)
        if markers:
            update_traceability_index(file_path, markers, project_dir)

            # Validate markers
            invalid = validate_trace_markers(markers, project_dir)
            if invalid:
                feedback(
                    f"Warning: Invalid @trace markers in {file_path}: "
                    f"{', '.join(invalid)}"
                )

        # Output success
        output = {"success": True}
        if markers:
            output["trace_markers"] = markers

        print(json.dumps(output))
        return 0

    except Exception as e:
        feedback(f"Warning: Post-edit hook error: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
