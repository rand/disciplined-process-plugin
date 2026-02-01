#!/usr/bin/env python3
"""
Post-write hook - check for @trace SPEC-XX.YY markers in implementation files.

Called after file writes to remind about traceability.
Non-blocking - provides guidance only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.providers import feedback


# File extensions and their comment syntax
COMMENT_SYNTAX: dict[str, str] = {
    # C-style comments
    ".ts": "//",
    ".tsx": "//",
    ".js": "//",
    ".jsx": "//",
    ".go": "//",
    ".rs": "//",
    ".zig": "//",
    ".c": "//",
    ".cpp": "//",
    ".h": "//",
    ".hpp": "//",
    ".java": "//",
    ".swift": "//",
    ".kt": "//",
    # Hash comments
    ".py": "#",
    ".rb": "#",
    ".sh": "#",
    ".bash": "#",
    ".zsh": "#",
}

# Patterns that indicate test files
TEST_PATTERNS = {"test", "spec", "_test.", ".test."}


def is_test_file(path: str) -> bool:
    """Check if a file path is a test file."""
    path_lower = path.lower()
    return any(pattern in path_lower for pattern in TEST_PATTERNS)


def has_trace_marker(file_path: Path) -> bool:
    """Check if a file has @trace SPEC-XX.YY markers."""
    try:
        content = file_path.read_text()
        return "@trace SPEC-" in content
    except (OSError, UnicodeDecodeError):
        return True  # Assume OK if can't read


def check_file(file_path: str) -> None:
    """Check a single file for trace markers."""
    path = Path(file_path)

    # Skip if file doesn't exist
    if not path.exists():
        return

    # Skip test files
    if is_test_file(file_path):
        return

    # Skip if not a recognized source file
    if path.suffix not in COMMENT_SYNTAX:
        return

    # Skip if already has trace markers
    if has_trace_marker(path):
        return

    # Output reminder
    feedback(f"💡 Consider adding @trace SPEC-XX.YY marker to {path.name} to link implementation to specification")


def main() -> int:
    """Main entry point."""
    # Get files from argument or environment
    files_arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_FILE_PATHS", "")

    if not files_arg:
        return 0

    # Split on spaces (matches shell behavior)
    files = files_arg.split()

    for file_path in files:
        check_file(file_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
