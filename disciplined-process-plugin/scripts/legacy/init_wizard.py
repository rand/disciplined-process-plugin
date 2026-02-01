#!/usr/bin/env python3
"""
Initialization wizard for disciplined-process plugin.

Guides users through project setup with interactive prompts.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import TaskTracker


@dataclass
class WizardConfig:
    """Configuration collected by the wizard."""

    project_name: str = ""
    languages: list[str] = field(default_factory=list)
    task_tracker: TaskTracker = TaskTracker.BEADS
    enforcement: str = "guided"
    adversarial_enabled: bool = True
    adversarial_model: str = "gemini-2.5-flash"
    migrate_from_beads: bool = False


def detect_project_name(project_dir: Path) -> str:
    """Detect project name from package files."""
    # Check package.json
    package_json = project_dir / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            if "name" in data:
                return data["name"]
        except (json.JSONDecodeError, OSError):
            pass

    # Check Cargo.toml
    cargo_toml = project_dir / "Cargo.toml"
    if cargo_toml.exists():
        try:
            content = cargo_toml.read_text()
            for line in content.split("\n"):
                if line.startswith("name"):
                    return line.split("=")[1].strip().strip('"\'')
        except OSError:
            pass

    # Check pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            for line in content.split("\n"):
                if line.startswith("name"):
                    return line.split("=")[1].strip().strip('"\'')
        except OSError:
            pass

    # Fallback to directory name
    return project_dir.name


def detect_languages(project_dir: Path) -> list[str]:
    """Detect programming languages used in the project."""
    languages = []

    extensions = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".zig": "zig",
        ".java": "java",
        ".swift": "swift",
    }

    found = set()
    for ext, lang in extensions.items():
        # Check if any files with this extension exist
        if list(project_dir.glob(f"**/*{ext}"))[:1]:
            found.add(lang)

    # Prioritize certain languages
    priority = ["python", "typescript", "rust", "go", "javascript", "java", "swift", "zig"]
    for lang in priority:
        if lang in found:
            languages.append(lang)

    return languages[:3]  # Limit to top 3


def check_cli_available(command: str) -> bool:
    """Check if a CLI command is available."""
    return shutil.which(command) is not None


def check_tracker_availability(project_dir: Path) -> dict[str, dict]:
    """Check which task trackers are available."""
    trackers = {
        "beads": {
            "available": check_cli_available("bd"),
            "initialized": (project_dir / ".beads").is_dir(),
            "install": "brew install beads  # or: npm i -g beads-cli",
        },
        "builtin": {
            "available": True,  # Always available - Claude Code native
            "initialized": True,
            "install": None,
        },
        "chainlink": {
            "available": check_cli_available("chainlink"),
            "initialized": (project_dir / ".chainlink").is_dir(),
            "install": "(requires private source access)",
        },
        "github": {
            "available": check_cli_available("gh"),
            "initialized": True,  # Just needs CLI
            "install": "brew install gh",
        },
        "linear": {
            "available": check_cli_available("linear"),
            "initialized": True,
            "install": "npm install -g @linear/cli",
        },
        "markdown": {
            "available": True,
            "initialized": True,
            "install": None,
        },
        "none": {
            "available": True,
            "initialized": True,
            "install": None,
        },
    }
    return trackers


def create_config_file(config: WizardConfig, project_dir: Path) -> None:
    """Create the dp-config.yaml file."""
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    config_content = f"""# Disciplined Process Configuration v2
version: "2.0"

project:
  name: "{config.project_name}"
  languages:
{chr(10).join(f'    - {lang}' for lang in config.languages)}

# Issue tracker selection
task_tracker: {config.task_tracker.value}

# Beads-specific configuration (recommended)
beads:
  auto_sync: true
  daemon: true
  prefix: null

# Builtin-specific configuration (Claude Code native)
builtin:
  task_list_id: null  # Auto-generated from project path
  auto_set_env: true

# Chainlink-specific configuration (requires private source access)
chainlink:
  features:
    sessions: true
    milestones: true
    time_tracking: true
  rules_path: .claude/rules/

# Enforcement level
enforcement: {config.enforcement}

# Adversarial review configuration
adversarial_review:
  enabled: {str(config.adversarial_enabled).lower()}
  model: {config.adversarial_model}
  max_iterations: 5

# Spec configuration
specs:
  directory: docs/spec/
  id_format: "SPEC-{{section:02d}}.{{item:02d}}"

# ADR configuration
adrs:
  directory: docs/adr/
  template: .claude/templates/adr.md

# Degradation behavior
degradation:
  on_tracker_unavailable: warn
  on_hook_failure: warn
