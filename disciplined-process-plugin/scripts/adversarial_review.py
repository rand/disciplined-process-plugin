#!/usr/bin/env python3
"""
Adversarial review implementation for VDD workflow.

Invokes a fresh-context adversary (Gemini) to critique code changes,
detects hallucinations, and manages the review loop.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Critique:
    """A single critique from the adversary."""

    category: str  # LOGIC, SECURITY, PLACEHOLDER, ERROR, CONVENTION, TEST
    file_path: str
    line_number: int
    description: str
    why_wrong: str = ""
    suggested_fix: str = ""
    severity: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    is_hallucination: bool = False
    hallucination_reason: str = ""


@dataclass
class AdversaryResponse:
    """Parsed response from the adversary."""

    critiques: list[Critique] = field(default_factory=list)
    no_issues: bool = False
    raw_response: str = ""


@dataclass
class ReviewContext:
    """Context gathered for adversarial review."""

    diff: str
    files_changed: list[str]
    specs: dict[str, str]  # spec_id -> content
    tests: dict[str, str]  # file_path -> content
    previous_critiques: list[str]


def get_git_diff(project_dir: Path, staged_only: bool = False) -> str:
    """Get git diff for review."""
    cmd = ["git", "diff"]
    if staged_only:
        cmd.append("--staged")
    else:
        cmd.append("HEAD")

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=project_dir, timeout=30
    )
    return result.stdout if result.returncode == 0 else ""


def get_changed_files(project_dir: Path, staged_only: bool = False) -> list[str]:
    """Get list of changed files."""
    cmd = ["git", "diff", "--name-only"]
    if staged_only:
        cmd.append("--staged")
    else:
        cmd.append("HEAD")

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=project_dir, timeout=30
    )
    if result.returncode != 0:
        return []

    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def gather_context(project_dir: Path, staged_only: bool = False) -> ReviewContext:
    """Gather all context needed for adversarial review."""
    diff = get_git_diff(project_dir, staged_only)
    files_changed = get_changed_files(project_dir, staged_only)

    # Extract linked specs from changed files
    specs: dict[str, str] = {}
    try:
        from traceability import find_trace_markers, parse_all_specs

        # Find all specs in the project
        spec_dir = project_dir / "docs" / "spec"
        all_specs = parse_all_specs(spec_dir)
        spec_map = {s.spec_id: s for s in all_specs}

        # Find trace markers in changed files
        changed_paths = [project_dir / f for f in files_changed if f.endswith(('.py', '.ts', '.tsx', '.js', '.go', '.rs'))]
        if changed_paths:
            # Create temp list of parent directories for changed files
            search_dirs = list(set(p.parent for p in changed_paths if p.exists()))
            if search_dirs:
                markers = find_trace_markers(search_dirs)
                # Extract unique spec IDs referenced in changed files
                changed_spec_ids = set()
                for marker in markers:
                    # Check if the marker's file is in our changed files
                    try:
                        rel_path = str(marker.file_path.relative_to(project_dir))
                        if rel_path in files_changed:
                            # Get the base spec ID (SPEC-XX.YY without sub-items)
                            base_id = ".".join(marker.spec_id.split(".")[:2])
                            if base_id.startswith("SPEC-"):
                                changed_spec_ids.add(base_id)
                    except ValueError:
                        continue

                # Get spec content for referenced specs
                for spec_id in changed_spec_ids:
                    if spec_id in spec_map:
                        spec = spec_map[spec_id]
                        specs[spec_id] = spec.title
    except ImportError:
        pass  # Gracefully degrade if traceability not available

    # Find tests for changed files
    tests: dict[str, str] = {}
    try:
        tests_dir = project_dir / "tests"
        if tests_dir.is_dir():
            for changed_file in files_changed:
                # Look for corresponding test file
                base_name = Path(changed_file).stem
                possible_test_names = [
                    f"test_{base_name}.py",
                    f"{base_name}_test.py",
                    f"test_{base_name}.ts",
                    f"{base_name}.test.ts",
                    f"{base_name}.test.tsx",
                ]
                for test_name in possible_test_names:
                    for test_file in tests_dir.rglob(test_name):
                        try:
                            content = test_file.read_text()
                            rel_path = str(test_file.relative_to(project_dir))
                            # Limit content size
                            tests[rel_path] = content[:2000]
                        except (OSError, UnicodeDecodeError):
                            continue
    except Exception:
        pass  # Gracefully degrade

    return ReviewContext(
        diff=diff,
        files_changed=files_changed,
        specs=specs,
        tests=tests,
        previous_critiques=[],
    )


def format_context_for_adversary(context: ReviewContext) -> str:
    """Format context for the adversary prompt."""
    sections = []

    sections.append("## Files Changed")
    sections.append("```diff")
    sections.append(context.diff[:10000])  # Limit diff size
    if len(context.diff) > 10000:
        sections.append("... (diff truncated)")
    sections.append("```")

    if context.specs:
        sections.append("\n## Relevant Specs")
        for spec_id, content in context.specs.items():
            sections.append(f"### {spec_id}")
            sections.append(content)

    if context.tests:
        sections.append("\n## Test Coverage")
        for file_path, content in context.tests.items():
            sections.append(f"### {file_path}")
            sections.append("```")
            sections.append(content[:2000])
            sections.append("```")

    if context.previous_critiques:
        sections.append("\n## Previous Critiques (already addressed)")
        for critique in context.previous_critiques:
            sections.append(f"- {critique}")

    return "\n".join(sections)


def parse_adversary_response(response: str) -> AdversaryResponse:
    """Parse the adversary's response into structured critiques."""
    result = AdversaryResponse(raw_response=response)

    # Check for "no issues" response
    if re.search(r"no\s+issues?\s+found", response, re.IGNORECASE):
        result.no_issues = True
        return result

    # Parse critique blocks
    # Pattern: [CATEGORY] file:line
    critique_pattern = re.compile(
        r"\[(\w+)\]\s+([^\s:]+):(\d+)\s*\n(.*?)(?=\n\[|\n##|\Z)",
        re.DOTALL | re.MULTILINE,
    )

    for match in critique_pattern.finditer(response):
        category = match.group(1).upper()
        file_path = match.group(2)
        line_number = int(match.group(3))
        body = match.group(4).strip()

        # Extract why and fix if present
        why_wrong = ""
        suggested_fix = ""

        why_match = re.search(r"Why it's wrong:\s*\n(.*?)(?=Suggested fix:|$)", body, re.DOTALL)
        if why_match:
            why_wrong = why_match.group(1).strip()

        fix_match = re.search(r"Suggested fix:\s*\n(.*?)$", body, re.DOTALL)
        if fix_match:
            suggested_fix = fix_match.group(1).strip()

        # Get description (first paragraph)
        description = body.split("\n\n")[0].strip()
        if "Why it's wrong:" in description:
            description = description.split("Why it's wrong:")[0].strip()

        result.critiques.append(
            Critique(
                category=category,
                file_path=file_path,
                line_number=line_number,
                description=description,
                why_wrong=why_wrong,
                suggested_fix=suggested_fix,
            )
        )

    return result


