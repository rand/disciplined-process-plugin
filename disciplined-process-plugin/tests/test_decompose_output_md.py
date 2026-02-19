"""Tests for Markdown output generation.

@trace SPEC-07
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.spec_decompose.output_markdown import (
    generate_hole_markdown,
    generate_state_yaml,
    generate_task_markdown,
    write_markdown_output,
)


SAMPLE_TASK = {
    "number": 1,
    "title": "Configure OAuth provider",
    "description": "Set up OAuth provider configuration from environment variables.",
    "priority": 1,
    "depends_on_tasks": [],
    "depends_on_holes": ["H001"],
    "spec_traces": ["SPEC-03.01"],
    "context_files": [
        {"path": "src/config/oauth.py", "reason": "Config module", "estimated_tokens": 800}
    ],
    "acceptance_criteria": [
        "OAuth config loads from env vars",
        "Unit test covers missing config",
    ],
    "orchestration": {
        "parallel_group": "foundation",
        "estimated_tokens": 17200,
        "blocks": [2, 3],
    },
}

SAMPLE_HOLE = {
    "number": "H001",
    "title": "Session revocation behavior",
    "hole_type": "clarification",
    "priority": 1,
    "known": {
        "input": "User with revoked token",
        "output": "[? behavior]",
        "constraints": ["No orphaned sessions"],
    },
    "unknown": [
        "Eager or lazy invalidation?",
        "Error page or redirect?",
    ],
    "blocks_tasks": [5, 6],
    "resolution_method": "human_input",
}

SAMPLE_DATA = {
    "spec_source": ["docs/spec/auth.md"],
    "epic": {"title": "Auth System"},
    "tasks": [SAMPLE_TASK],
    "holes": [SAMPLE_HOLE],
    "parallel_groups": [{"name": "foundation", "tasks": [1]}],
    "coverage": {"requirements_total": 1, "requirements_covered": 1,
                 "requirements_with_holes": 0, "uncovered": []},
}


class TestGenerateTaskMarkdown:
    """Tests for individual task file generation."""

    def test_contains_title(self) -> None:
        md = generate_task_markdown(SAMPLE_TASK)
        assert "T001: Configure OAuth provider" in md

    def test_contains_status(self) -> None:
        md = generate_task_markdown(SAMPLE_TASK)
        assert "**Status:** open" in md

    def test_contains_dependencies(self) -> None:
        md = generate_task_markdown(SAMPLE_TASK)
        assert "H001" in md

    def test_contains_spec_traces(self) -> None:
        md = generate_task_markdown(SAMPLE_TASK)
        assert "SPEC-03.01" in md

    def test_contains_acceptance_criteria(self) -> None:
        md = generate_task_markdown(SAMPLE_TASK)
        assert "- [ ] OAuth config loads from env vars" in md

    def test_contains_context_files(self) -> None:
        md = generate_task_markdown(SAMPLE_TASK)
        assert "src/config/oauth.py" in md

    def test_contains_orchestration_metadata(self) -> None:
        md = generate_task_markdown(SAMPLE_TASK)
        assert "ORCHESTRATION METADATA" in md
        assert "parallel_group: foundation" in md


class TestGenerateHoleMarkdown:
    """Tests for individual hole file generation."""

    def test_contains_title(self) -> None:
        md = generate_hole_markdown(SAMPLE_HOLE)
        assert "H001: Session revocation behavior" in md

    def test_contains_type(self) -> None:
        md = generate_hole_markdown(SAMPLE_HOLE)
        assert "**Type:** clarification" in md

    def test_contains_known(self) -> None:
        md = generate_hole_markdown(SAMPLE_HOLE)
        assert "User with revoked token" in md

    def test_contains_unknown(self) -> None:
        md = generate_hole_markdown(SAMPLE_HOLE)
        assert "Eager or lazy invalidation?" in md

    def test_contains_blocks(self) -> None:
        md = generate_hole_markdown(SAMPLE_HOLE)
        assert "T005" in md
        assert "T006" in md


class TestGenerateStateYaml:
    """Tests for state.yaml generation."""

    def test_valid_yaml(self) -> None:
        text = generate_state_yaml(SAMPLE_DATA)
        state = yaml.safe_load(text)
        assert state["version"] == 1

    def test_contains_tasks(self) -> None:
        text = generate_state_yaml(SAMPLE_DATA)
        state = yaml.safe_load(text)
        assert len(state["tasks"]) == 1
        assert state["tasks"][0]["title"] == "Configure OAuth provider"

    def test_contains_holes(self) -> None:
        text = generate_state_yaml(SAMPLE_DATA)
        state = yaml.safe_load(text)
        assert len(state["holes"]) == 1

    def test_contains_dependencies(self) -> None:
        text = generate_state_yaml(SAMPLE_DATA)
        state = yaml.safe_load(text)
        # SAMPLE_TASK has depends_on_holes: ["H001"]
        assert any(d["to"] == "H001" for d in state["dependencies"])

    def test_task_status_is_not_started(self) -> None:
        """Gap 12: status should be 'not_started' per schemas.md."""
        text = generate_state_yaml(SAMPLE_DATA)
        state = yaml.safe_load(text)
        assert state["tasks"][0]["status"] == "not_started"
        assert state["holes"][0]["status"] == "not_started"

    def test_enrichment_fields(self) -> None:
        """Gap 13: state.yaml should contain description, produces, acceptance_criteria."""
        task_with_produces = {
            **SAMPLE_TASK,
            "produces": ["src/auth.py", "tests/test_auth.py"],
        }
        data = {**SAMPLE_DATA, "tasks": [task_with_produces]}
        text = generate_state_yaml(data)
        state = yaml.safe_load(text)
        task = state["tasks"][0]
        assert "description" in task
        assert task["produces"] == ["src/auth.py", "tests/test_auth.py"]
        assert "acceptance_criteria" in task
        assert len(task["acceptance_criteria"]) == 2

    def test_spec_hash_from_files(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Test spec\n")
        text = generate_state_yaml(SAMPLE_DATA, spec_files=[str(spec)])
        state = yaml.safe_load(text)
        assert state["spec_hash"].startswith("sha256:")


class TestWriteMarkdownOutput:
    """Tests for full markdown output directory."""

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        out = write_markdown_output(SAMPLE_DATA, output_dir=tmp_path)
        assert (out / "README.md").exists()
        assert (out / "tasks").is_dir()
        assert (out / "holes").is_dir()
        assert (out / "state.yaml").exists()

    def test_creates_task_files(self, tmp_path: Path) -> None:
        write_markdown_output(SAMPLE_DATA, output_dir=tmp_path)
        task_files = list((tmp_path / "tasks").glob("*.md"))
        assert len(task_files) == 1
        content = task_files[0].read_text()
        assert "Configure OAuth provider" in content

    def test_creates_hole_files(self, tmp_path: Path) -> None:
        write_markdown_output(SAMPLE_DATA, output_dir=tmp_path)
        hole_files = list((tmp_path / "holes").glob("*.md"))
        assert len(hole_files) == 1
        content = hole_files[0].read_text()
        assert "Session revocation behavior" in content

    def test_state_yaml_is_valid(self, tmp_path: Path) -> None:
        write_markdown_output(SAMPLE_DATA, output_dir=tmp_path)
        state = yaml.safe_load((tmp_path / "state.yaml").read_text())
        assert state["version"] == 1
        assert len(state["tasks"]) == 1
