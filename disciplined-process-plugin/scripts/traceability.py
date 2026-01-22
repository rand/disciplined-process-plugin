#!/usr/bin/env python3
"""
Traceability utilities for spec-issue-code linking.

Provides functions to:
- Parse spec IDs from documentation
- Extract @trace markers from code/tests
- Parse issue links from HTML comments
- Generate coverage reports
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SpecReference:
    """A specification reference with optional issue link."""

    spec_id: str  # e.g., "SPEC-01.03"
    title: str
    file_path: Path
    line_number: int
    issue_link: str | None = None  # e.g., "chainlink:15" or "beads:bd-a1b2"


@dataclass
class TraceMarker:
    """A @trace marker in code or tests."""

    spec_id: str
    file_path: Path
    line_number: int
    context: str  # surrounding code/comment


@dataclass
class TraceCoverage:
    """Coverage information for a single spec."""

    spec: SpecReference
    issue_status: str | None = None  # open, in_progress, closed
    trace_count: int = 0
    test_count: int = 0
    code_locations: list[str] = field(default_factory=list)
    test_locations: list[str] = field(default_factory=list)


# Regex patterns
SPEC_ID_PATTERN = re.compile(r"\[SPEC-(\d+)(?:\.(\d+))?\]")
ISSUE_LINK_PATTERN = re.compile(r"<!--\s*(chainlink|beads):(\S+)\s*-->")
TRACE_PATTERN = re.compile(r"@trace\s+SPEC-(\d+)\.(\d+)(?:\.(\w+))?")


def parse_specs_from_file(file_path: Path) -> list[SpecReference]:
    """Parse all spec references from a markdown file."""
    specs = []
    try:
        content = file_path.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find spec IDs
            for match in SPEC_ID_PATTERN.finditer(line):
                section = match.group(1)
                paragraph = match.group(2)
                spec_id = f"SPEC-{section}" + (f".{paragraph}" if paragraph else "")

                # Extract title (text after the spec ID until end or next marker)
                title_start = match.end()
                title_end = line.find("<!--", title_start)
                if title_end == -1:
                    title_end = len(line)
                title = line[title_start:title_end].strip().rstrip(".")

                # Check for issue link
                issue_link = None
                link_match = ISSUE_LINK_PATTERN.search(line)
                if link_match:
                    provider = link_match.group(1)
                    issue_id = link_match.group(2)
                    issue_link = f"{provider}:{issue_id}"

                specs.append(
                    SpecReference(
                        spec_id=spec_id,
                        title=title,
                        file_path=file_path,
                        line_number=line_num,
                        issue_link=issue_link,
                    )
                )
    except (OSError, UnicodeDecodeError):
        pass

    return specs


def parse_all_specs(spec_dir: Path) -> list[SpecReference]:
    """Parse all specs from the spec directory."""
    all_specs = []
    if not spec_dir.is_dir():
        return all_specs

    for md_file in spec_dir.glob("**/*.md"):
        all_specs.extend(parse_specs_from_file(md_file))

    return sorted(all_specs, key=lambda s: s.spec_id)


def find_trace_markers(
    search_dirs: list[Path], patterns: list[str] | None = None
) -> list[TraceMarker]:
    """Find all @trace markers in code and test files."""
    markers = []

    if patterns is None:
        patterns = ["*.py", "*.ts", "*.tsx", "*.js", "*.go", "*.rs"]

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue

        for pattern in patterns:
            for file_path in search_dir.glob(f"**/{pattern}"):
                try:
                    content = file_path.read_text()
                    lines = content.split("\n")

                    for line_num, line in enumerate(lines, 1):
                        for match in TRACE_PATTERN.finditer(line):
                            section = match.group(1)
                            paragraph = match.group(2)
                            sub = match.group(3)

                            spec_id = f"SPEC-{section}.{paragraph}"
                            if sub:
                                spec_id += f".{sub}"

                            markers.append(
                                TraceMarker(
                                    spec_id=spec_id,
                                    file_path=file_path,
                                    line_number=line_num,
                                    context=line.strip(),
                                )
                            )
                except (OSError, UnicodeDecodeError):
                    continue

    return markers


def get_issue_status(issue_link: str, project_dir: Path) -> str | None:
    """Get the status of a linked issue."""
    if not issue_link:
        return None

    parts = issue_link.split(":", 1)
    if len(parts) != 2:
        return None

    provider, issue_id = parts

    try:
        if provider == "chainlink":
            result = subprocess.run(
                ["chainlink", "show", issue_id],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=project_dir,
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                if "closed" in output:
                    return "closed"
                elif "in progress" in output or "in_progress" in output:
                    return "in_progress"
                else:
                    return "open"
        elif provider == "beads":
            result = subprocess.run(
                ["bd", "show", issue_id],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=project_dir,
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                if "closed" in output:
                    return "closed"
                elif "in_progress" in output:
                    return "in_progress"
                else:
                    return "open"
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def generate_coverage_report(project_dir: Path) -> list[TraceCoverage]:
    """Generate full traceability coverage report."""
    spec_dir = project_dir / "docs" / "spec"
    src_dir = project_dir / "src"
    tests_dir = project_dir / "tests"

    # Parse all specs
    specs = parse_all_specs(spec_dir)

    # Find all trace markers
    code_markers = find_trace_markers([src_dir])
    test_markers = find_trace_markers([tests_dir])

    # Build coverage info
    coverage = []
    for spec in specs:
        # Find matching traces (match SPEC-XX.YY, ignoring sub-items like .a)
        base_spec_id = spec.spec_id
        code_traces = [
            m for m in code_markers if m.spec_id.startswith(base_spec_id)
        ]
        test_traces = [
            m for m in test_markers if m.spec_id.startswith(base_spec_id)
        ]

        # Get issue status
        issue_status = get_issue_status(spec.issue_link, project_dir)

        coverage.append(
            TraceCoverage(
                spec=spec,
                issue_status=issue_status,
                trace_count=len(code_traces) + len(test_traces),
                test_count=len(test_traces),
                code_locations=[
                    f"{m.file_path.relative_to(project_dir)}:{m.line_number}"
                    for m in code_traces
                ],
                test_locations=[
                    f"{m.file_path.relative_to(project_dir)}:{m.line_number}"
                    for m in test_traces
                ],
            )
        )

    return coverage


def link_spec_to_issue(
    spec_id: str, issue_id: str, provider: str, project_dir: Path
) -> bool:
    """Add issue link to a spec in documentation."""
    spec_dir = project_dir / "docs" / "spec"
    specs = parse_all_specs(spec_dir)

    # Find the spec
    spec = next((s for s in specs if s.spec_id == spec_id), None)
    if not spec:
        return False

    # Read file
    content = spec.file_path.read_text()
    lines = content.split("\n")

    # Find and update the line
    line_idx = spec.line_number - 1
    line = lines[line_idx]

    # Remove existing link if present
    line = ISSUE_LINK_PATTERN.sub("", line).rstrip()

    # Add new link
    line = f"{line} <!-- {provider}:{issue_id} -->"
    lines[line_idx] = line

    # Write back
    spec.file_path.write_text("\n".join(lines))
    return True


def unlink_spec(spec_id: str, project_dir: Path) -> bool:
    """Remove issue link from a spec."""
    spec_dir = project_dir / "docs" / "spec"
    specs = parse_all_specs(spec_dir)

    # Find the spec
    spec = next((s for s in specs if s.spec_id == spec_id), None)
    if not spec or not spec.issue_link:
        return False

    # Read file
    content = spec.file_path.read_text()
    lines = content.split("\n")

    # Find and update the line
    line_idx = spec.line_number - 1
    line = lines[line_idx]

    # Remove link
    line = ISSUE_LINK_PATTERN.sub("", line).rstrip()
    lines[line_idx] = line

    # Write back
    spec.file_path.write_text("\n".join(lines))
    return True


def format_coverage_report(coverage: list[TraceCoverage], project_dir: Path) -> str:
    """Format coverage report as text."""
    lines = [
        "Spec Coverage Report",
        "=" * 72,
        "",
    ]

    # Group by section
    sections: dict[str, list[TraceCoverage]] = {}
    for cov in coverage:
        # Extract section from SPEC-XX.YY
        match = re.match(r"SPEC-(\d+)", cov.spec.spec_id)
        if match:
            section = match.group(1)
            if section not in sections:
                sections[section] = []
            sections[section].append(cov)

    # Output each section
    total_specs = 0
    covered_specs = 0

    for section_num in sorted(sections.keys()):
        section_covs = sections[section_num]
        lines.append(f"Section {section_num}")
        lines.append("-" * 72)

        for cov in section_covs:
            total_specs += 1

            # Determine status indicator
            if cov.issue_status == "closed" and cov.test_count > 0:
                indicator = "[x]"
                covered_specs += 1
            elif cov.spec.issue_link:
                indicator = "[!]"
            else:
                indicator = "[ ]"

            # Issue info
            if cov.spec.issue_link:
                issue_info = f"{cov.spec.issue_link} ({cov.issue_status or 'unknown'})"
            else:
                issue_info = "No linked issue"

            # Test info
            if cov.test_count > 0:
                test_info = f"tests: {cov.test_count}"
            else:
                test_info = "tests: -"

            # Code info
            if cov.code_locations:
                code_info = f"code: {cov.code_locations[0]}"
            else:
                code_info = "code: -"

            lines.append(
                f"{cov.spec.spec_id:12} {indicator} {issue_info:30} {test_info:15} {code_info}"
            )

        lines.append("")

    # Summary
    in_progress = sum(1 for c in coverage if c.spec.issue_link and c.issue_status != "closed")
    not_started = sum(1 for c in coverage if not c.spec.issue_link)

    lines.append(
        f"Summary: {covered_specs}/{total_specs} specs fully covered, "
        f"{in_progress} in progress, {not_started} not started"
    )
    lines.append("=" * 72)

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    project_dir = Path.cwd()
    coverage = generate_coverage_report(project_dir)
    print(format_coverage_report(coverage, project_dir))