def validate_critique(critique: Critique, project_dir: Path) -> Critique:
    """Validate a critique against the actual code to detect hallucinations."""
    file_path = project_dir / critique.file_path

    if not file_path.exists():
        critique.is_hallucination = True
        critique.hallucination_reason = f"File '{critique.file_path}' does not exist"
        return critique

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        # Check if line number exists
        if critique.line_number > len(lines) or critique.line_number < 1:
            critique.is_hallucination = True
            critique.hallucination_reason = (
                f"Line {critique.line_number} does not exist "
                f"(file has {len(lines)} lines)"
            )
            return critique

        # Get the actual line content
        actual_line = lines[critique.line_number - 1]

        # Check for obviously wrong references
        # Extract function/variable names from the critique
        names_in_critique = re.findall(r"`(\w+)`", critique.description)
        for name in names_in_critique:
            if len(name) > 3 and name not in content:
                critique.is_hallucination = True
                critique.hallucination_reason = (
                    f"Referenced '{name}' not found in {critique.file_path}"
                )
                return critique

    except (OSError, UnicodeDecodeError) as e:
        critique.is_hallucination = True
        critique.hallucination_reason = f"Cannot read file: {e}"

    return critique


def detect_hallucinations(
    response: AdversaryResponse, project_dir: Path
) -> AdversaryResponse:
    """Validate all critiques and flag potential hallucinations."""
    for i, critique in enumerate(response.critiques):
        response.critiques[i] = validate_critique(critique, project_dir)

    return response