"""

    config_file = claude_dir / "dp-config.yaml"
    config_file.write_text(config_content)


def create_settings_file(config: WizardConfig, project_dir: Path) -> None:
    """Create or update .claude/settings.json with hooks."""
    claude_dir = project_dir / ".claude"
    settings_file = claude_dir / "settings.json"

    # Load existing settings or create new
    settings: dict[str, Any] = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            pass

    # Add hooks configuration
    settings["hooks"] = {
        "SessionStart": [
            {
                "matcher": "startup|resume",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'uv run "$CLAUDE_PROJECT_DIR"/.claude/hooks/session_start.py',
                        "timeout": 10,
                    }
                ],
            }
        ],
        "UserPromptSubmit": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'uv run "$CLAUDE_PROJECT_DIR"/.claude/hooks/prompt_guard.py',
                        "timeout": 5,
                    }
                ],
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'uv run "$CLAUDE_PROJECT_DIR"/.claude/hooks/pre_edit.py',
                        "timeout": 5,
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'uv run "$CLAUDE_PROJECT_DIR"/.claude/hooks/post_edit.py',
                        "timeout": 30,
                    }
                ],
            }
        ],
        "Stop": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'uv run "$CLAUDE_PROJECT_DIR"/.claude/hooks/stop_handler.py',
                        "timeout": 10,
                    }
                ],
            }
        ],
    }

    settings_file.write_text(json.dumps(settings, indent=2))


def create_language_rules(languages: list[str], project_dir: Path) -> list[str]:
    """Create language-specific rule files."""
    rules_dir = project_dir / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    created = []

    rules_content = {
        "python": """# Python Rules

## Code Style
- Use type hints for all function signatures
- Follow PEP 8 naming conventions
- Use `pathlib.Path` instead of `os.path`
- Prefer f-strings over `.format()` or `%`

## Error Handling
- Never use bare `except:` clauses
- Always specify exception types
- Log errors before re-raising

## Testing
- Use pytest for all tests
- Include `@trace SPEC-XX.YY` markers
- Test edge cases: None, empty, negative

## Security
- Never hardcode credentials
- Use `secrets` module for tokens
- Validate all external input
""",
        "typescript": """# TypeScript Rules

## Code Style
- Use strict TypeScript (`strict: true`)
- Prefer `interface` over `type` for objects
- Use `readonly` where applicable
- Avoid `any` - use `unknown` if needed

## Error Handling
- Use custom error classes
- Always handle Promise rejections
- Avoid swallowing errors silently

## Testing
- Use describe/it blocks with clear names
- Include `// @trace SPEC-XX.YY` markers
- Mock external dependencies

## Security
- Sanitize user input
- Use parameterized queries
- Never expose stack traces
""",
        "go": """# Go Rules

## Code Style
- Follow effective Go guidelines
- Use meaningful variable names
- Keep functions focused and small

## Error Handling
- Always check returned errors
- Wrap errors with context
- Use sentinel errors for known cases

## Testing
- Use table-driven tests
- Include `// @trace SPEC-XX.YY` markers
- Use testify for assertions
""",
        "rust": """# Rust Rules

## Code Style
- Use `rustfmt` for formatting
- Prefer `Result` over `panic!`
- Use `clippy` for linting

## Error Handling
- Use `?` operator for propagation
- Create domain-specific error types
- Implement `std::error::Error`

## Testing
- Include `// @trace SPEC-XX.YY` markers
- Use `#[test]` attribute
- Test with `cargo test`
""",
    }

    for lang in languages:
        if lang in rules_content:
            rule_file = rules_dir / f"{lang}.md"
            rule_file.write_text(rules_content[lang])
            created.append(f".claude/rules/{lang}.md")

    return created


def create_spec_template(project_dir: Path) -> None:
    """Create initial spec template."""
    spec_dir = project_dir / "docs" / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    overview = spec_dir / "00-overview.md"
    overview.write_text("""# Project Overview
[SPEC-00]

## Purpose

[SPEC-00.01] This document defines the project specifications.

## Scope

[SPEC-00.02] The system shall...

## Definitions

[SPEC-00.03] Key terms used throughout this specification:
- **Term**: Definition

## Requirements

See section-specific specification files for detailed requirements.
""")


def create_adr_template(project_dir: Path) -> None:
    """Create ADR template and initial ADR."""
    adr_dir = project_dir / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)

    # Template
    template = adr_dir / "template.md"
    template.write_text("""# ADR-NNNN: Title

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue we're addressing?

## Decision
What is the decision and rationale?

## Consequences
What are the results of this decision?

