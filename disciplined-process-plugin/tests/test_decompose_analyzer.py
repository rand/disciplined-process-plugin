"""Tests for spec file reading and analysis.

@trace SPEC-07
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.spec_decompose.analyzer import (
    SpecBundle,
    SpecFile,
    read_spec_files,
)


class TestReadSpecFiles:
    """Tests for reading spec files."""

    def test_single_file(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Auth Spec\n[SPEC-01.01] Login requirement\n")

        bundle = read_spec_files([spec])
        assert len(bundle.files) == 1
        assert bundle.total_tokens > 0
        assert "SPEC-01.01" in bundle.all_spec_ids

    def test_multiple_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("[SPEC-01.01] A\n")
        (tmp_path / "b.md").write_text("[SPEC-02.01] B\n")

        bundle = read_spec_files([tmp_path / "a.md", tmp_path / "b.md"])
        assert len(bundle.files) == 2
        assert "SPEC-01.01" in bundle.all_spec_ids
        assert "SPEC-02.01" in bundle.all_spec_ids

    def test_directory_input(self, tmp_path: Path) -> None:
        (tmp_path / "spec1.md").write_text("[SPEC-01.01] First\n")
        (tmp_path / "spec2.md").write_text("[SPEC-02.01] Second\n")

        bundle = read_spec_files([tmp_path])
        assert len(bundle.files) == 2

    def test_combined_text(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("Content A\n")
        (tmp_path / "b.md").write_text("Content B\n")

        bundle = read_spec_files([tmp_path / "a.md", tmp_path / "b.md"])
        text = bundle.combined_text
        assert "Content A" in text
        assert "Content B" in text

    def test_nonexistent_file(self) -> None:
        bundle = read_spec_files([Path("/nonexistent/spec.md")])
        assert len(bundle.files) == 0

    def test_empty_directory(self, tmp_path: Path) -> None:
        bundle = read_spec_files([tmp_path])
        assert len(bundle.files) == 0

    def test_sharding_threshold(self, tmp_path: Path) -> None:
        # Small file should not need sharding
        spec = tmp_path / "small.md"
        spec.write_text("Small spec\n")
        bundle = read_spec_files([spec])
        assert not bundle.needs_sharding

    def test_spec_id_extraction(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("""
[SPEC-01] Overview
[SPEC-01.01] Login with email
[SPEC-01.02] Password reset
[SPEC-02.01] Session management
""")
        bundle = read_spec_files([spec])
        assert "SPEC-01" in bundle.all_spec_ids
        assert "SPEC-01.01" in bundle.all_spec_ids
        assert "SPEC-01.02" in bundle.all_spec_ids
        assert "SPEC-02.01" in bundle.all_spec_ids

    def test_no_duplicate_spec_ids(self, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("[SPEC-01.01] First mention\n[SPEC-01.01] Second mention\n")
        bundle = read_spec_files([spec])
        assert bundle.all_spec_ids.count("SPEC-01.01") == 1
