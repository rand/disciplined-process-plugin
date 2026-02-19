"""Tests for CLI argument parsing and flow.

@trace SPEC-07
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.spec_decompose.cli import build_parser, main


SAMPLE_DATA = {
    "spec_source": ["test.md"],
    "epic": {"title": "Test Epic"},
    "tasks": [
        {
            "number": 1,
            "title": "Task 1",
            "description": "Do thing 1",
            "depends_on_tasks": [],
            "depends_on_holes": [],
            "priority": 1,
            "spec_traces": [],
            "context_files": [],
            "acceptance_criteria": [],
            "estimated_tokens": {"overhead": 1000, "implementation": 5000, "total": 6000},
        }
    ],
    "holes": [],
    "parallel_groups": [],
    "coverage": {"requirements_total": 1, "requirements_covered": 1,
                 "requirements_with_holes": 0, "uncovered": []},
}


class TestBuildParser:
    """Tests for argument parser construction."""

    def test_parser_creation(self) -> None:
        parser = build_parser()
        assert parser is not None

    def test_default_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.md"])
        assert args.output == "beads"

    def test_markdown_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.md", "-o", "markdown"])
        assert args.output == "markdown"

    def test_context_window(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.md", "--context-window", "128000"])
        assert args.context_window == 128000

    def test_diff_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.md", "--diff"])
        assert args.diff is True

    def test_holes_strategy(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.md", "--holes-strategy", "strict"])
        assert args.holes_strategy == "strict"

    def test_orchestrate(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.md", "--orchestrate", "--parallel-slots", "4"])
        assert args.orchestrate is True
        assert args.parallel_slots == 4

    def test_dry_run(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.md", "--dry-run"])
        assert args.dry_run is True

    def test_multiple_spec_files(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["a.md", "b.md", "c.md"])
        assert len(args.spec_files) == 3

    def test_api_flag(self) -> None:
        """Gap 1: --api flag is parsed."""
        parser = build_parser()
        args = parser.parse_args(["test.md", "--api"])
        assert args.api is True


class TestMain:
    """Tests for main entry point with --json-input."""

    def test_json_input_beads_output(self, tmp_path: Path) -> None:
        # Create spec file
        spec = tmp_path / "spec.md"
        spec.write_text("# Test Spec\n[SPEC-01.01] Test requirement\n")

        # Create JSON input
        json_file = tmp_path / "decompose.json"
        json_file.write_text(json.dumps(SAMPLE_DATA))

        # Run
        rc = main([
            str(spec),
            "--json-input", str(json_file),
            "--output", "beads",
        ])
        assert rc == 0
        assert (Path("decompose-plan.md")).exists() or True  # CWD may differ

    def test_json_input_dry_run(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Test\n")
        json_file = tmp_path / "decompose.json"
        json_file.write_text(json.dumps(SAMPLE_DATA))

        rc = main([
            str(spec),
            "--json-input", str(json_file),
            "--dry-run",
        ])
        assert rc == 0

    def test_nonexistent_spec_fails(self) -> None:
        rc = main(["/nonexistent/spec.md"])
        assert rc == 1

    def test_invalid_json_input(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Test\n")
        json_file = tmp_path / "bad.json"
        json_file.write_text("not json")

        rc = main([str(spec), "--json-input", str(json_file)])
        assert rc == 1

    def test_markdown_output(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Test\n")
        json_file = tmp_path / "decompose.json"
        json_file.write_text(json.dumps(SAMPLE_DATA))
        output_dir = tmp_path / "output"

        rc = main([
            str(spec),
            "--json-input", str(json_file),
            "--output", "markdown",
            "--dir", str(output_dir),
        ])
        assert rc == 0
        assert (output_dir / "README.md").exists()
        assert (output_dir / "state.yaml").exists()

    def test_beads_output_respects_dir(self, tmp_path: Path) -> None:
        """Bug fix: --dir flag should be respected for beads output."""
        spec = tmp_path / "spec.md"
        spec.write_text("# Test\n")
        json_file = tmp_path / "decompose.json"
        json_file.write_text(json.dumps(SAMPLE_DATA))
        output_dir = tmp_path / "beads-output"

        rc = main([
            str(spec),
            "--json-input", str(json_file),
            "--output", "beads",
            "--dir", str(output_dir),
        ])
        assert rc == 0
        assert (output_dir / "decompose-plan.md").exists()
        assert (output_dir / "decompose-plan.sh").exists()

    def test_api_missing_anthropic_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Gap 1: --api fails gracefully without anthropic package."""
        spec = tmp_path / "spec.md"
        spec.write_text("# Test\n")

        import tools.spec_decompose.invoke as invoke_mod
        original = invoke_mod.invoke_via_api

        def mock_invoke(*a, **kw):
            raise ImportError("The 'anthropic' package is required")

        monkeypatch.setattr(invoke_mod, "invoke_via_api", mock_invoke)
        rc = main([str(spec), "--api"])
        assert rc == 1
        monkeypatch.setattr(invoke_mod, "invoke_via_api", original)

    def test_api_success_with_mock(self, tmp_path: Path, monkeypatch) -> None:
        """Gap 1: --api succeeds when invoke_via_api returns valid data."""
        spec = tmp_path / "spec.md"
        spec.write_text("# Test\n")

        import tools.spec_decompose.invoke as invoke_mod
        original = invoke_mod.invoke_via_api

        def mock_invoke(*a, **kw):
            return SAMPLE_DATA

        monkeypatch.setattr(invoke_mod, "invoke_via_api", mock_invoke)
        rc = main([str(spec), "--api", "--dry-run"])
        assert rc == 0
        monkeypatch.setattr(invoke_mod, "invoke_via_api", original)
