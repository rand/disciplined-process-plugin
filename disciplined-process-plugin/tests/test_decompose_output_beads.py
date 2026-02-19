"""Tests for Beads output generation.

@trace SPEC-07
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.spec_decompose.output_beads import (
    generate_plan_markdown,
    generate_plan_script,
    write_beads_output,
)


SAMPLE_DATA = {
    "spec_source": ["docs/spec/auth.md"],
    "epic": {"title": "Authentication System", "description": "Full auth module"},
    "issues": [{"number": 1, "title": "OAuth Integration", "tasks": [1, 2]}],
    "tasks": [
        {
            "number": 1,
            "title": "Configure OAuth provider",
            "description": "Set up OAuth provider configuration",
            "priority": 1,
            "depends_on_tasks": [],
            "depends_on_holes": [],
            "spec_traces": ["SPEC-03.01"],
            "context_files": [
                {"path": "src/config/oauth.py", "reason": "Config module", "estimated_tokens": 800}
            ],
            "acceptance_criteria": ["OAuth config loads from env vars"],
            "produces": ["src/config/oauth.py"],
            "estimated_tokens": {"overhead": 3200, "implementation": 10000, "tests": 4000, "total": 17200},
            "orchestration": {"parallel_group": "foundation", "blocks": [2]},
        },
        {
            "number": 2,
            "title": "Token exchange endpoint",
            "description": "Implement OAuth token exchange",
            "priority": 1,
            "depends_on_tasks": [1],
            "depends_on_holes": ["H001"],
            "spec_traces": ["SPEC-03.02"],
            "context_files": [],
            "acceptance_criteria": ["Token exchange returns access token"],
            "produces": ["src/auth/token.py"],
            "estimated_tokens": {"overhead": 2000, "implementation": 25000, "tests": 10000, "total": 37000},
            "orchestration": {"parallel_group": "core", "blocks": []},
        },
    ],
    "holes": [
        {
            "number": "H001",
            "title": "Session revocation behavior",
            "hole_type": "clarification",
            "priority": 1,
            "known": {"input": "User with revoked token"},
            "unknown": ["Eager or lazy invalidation?"],
            "blocks_tasks": [2],
            "resolution_method": "human_input",
        }
    ],
    "parallel_groups": [
        {"name": "foundation", "tasks": [1], "rationale": "No dependencies"}
    ],
    "coverage": {
        "requirements_total": 2,
        "requirements_covered": 2,
        "requirements_with_holes": 1,
        "uncovered": [],
    },
}


class TestGeneratePlanMarkdown:
    """Tests for plan markdown generation."""

    def test_contains_title(self) -> None:
        md = generate_plan_markdown(SAMPLE_DATA)
        assert "Authentication System" in md

    def test_contains_task_table(self) -> None:
        md = generate_plan_markdown(SAMPLE_DATA)
        assert "Configure OAuth provider" in md
        assert "Token exchange endpoint" in md

    def test_contains_hole_table(self) -> None:
        md = generate_plan_markdown(SAMPLE_DATA)
        assert "Session revocation behavior" in md
        assert "clarification" in md

    def test_contains_coverage(self) -> None:
        md = generate_plan_markdown(SAMPLE_DATA)
        assert "2/2" in md

    def test_contains_parallel_groups(self) -> None:
        md = generate_plan_markdown(SAMPLE_DATA)
        assert "foundation" in md

    def test_shows_dependencies(self) -> None:
        md = generate_plan_markdown(SAMPLE_DATA)
        assert "T1" in md
        assert "H001" in md


class TestGeneratePlanScript:
    """Tests for plan script generation."""

    def test_starts_with_shebang(self) -> None:
        script = generate_plan_script(SAMPLE_DATA)
        assert script.startswith("#!/usr/bin/env bash")

    def test_creates_epic(self) -> None:
        script = generate_plan_script(SAMPLE_DATA)
        assert "EPIC_ID=" in script
        assert "Authentication System" in script

    def test_creates_holes(self) -> None:
        script = generate_plan_script(SAMPLE_DATA)
        assert "HOLE:" in script
        assert "H001" in script

    def test_creates_tasks(self) -> None:
        script = generate_plan_script(SAMPLE_DATA)
        assert "T1_ID=" in script
        assert "T2_ID=" in script

    def test_wires_dependencies(self) -> None:
        script = generate_plan_script(SAMPLE_DATA)
        assert "bd dep add" in script

    def test_custom_epic_title(self) -> None:
        script = generate_plan_script(SAMPLE_DATA, epic_title="Custom Title")
        assert "Custom Title" in script

    def test_uses_set_euo_pipefail(self) -> None:
        script = generate_plan_script(SAMPLE_DATA)
        assert "set -euo pipefail" in script


class TestWriteBeadsOutput:
    """Tests for writing output files."""

    def test_creates_both_files(self, tmp_path: Path) -> None:
        plan_md, plan_sh = write_beads_output(SAMPLE_DATA, output_dir=tmp_path)
        assert plan_md.exists()
        assert plan_sh.exists()

    def test_plan_md_is_readable(self, tmp_path: Path) -> None:
        plan_md, _ = write_beads_output(SAMPLE_DATA, output_dir=tmp_path)
        content = plan_md.read_text()
        assert "Authentication System" in content

    def test_plan_sh_is_executable_bash(self, tmp_path: Path) -> None:
        _, plan_sh = write_beads_output(SAMPLE_DATA, output_dir=tmp_path)
        content = plan_sh.read_text()
        assert content.startswith("#!/usr/bin/env bash")