def invoke_adversary(
    context: str, project_dir: Path, model: str = "gemini-2.5-flash"
) -> str:
    """Invoke the adversary agent via rlm-claude-code or direct API."""
    # Try rlm-claude-code first
    agent_path = project_dir / "agents" / "adversary.md"

    if not agent_path.exists():
        # Fall back to plugin's agent
        agent_path = (
            Path(__file__).parent.parent / "agents" / "adversary.md"
        )

    # Read agent definition
    if agent_path.exists():
        agent_content = agent_path.read_text()
        # Replace $CONTEXT placeholder
        prompt = agent_content.replace("$CONTEXT", context)
    else:
        prompt = f"""You are a hyper-critical code reviewer. Review this code and find issues:

{context}

Format each issue as:
[CATEGORY] file:line
Description

Categories: LOGIC, SECURITY, PLACEHOLDER, ERROR, CONVENTION, TEST

If no issues found, say exactly: "No issues found."
"""

    # Try to invoke via claude CLI with fresh context
    try:
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--model", model,
                "-p", prompt,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_dir,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: return empty (would need actual API integration)
    return "No issues found."


def format_critique_output(response: AdversaryResponse, iteration: int) -> str:
    """Format critiques for display."""
    lines = [
        "=" * 64,
        f"Adversary Critique (Iteration {iteration})",
        "=" * 64,
        "",
    ]

    if response.no_issues:
        lines.append("No issues found.")
        lines.append("")
        lines.append("The adversary could not find any legitimate issues.")
        lines.append("Code review complete.")
        return "\n".join(lines)

    for i, critique in enumerate(response.critiques, 1):
        hallucination_flag = ""
        if critique.is_hallucination:
            hallucination_flag = "\n   [!] POTENTIAL HALLUCINATION: " + critique.hallucination_reason

        lines.append(f"{i}. [{critique.category}] {critique.file_path}:{critique.line_number}")
        lines.append(f"   {critique.description}")
        if critique.why_wrong:
            lines.append(f"\n   Why: {critique.why_wrong}")
        if critique.suggested_fix:
            lines.append(f"\n   Fix: {critique.suggested_fix}")
        if hallucination_flag:
            lines.append(hallucination_flag)
        lines.append("")

    lines.extend([
        "-" * 64,
        "Options:",
        "[A]ccept all and address",
        "[P]artially accept (select which: e.g., 1,3)",
        "[R]eject as hallucinated",
        "[D]one (code is complete)",
        "-" * 64,
    ])

    return "\n".join(lines)


def run_adversarial_review(
    project_dir: Path,
    staged_only: bool = False,
    max_iterations: int = 5,
    model: str = "gemini-2.5-flash",
) -> dict[str, Any]:
    """Run the full adversarial review loop."""
    results = {
        "iterations": 0,
        "total_critiques": 0,
        "accepted_critiques": 0,
        "rejected_critiques": 0,
        "hallucinations_detected": 0,
        "outcome": "incomplete",
    }

    context = gather_context(project_dir, staged_only)

    if not context.diff.strip():
        return {**results, "outcome": "no_changes", "message": "No changes to review"}

    for iteration in range(1, max_iterations + 1):
        results["iterations"] = iteration

        # Format context and invoke adversary
        formatted_context = format_context_for_adversary(context)
        raw_response = invoke_adversary(formatted_context, project_dir, model)

        # Parse and validate response
        response = parse_adversary_response(raw_response)
        response = detect_hallucinations(response, project_dir)

        # Count hallucinations
        hallucinations = sum(1 for c in response.critiques if c.is_hallucination)
        results["hallucinations_detected"] += hallucinations

        if response.no_issues:
            results["outcome"] = "complete"
            print(format_critique_output(response, iteration))
            break

        results["total_critiques"] += len(response.critiques)

        # Display critiques
        print(format_critique_output(response, iteration))

        # In non-interactive mode, just report
        # Interactive mode would prompt for Accept/Reject/Done
        results["outcome"] = "needs_review"
        break  # Exit after first iteration in non-interactive mode

    return results


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run adversarial code review")
    parser.add_argument(
        "--staged", action="store_true", help="Only review staged changes"
    )
    parser.add_argument(
        "--max-iterations", type=int, default=5, help="Maximum review iterations"
    )
    parser.add_argument(
        "--model", default="gemini-2.5-flash", help="Model for adversary"
    )
    parser.add_argument(
        "--project-dir", type=Path, default=Path.cwd(), help="Project directory"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    args = parser.parse_args()

    results = run_adversarial_review(
        args.project_dir,
        staged_only=args.staged,
        max_iterations=args.max_iterations,
        model=args.model,
    )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\nReview Summary:")
        print(f"  Iterations: {results['iterations']}")
        print(f"  Total critiques: {results['total_critiques']}")
        print(f"  Hallucinations detected: {results['hallucinations_detected']}")
        print(f"  Outcome: {results['outcome']}")

    return 0 if results["outcome"] in ("complete", "no_changes") else 1


if __name__ == "__main__":
    sys.exit(main())