## Alternatives Considered
What other options were evaluated?
""")

    # Initial ADR
    initial = adr_dir / "0001-adopt-disciplined-process.md"
    initial.write_text("""# ADR-0001: Adopt Disciplined Process

## Status
Accepted

## Context
We need a structured approach to development that ensures:
- Traceable requirements
- Test coverage for all features
- Consistent code review
- AI-assisted development workflow

## Decision
Adopt the disciplined-process-plugin for Claude Code, which provides:
- Specification management with [SPEC-XX.YY] IDs
- Task tracking integration
- Adversarial code review
- Traceability validation

## Consequences
- All features require specification references
- Tests must include @trace markers
- Code reviews run before completion
- Hooks enforce workflow compliance

## Alternatives Considered
- Manual tracking: Too error-prone
- GitHub issues only: Lacks traceability
- No process: Technical debt accumulates
""")


def initialize_tracker(tracker: TaskTracker, project_dir: Path) -> bool:
    """Initialize the selected task tracker."""
    try:
        if tracker == TaskTracker.BEADS:
            if not (project_dir / ".beads").is_dir():
                subprocess.run(
                    ["bd", "init"],
                    cwd=project_dir,
                    capture_output=True,
                    timeout=30,
                )
            return True

        elif tracker == TaskTracker.BUILTIN:
            # Builtin requires no initialization - handled by providers.py
            # Just ensure the task list ID is set when provider is used
            return True

        elif tracker == TaskTracker.CHAINLINK:
            if not (project_dir / ".chainlink").is_dir():
                subprocess.run(
                    ["chainlink", "init"],
                    cwd=project_dir,
                    capture_output=True,
                    timeout=30,
                )
            return True

        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def run_wizard(project_dir: Path) -> WizardConfig:
    """Run the interactive wizard (for documentation - actual interaction via Claude)."""
    config = WizardConfig()

    # Detect project info
    config.project_name = detect_project_name(project_dir)
    config.languages = detect_languages(project_dir)

    # Check tracker availability
    trackers = check_tracker_availability(project_dir)

    # Default selections (wizard would prompt for these)
    # Prefer Beads (recommended, public), then Builtin (zero-config), then Chainlink (power users)
    if trackers["beads"]["available"]:
        config.task_tracker = TaskTracker.BEADS
    elif trackers["chainlink"]["available"]:
        config.task_tracker = TaskTracker.CHAINLINK
    else:
        # Builtin is always available as fallback
        config.task_tracker = TaskTracker.BUILTIN

    # Check for migration opportunity
    if config.task_tracker == TaskTracker.BEADS and trackers["chainlink"]["initialized"]:
        # Could offer to migrate from Chainlink to Beads
        pass

    return config


def execute_setup(config: WizardConfig, project_dir: Path) -> dict[str, Any]:
    """Execute the setup based on wizard configuration."""
    results = {
        "success": True,
        "created": [],
        "errors": [],
    }

    try:
        # Create config file
        create_config_file(config, project_dir)
        results["created"].append(".claude/dp-config.yaml")

        # Create settings file
        create_settings_file(config, project_dir)
        results["created"].append(".claude/settings.json")

        # Create language rules
        rules = create_language_rules(config.languages, project_dir)
        results["created"].extend(rules)

        # Create spec template
        create_spec_template(project_dir)
        results["created"].append("docs/spec/00-overview.md")

        # Create ADR template
        create_adr_template(project_dir)
        results["created"].extend([
            "docs/adr/template.md",
            "docs/adr/0001-adopt-disciplined-process.md",
        ])

        # Initialize tracker
        if not initialize_tracker(config.task_tracker, project_dir):
            results["errors"].append(f"Failed to initialize {config.task_tracker.value}")

    except Exception as e:
        results["success"] = False
        results["errors"].append(str(e))

    return results


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize disciplined process")
    parser.add_argument(
        "--project-dir", type=Path, default=Path.cwd(), help="Project directory"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    args = parser.parse_args()

    # Run wizard and setup
    config = run_wizard(args.project_dir)
    results = execute_setup(config, args.project_dir)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if results["success"]:
            print("\n" + "=" * 60)
            print("Setup Complete!")
            print("=" * 60)
            print("\nCreated:")
            for item in results["created"]:
                print(f"  [x] {item}")
            if results["errors"]:
                print("\nWarnings:")
                for err in results["errors"]:
                    print(f"  [!] {err}")
            print("\nRun '/dp:help' for command reference.")
        else:
            print("\nSetup failed:")
            for err in results["errors"]:
                print(f"  - {err}")

    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
