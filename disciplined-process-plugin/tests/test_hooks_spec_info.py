"""
Tests for spec-info.py hook — phase-aware spec enforcement.
"""
from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import importlib
spec_info = importlib.import_module("spec-info")


class TestIsSkipFile:
    def test_skips_test_files(self):
        assert spec_info.is_skip_file("/src/tests/test_foo.py")
        assert spec_info.is_skip_file("/src/foo.test.ts")
        assert spec_info.is_skip_file("/src/foo_test.go")

    def test_skips_docs_and_specs(self):
        assert spec_info.is_skip_file("/project/docs/readme.md")
        assert spec_info.is_skip_file("/project/docs/spec/01.md")

    def test_skips_config_files(self):
        assert spec_info.is_skip_file("/project/config.json")
        assert spec_info.is_skip_file("/project/settings.yaml")
        assert spec_info.is_skip_file("/project/pyproject.toml")

    def test_skips_non_impl_extensions(self):
        assert spec_info.is_skip_file("/project/style.css")
        assert spec_info.is_skip_file("/project/index.html")

    def test_allows_impl_files(self):
        assert not spec_info.is_skip_file("/src/main.py")
        assert not spec_info.is_skip_file("/src/app.ts")
        assert not spec_info.is_skip_file("/src/lib.rs")
        assert not spec_info.is_skip_file("/src/handler.go")


class TestProjectHasSpecs:
    def test_no_spec_dir(self, tmp_path: Path):
        f = tmp_path / "src" / "main.py"
        f.parent.mkdir(parents=True)
        f.write_text("print('hello')")
        assert not spec_info.project_has_specs(str(f))

    def test_empty_spec_dir(self, tmp_path: Path):
        (tmp_path / "docs" / "spec").mkdir(parents=True)
        f = tmp_path / "src" / "main.py"
        f.parent.mkdir(parents=True)
        f.write_text("x = 1")
        assert not spec_info.project_has_specs(str(f))

    def test_spec_dir_with_specs(self, tmp_path: Path):
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "01-feature.md").write_text("[SPEC-01.01] Requirement")
        f = tmp_path / "src" / "main.py"
        f.parent.mkdir(parents=True)
        f.write_text("x = 1")
        assert spec_info.project_has_specs(str(f))

    def test_spec_dir_without_spec_refs(self, tmp_path: Path):
        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "overview.md").write_text("Just an overview, no specs yet")
        f = tmp_path / "src" / "main.py"
        f.parent.mkdir(parents=True)
        f.write_text("x = 1")
        assert not spec_info.project_has_specs(str(f))


class TestFileHasSpecRefs:
    def test_file_with_refs(self, tmp_path: Path):
        f = tmp_path / "main.py"
        f.write_text("# @trace SPEC-01.05\ndef foo(): pass")
        assert spec_info.file_has_spec_refs(str(f)) == {"SPEC-01.05"}

    def test_file_without_refs(self, tmp_path: Path):
        f = tmp_path / "main.py"
        f.write_text("def foo(): pass")
        assert spec_info.file_has_spec_refs(str(f)) == set()

    def test_nonexistent_file(self):
        assert spec_info.file_has_spec_refs("/nonexistent/file.py") == set()


def make_stdin(file_path: str) -> StringIO:
    return StringIO(json.dumps({"toolInput": {"file_path": file_path}}))


class TestMainDecisions:
    """Test the full main() decision logic."""

    def _run(self, file_path: str, phase: str = "", rigor: str = "", project_specs: bool = False, file_specs: set | None = None):
        """Run main() with mocked dependencies, return parsed JSON output."""
        stdout = StringIO()
        stdin = make_stdin(file_path)
        with patch("sys.stdin", stdin), \
             patch("sys.stdout", stdout), \
             patch.object(spec_info, "get_phase_and_rigor", return_value=(phase, rigor)), \
             patch.object(spec_info, "project_has_specs", return_value=project_specs), \
             patch.object(spec_info, "file_has_spec_refs", return_value=file_specs or set()):
            spec_info.main()
        return json.loads(stdout.getvalue())

    def test_no_file_path_approves(self):
        stdout = StringIO()
        stdin = StringIO(json.dumps({"toolInput": {"file_path": ""}}))
        with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            spec_info.main()
        result = json.loads(stdout.getvalue())
        assert result["decision"] == "approve"

    def test_skip_file_approves(self):
        result = self._run("/src/tests/test_foo.py")
        assert result["decision"] == "approve"
        assert "Skipped" in result["reason"]

    def test_file_with_spec_refs_approves(self):
        result = self._run("/src/main.py", phase="implement", rigor="large",
                          project_specs=True, file_specs={"SPEC-01.01"})
        assert result["decision"] == "approve"
        assert "SPEC-01.01" in result["reason"]

    def test_orient_phase_approves(self):
        result = self._run("/src/main.py", phase="orient")
        assert result["decision"] == "approve"
        assert "not enforcing" in result["reason"]

    def test_spec_phase_approves(self):
        result = self._run("/src/main.py", phase="spec")
        assert result["decision"] == "approve"

    def test_unknown_phase_approves(self):
        result = self._run("/src/main.py", phase="")
        assert result["decision"] == "approve"

    def test_trivial_rigor_approves(self):
        result = self._run("/src/main.py", phase="implement", rigor="trivial",
                          project_specs=True)
        assert result["decision"] == "approve"
        assert "trivial" in result["reason"]

    def test_no_project_specs_approves(self):
        result = self._run("/src/main.py", phase="implement", rigor="medium",
                          project_specs=False)
        assert result["decision"] == "approve"
        assert "no specs yet" in result["reason"]

    def test_implement_phase_with_specs_no_refs_denies(self):
        result = self._run("/src/main.py", phase="implement", rigor="medium",
                          project_specs=True)
        output = result["hookSpecificOutput"]
        assert output["permissionDecision"] == "deny"
        assert "no SPEC references" in output["permissionDecisionReason"]
        assert "To proceed" in output["permissionDecisionReason"]

    def test_review_phase_with_specs_no_refs_denies(self):
        result = self._run("/src/main.py", phase="review", rigor="large",
                          project_specs=True)
        output = result["hookSpecificOutput"]
        assert output["permissionDecision"] == "deny"

    def test_exception_approves(self):
        """Errors should never block."""
        stdout = StringIO()
        stdin = StringIO("not json")
        with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            spec_info.main()
        result = json.loads(stdout.getvalue())
        assert result["decision"] == "approve"
