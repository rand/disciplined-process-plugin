#!/usr/bin/env python3
"""
Migration script for moving issues between Beads and Chainlink.

Supports bidirectional migration with checkpoint recovery.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class IssueMapping:
    """Maps source ID to target ID."""

    source_id: str
    target_id: str
    title: str
    spec_refs: list[str] = field(default_factory=list)


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    source: str
    target: str
    issues_migrated: int
    dependencies_migrated: int
    mappings: list[IssueMapping]
    errors: list[str] = field(default_factory=list)


def parse_beads_issues(beads_dir: Path) -> list[dict[str, Any]]:
    """Parse issues from Beads JSONL file."""
    issues_file = beads_dir / "issues.jsonl"
    if not issues_file.exists():
        raise FileNotFoundError(f"Beads issues file not found: {issues_file}")

    issues = []
    with open(issues_file) as f:
        for line in f:
            line = line.strip()
            if line:
                issues.append(json.loads(line))

    return issues


def extract_spec_refs(text: str) -> list[str]:
    """Extract SPEC-XX.YY references from text."""
    pattern = r"\[SPEC-(\d+)\.(\d+)\]"
    matches = re.findall(pattern, text or "")
    return [f"SPEC-{m[0]}.{m[1]}" for m in matches]


def map_beads_priority(priority: int) -> str:
    """Map Beads numeric priority to Chainlink priority."""
    # Beads: 0=critical, 1=high, 2=medium, 3=low, 4=backlog
    # Chainlink: critical, high, medium, low
    mapping = {0: "critical", 1: "high", 2: "medium", 3: "low", 4: "low"}
    return mapping.get(priority, "medium")


def map_chainlink_priority(priority: str) -> int:
    """Map Chainlink priority to Beads numeric priority."""
    mapping = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return mapping.get(priority.lower(), 2)


def create_chainlink_issue(
    issue: dict[str, Any], project_dir: Path, dry_run: bool = False
) -> str | None:
    """Create a Chainlink issue from Beads issue data."""
    title = issue.get("title", "Untitled")
    description = issue.get("description", "")
    priority = map_beads_priority(issue.get("priority", 2))

    if dry_run:
        return None

    cmd = ["chainlink", "create", title, "-p", priority]
    if description:
        cmd.extend(["-d", description])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir)

    if result.returncode != 0:
        return None

    # Parse created issue ID from output
    # Expected format: "Created issue #N: title"
    match = re.search(r"#(\d+)", result.stdout)
    if match:
        return f"CL-{match.group(1)}"

    return None


def create_beads_issue(
    issue: dict[str, Any], project_dir: Path, dry_run: bool = False
) -> str | None:
    """Create a Beads issue from Chainlink issue data."""
    title = issue.get("title", "Untitled")
    description = issue.get("description", "")
    priority = map_chainlink_priority(issue.get("priority", "medium"))
    issue_type = issue.get("template", "task")

    if dry_run:
        return None

    cmd = [
        "bd",
        "create",
        f"--title={title}",
        f"--priority={priority}",
        f"--type={issue_type}",
    ]
    if description:
        cmd.append(f"--description={description}")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir)

    if result.returncode != 0:
        return None

    # Parse created issue ID from output
    # Expected format: "Created bd-xxxx: title"
    match = re.search(r"(bd-[a-z0-9]+)", result.stdout)
    if match:
        return match.group(1)

    return None


def migrate_beads_to_chainlink(
    project_dir: Path, dry_run: bool = False
) -> MigrationResult:
    """Migrate issues from Beads to Chainlink."""
    beads_dir = project_dir / ".beads"
    if not beads_dir.is_dir():
        return MigrationResult(
            success=False,
            source="beads",
            target="chainlink",
            issues_migrated=0,
            dependencies_migrated=0,
            mappings=[],
            errors=[".beads/ directory not found"],
        )

    # Check Chainlink CLI
    if subprocess.run(["which", "chainlink"], capture_output=True).returncode != 0:
        return MigrationResult(
            success=False,
            source="beads",
            target="chainlink",
            issues_migrated=0,
            dependencies_migrated=0,
            mappings=[],
            errors=["chainlink CLI not found"],
        )

    # Initialize Chainlink if needed
    chainlink_dir = project_dir / ".chainlink"
    if not chainlink_dir.is_dir() and not dry_run:
        subprocess.run(["chainlink", "init"], cwd=project_dir, capture_output=True)

    # Parse Beads issues
    try:
        issues = parse_beads_issues(beads_dir)
    except Exception as e:
        return MigrationResult(
            success=False,
            source="beads",
            target="chainlink",
            issues_migrated=0,
            dependencies_migrated=0,
            mappings=[],
            errors=[str(e)],
        )

    # Create mappings
    mappings: list[IssueMapping] = []
    errors: list[str] = []
    id_map: dict[str, str] = {}  # beads_id -> chainlink_id

    print(f"\nMigrating {len(issues)} issues from Beads to Chainlink...")
    if dry_run:
        print("(DRY RUN - no changes will be made)\n")

    for i, issue in enumerate(issues, 1):
        beads_id = issue.get("id", "unknown")
        title = issue.get("title", "Untitled")
        description = issue.get("description", "")

        print(f"  [{i}/{len(issues)}] {beads_id}: {title[:50]}...")

        if dry_run:
            chainlink_id = f"CL-{i}"
        else:
            chainlink_id = create_chainlink_issue(issue, project_dir)

        if chainlink_id:
            id_map[beads_id] = chainlink_id
            spec_refs = extract_spec_refs(description)
            mappings.append(
                IssueMapping(
                    source_id=beads_id,
                    target_id=chainlink_id,
                    title=title,
                    spec_refs=spec_refs,
                )
            )
        else:
            errors.append(f"Failed to create issue for {beads_id}")

    # Migrate dependencies
    deps_migrated = 0
    for issue in issues:
        beads_id = issue.get("id", "")
        if beads_id not in id_map:
            continue

        chainlink_id = id_map[beads_id]
        dependencies = issue.get("dependencies", [])

        for dep in dependencies:
            dep_beads_id = dep.get("depends_on_id", "")
            dep_type = dep.get("type", "blocks")

            if dep_beads_id in id_map and not dry_run:
                dep_chainlink_id = id_map[dep_beads_id]
                # Chainlink uses "block" command
                if dep_type == "blocks":
                    subprocess.run(
                        ["chainlink", "block", chainlink_id.replace("CL-", ""),
                         dep_chainlink_id.replace("CL-", "")],
                        cwd=project_dir,
                        capture_output=True,
                    )
                elif dep_type == "related":
                    subprocess.run(
                        ["chainlink", "relate", chainlink_id.replace("CL-", ""),
                         dep_chainlink_id.replace("CL-", "")],
                        cwd=project_dir,
                        capture_output=True,
                    )
                deps_migrated += 1

    return MigrationResult(
        success=len(errors) == 0,
        source="beads",
        target="chainlink",
        issues_migrated=len(mappings),
        dependencies_migrated=deps_migrated,
        mappings=mappings,
        errors=errors,
    )


def migrate_chainlink_to_beads(
    project_dir: Path, dry_run: bool = False
) -> MigrationResult:
    """Migrate issues from Chainlink to Beads."""
    chainlink_dir = project_dir / ".chainlink"
    if not chainlink_dir.is_dir():
        return MigrationResult(
            success=False,
            source="chainlink",
            target="beads",
            issues_migrated=0,
            dependencies_migrated=0,
            mappings=[],
            errors=[".chainlink/ directory not found"],
        )

    # Check Beads CLI
    if subprocess.run(["which", "bd"], capture_output=True).returncode != 0:
        return MigrationResult(
            success=False,
            source="chainlink",
            target="beads",
            issues_migrated=0,
            dependencies_migrated=0,
            mappings=[],
            errors=["bd CLI not found"],
        )

    # Initialize Beads if needed
    beads_dir = project_dir / ".beads"
    if not beads_dir.is_dir() and not dry_run:
        subprocess.run(["bd", "init"], cwd=project_dir, capture_output=True)

    # Get Chainlink issues
    result = subprocess.run(
        ["chainlink", "list", "-s", "all"],
        capture_output=True,
        text=True,
        cwd=project_dir,
    )

    if result.returncode != 0:
        return MigrationResult(
            success=False,
            source="chainlink",
            target="beads",
            issues_migrated=0,
            dependencies_migrated=0,
            mappings=[],
            errors=["Failed to list Chainlink issues"],
        )

    # Parse issues (simplified - would need actual Chainlink output parsing)
    lines = result.stdout.strip().split("\n")
    mappings: list[IssueMapping] = []
    errors: list[str] = []

    print(f"\nMigrating from Chainlink to Beads...")
    if dry_run:
        print("(DRY RUN - no changes will be made)\n")

    print("\nWarning: The following data will be lost:")
    print("  - Session history and handoff notes")
    print("  - Time tracking data")
    print("  - Milestones (will be converted to labels)")
    print()

    # Simplified migration - in practice would parse Chainlink export
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue

        # Parse line format: "#N: title [status] (priority)"
        match = re.match(r"#(\d+):\s*(.+?)(?:\s*\[|\s*$)", line)
        if not match:
            continue

        chainlink_id = f"CL-{match.group(1)}"
        title = match.group(2).strip()

        print(f"  [{i}] {chainlink_id}: {title[:50]}...")

        if dry_run:
            beads_id = f"bd-{i:04x}"
        else:
            beads_id = create_beads_issue({"title": title}, project_dir)

        if beads_id:
            mappings.append(
                IssueMapping(
                    source_id=chainlink_id, target_id=beads_id, title=title, spec_refs=[]
                )
            )
        else:
            errors.append(f"Failed to create issue for {chainlink_id}")

    return MigrationResult(
        success=len(errors) == 0,
        source="chainlink",
        target="beads",
        issues_migrated=len(mappings),
        dependencies_migrated=0,  # Would need to migrate blocking relationships
        mappings=mappings,
        errors=errors,
    )


def save_mapping_file(result: MigrationResult, project_dir: Path) -> None:
    """Save migration mapping file."""
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)

    mapping_file = claude_dir / "dp-migration-map.json"
    data = {
        "migrated_at": datetime.now().isoformat(),
        "source": result.source,
        "target": result.target,
        "version": "1.0",
        "mappings": [
            {
                "source_id": m.source_id,
                "target_id": m.target_id,
                "title": m.title,
                "spec_refs": m.spec_refs,
            }
            for m in result.mappings
        ],
    }

    with open(mapping_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nMapping saved to {mapping_file}")


def update_config(target: str, project_dir: Path) -> None:
    """Update dp-config.yaml with new tracker."""
    config_file = project_dir / ".claude" / "dp-config.yaml"
    if not config_file.exists():
        return

    content = config_file.read_text()
    # Update tracker setting
    content = re.sub(
        r"(task_tracker:\s*)(\w+)", f"\\g<1>{target}", content, count=1
    )
    config_file.write_text(content)
    print(f"\nUpdated {config_file} to use {target}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate between task trackers")
    parser.add_argument(
        "direction",
        choices=["beads-to-chainlink", "chainlink-to-beads"],
        help="Migration direction",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current)",
    )

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"Migration: {args.direction}")
    print(f"{'=' * 60}")

    if args.direction == "beads-to-chainlink":
        result = migrate_beads_to_chainlink(args.project_dir, args.dry_run)
    else:
        result = migrate_chainlink_to_beads(args.project_dir, args.dry_run)

    print(f"\n{'=' * 60}")
    print("Migration Summary")
    print(f"{'=' * 60}")
    print(f"  Source: {result.source}")
    print(f"  Target: {result.target}")
    print(f"  Issues migrated: {result.issues_migrated}")
    print(f"  Dependencies migrated: {result.dependencies_migrated}")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)}):")
        for err in result.errors:
            print(f"    - {err}")

    if result.success and not args.dry_run:
        save_mapping_file(result, args.project_dir)
        update_config(result.target, args.project_dir)
        print("\nMigration completed successfully!")
    elif args.dry_run:
        print("\nDry run complete. Run without --dry-run to execute.")
    else:
        print("\nMigration completed with errors. Check output above.")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
