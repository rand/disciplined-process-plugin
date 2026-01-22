#!/usr/bin/env python3
"""
UserPromptSubmit hook - validate spec references and inject rules.

Runs on every user prompt to:
1. Validate spec references in requests
2. Inject language-specific rules
3. Log prompt for audit trail
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


def get_prompt_from_stdin() -> str:
    """Read the user prompt from stdin (passed by Claude Code)."""
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def extract_spec_references(text: str) -> list[str]:
    """Extract SPEC-XX.YY references from text."""
    pattern = r"\[?SPEC-(\d+)\.(\d+)\]?"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [f"SPEC-{m[0]}.{m[1]}" for m in matches]


def validate_spec_exists(spec_id: str, project_dir: Path) -> bool:
    """Check if a spec ID exists in the spec directory."""
    spec_dir = project_dir / "docs" / "spec"
    if not spec_dir.is_dir():
        return True  # No spec dir, assume valid

    # Search for the spec ID in any markdown file
    for md_file in spec_dir.glob("**/*.md"):
        try:
            content = md_file.read_text()
            if f"[{spec_id}]" in content:
                return True
        except (OSError, UnicodeDecodeError):
            continue

    return False


def detect_language_from_prompt(prompt: str) -> list[str]:
    """Detect programming languages mentioned in the prompt."""
    languages = []

    lang_patterns = {
        "python": r"\b(python|\.py|pytest|pip|django|flask)\b",
        "typescript": r"\b(typescript|\.ts|\.tsx|npm|yarn|react|next)\b",
        "javascript": r"\b(javascript|\.js|\.jsx|node)\b",
        "rust": r"\b(rust|\.rs|cargo|rustc)\b",
        "go": r"\b(golang|\.go|go\s+build|go\s+run)\b",
    }

    for lang, pattern in lang_patterns.items():
        if re.search(pattern, prompt, re.IGNORECASE):
            languages.append(lang)

    return languages


def get_language_rules(languages: list[str], project_dir: Path) -> str:
    """Get language-specific rules to inject."""
    rules = []
    rules_dir = project_dir / ".claude" / "rules"

    if not rules_dir.is_dir():
        return ""

    for lang in languages:
        rule_file = rules_dir / f"{lang}.md"
        if rule_file.exists():
            try:
                content = rule_file.read_text()
                rules.append(f"## {lang.title()} Rules\n{content}")
            except (OSError, UnicodeDecodeError):
                continue

    return "\n\n".join(rules)


def log_prompt_audit(prompt: str, project_dir: Path) -> None:
    """Log prompt for audit trail (if enabled)."""
    audit_dir = project_dir / ".claude" / "audit"
    if not audit_dir.exists():
        return  # Audit logging not enabled

    # Append to daily audit log
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = audit_dir / f"prompts-{today}.jsonl"

    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
        with open(audit_file, "a") as f:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "prompt_preview": prompt[:200],
                "length": len(prompt),
            }
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # Audit logging is best-effort


def main() -> int:
    """Main entry point."""
    try:
        project_dir = get_project_dir()
        config = get_config()
        prompt = get_prompt_from_stdin()

        if not prompt:
            return 0  # No prompt to validate

        # Extract and validate spec references
        spec_refs = extract_spec_references(prompt)
        invalid_specs = []

        for spec_id in spec_refs:
            if not validate_spec_exists(spec_id, project_dir):
                invalid_specs.append(spec_id)

        # Handle invalid specs based on enforcement level
        if invalid_specs:
            if config.enforcement == EnforcementLevel.STRICT:
                # Block the prompt
                print(
                    json.dumps({
                        "error": f"Invalid spec references: {', '.join(invalid_specs)}. "
                        "These specs do not exist in docs/spec/."
                    })
                )
                return 2  # Block operation
            else:
                # Warn but allow
                feedback(
                    f"Warning: Referenced specs not found: {', '.join(invalid_specs)}"
                )

        # Detect languages and inject rules
        languages = detect_language_from_prompt(prompt)
        if languages:
            rules = get_language_rules(languages, project_dir)
            if rules:
                print(
                    json.dumps({
                        "additionalContext": rules,
                    })
                )

        # Log for audit (if enabled)
        log_prompt_audit(prompt, project_dir)

        return 0

    except Exception as e:
        # Hooks should never crash
        feedback(f"Warning: Prompt guard error: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
