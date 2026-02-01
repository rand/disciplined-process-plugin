#!/usr/bin/env python3
"""
Pre-commit check for disciplined process.

Runs tests and validates spec compliance before allowing commit.
Respects degradation level for graceful operation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib import DPConfig, EnforcementLevel, get_config
from lib.degradation import DegradationLevel, get_current_level, is_feature_available
from lib.providers import error, feedback, get_project_dir


def detect_project_type(project_dir: Path) -> str | None:
    """Detect the project type based on config files."""
    if (project_dir / "package.json").exists():
        return "node"
    if (project_dir / "Cargo.toml").exists():
        return "rust"
    if (project_dir / "pyproject.toml").exists() or (project_dir / "setup.py").exists():
        return "python"
    if (project_dir / "go.mod").exists():
        return "go"
    if (project_dir / "build.zig").exists():
        return "zig"
    return None


def run_tests(project_dir: Path) -> tuple[bool, str]:
    """
    Run tests for the detected project type.

    Returns (success, output).
    """
    project_type = detect_project_type(project_dir)

    if project_type is None:
        return True, "No test framework detected"

    try:
        match project_type:
            case "node":
                # Check if test script exists
                package_json = project_dir / "package.json"
                content = package_json.read_text()
                if '"test"' not in content:
                    return True, "No test script in package.json"

                result = subprocess.run(
                    ["npm", "test", "--", "--passWithNoTests"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=project_dir,
                )

            case "rust":
                result = subprocess.run(
                    ["cargo", "test"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=project_dir,
                )

            case "python":
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-x"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=project_dir,
                )

            case "go":
                result = subprocess.run(
                    ["go", "test", "./..."],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=project_dir,
                )

            case "zig":
                result = subprocess.run(
                    ["zig", "build", "test"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=project_dir,
                )

            case _:
                return True, f"Unknown project type: {project_type}"

        output = result.stdout + result.stderr
        return result.returncode == 0, output

    except subprocess.TimeoutExpired:
        return False, "Test timeout exceeded"
    except FileNotFoundError as e:
        return True, f"Test runner not found: {e}"


def get_staged_source_files(project_dir: Path) -> list[Path]:
    """Get list of staged source files (excluding tests)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=project_dir,
        )
        if result.returncode != 0:
            return []

        source_extensions = {".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go", ".zig"}
        test_patterns = {"test", "spec", "_test.", ".test."}

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            path = Path(line)
            # Skip test files
            if any(pattern in line.lower() for pattern in test_patterns):
                continue
            # Only source files
            if path.suffix in source_extensions:
                files.append(project_dir / path)

        return files
    except (subprocess.SubprocessError, OSError):
        return []


def check_trace_markers(files: list[Path]) -> list[Path]:
    """
    Check files for @trace SPEC-XX.YY markers.

    Returns list of files missing markers.
    """
    missing = []
    for file_path in files:
        try:
            content = file_path.read_text()
            if "@trace SPEC-" not in content:
                missing.append(file_path)
        except (OSError, UnicodeDecodeError):
            continue
    return missing


def main() -> int:
    """Main entry point."""
    project_dir = get_project_dir()

    # Check degradation level
    level = get_current_level()
    if level == DegradationLevel.SAFE:
        print("⚠️ Safe mode active - skipping pre-commit checks")
        return 0

    try:
        config = get_config()
    except Exception:
        # If config can't be loaded, use defaults
        config = DPConfig()

    enforcement = config.enforcement.level

    # In minimal mode, skip all checks
    if enforcement == EnforcementLevel.MINIMAL:
        return 0

    # Check if features are available at current degradation level
    if not is_feature_available("pre_commit_checks"):
        print("⚠️ Pre-commit checks disabled in current mode")
        return 0

    print("🔍 Running pre-commit checks...")
    failed = False

    # Run tests
    test_enforcement = config.enforcement.effective_level("pre_commit_tests")
    success, output = run_tests(project_dir)

    if not success:
        print()
        print("❌ Tests failed. Fix tests before committing.")
        if output:
            # Truncate output for display
            lines = output.split("\n")
            if len(lines) > 20:
                print("\n".join(lines[:10]))
                print(f"... ({len(lines) - 20} more lines) ...")
                print("\n".join(lines[-10:]))
            else:
                print(output)

        if test_enforcement == EnforcementLevel.STRICT:
            failed = True
        else:
            print("⚠️  Continuing in guided mode despite test failures")

    # Check trace markers
    trace_enforcement = config.enforcement.effective_level("trace_markers")
    staged_files = get_staged_source_files(project_dir)
    missing_traces = check_trace_markers(staged_files)

    if missing_traces:
        print()
        for file_path in missing_traces:
            print(f"⚠️  Missing @trace marker: {file_path.relative_to(project_dir)}")

        if trace_enforcement == EnforcementLevel.STRICT:
            print()
            print(f"❌ {len(missing_traces)} files missing @trace SPEC-XX.YY markers")
            print("   Add trace markers linking implementation to specifications.")
            failed = True
        else:
            print()
            print(f"⚠️  {len(missing_traces)} files missing trace markers (non-blocking in guided mode)")

    if failed:
        print()
        print("Commit blocked. Fix issues above or use --no-verify to bypass (not recommended).")
        return 1

    print("✅ Pre-commit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
