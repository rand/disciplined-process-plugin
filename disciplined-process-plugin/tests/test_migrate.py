"""
Tests for migrate.py migration script.

@trace SPEC-01.11
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestIssueMapping:
    """Test IssueMapping dataclass."""

    def test_basic_mapping(self):
        """Should store source to target mapping."""
        from migrate import IssueMapping

        mapping = IssueMapping(
            source_id="bd-001",
            target_id="CL-1",
            title="Test Issue",
            spec_refs=["SPEC-01.01"],
        )

        assert mapping.source_id == "bd-001"
        assert mapping.target_id == "CL-1"
        assert mapping.title == "Test Issue"
        assert mapping.spec_refs == ["SPEC-01.01"]

    def test_default_spec_refs(self):
        """Should default to empty spec_refs."""
        from migrate import IssueMapping

        mapping = IssueMapping(
            source_id="a", target_id="b", title="c"
        )
        assert mapping.spec_refs == []


class TestMigrationResult:
    """Test MigrationResult dataclass."""

    def test_successful_result(self):
        """Should represent successful migration."""
        from migrate import IssueMapping, MigrationResult

        result = MigrationResult(
            success=True,
            source="beads",
            target="chainlink",
            issues_migrated=5,
            dependencies_migrated=3,
            mappings=[],
        )

        assert result.success is True
        assert result.issues_migrated == 5
        assert result.dependencies_migrated == 3

    def test_failed_result_with_errors(self):
        """Should include errors on failure."""
        from migrate import MigrationResult

        result = MigrationResult(
            success=False,
            source="beads",
            target="chainlink",
            issues_migrated=0,
            dependencies_migrated=0,
            mappings=[],
            errors=["CLI not found", "Permission denied"],
        )

        assert result.success is False
        assert len(result.errors) == 2


class TestParseBeadsIssues:
    """Test Beads issue parsing."""

    def test_parses_jsonl_file(self, tmp_path: Path):
        """Should parse issues from JSONL format."""
        from migrate import parse_beads_issues

        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        issues_file = beads_dir / "issues.jsonl"
        issues_file.write_text(
            '{"id": "bd-001", "title": "First"}\n'
            '{"id": "bd-002", "title": "Second"}\n'
        )

        issues = parse_beads_issues(beads_dir)

        assert len(issues) == 2
        assert issues[0]["id"] == "bd-001"
        assert issues[1]["title"] == "Second"

    def test_skips_empty_lines(self, tmp_path: Path):
        """Should skip empty lines in JSONL."""
        from migrate import parse_beads_issues

        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        issues_file = beads_dir / "issues.jsonl"
        issues_file.write_text(
            '{"id": "bd-001", "title": "First"}\n'
            '\n'
            '{"id": "bd-002", "title": "Second"}\n'
        )

        issues = parse_beads_issues(beads_dir)
        assert len(issues) == 2

    def test_raises_on_missing_file(self, tmp_path: Path):
        """Should raise error if issues file not found."""
        from migrate import parse_beads_issues

        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        # No issues.jsonl created

        with pytest.raises(FileNotFoundError):
            parse_beads_issues(beads_dir)


class TestExtractSpecRefs:
    """Test spec reference extraction."""

    def test_extracts_single_spec(self):
        """Should extract single spec reference."""
        from migrate import extract_spec_refs

        text = "Implements [SPEC-01.05] for user login"
        refs = extract_spec_refs(text)

        assert refs == ["SPEC-01.05"]

    def test_extracts_multiple_specs(self):
        """Should extract multiple spec references."""
        from migrate import extract_spec_refs

        text = "Covers [SPEC-01.01] and [SPEC-02.03]"
        refs = extract_spec_refs(text)

        assert len(refs) == 2
        assert "SPEC-01.01" in refs
        assert "SPEC-02.03" in refs

    def test_returns_empty_for_no_specs(self):
        """Should return empty list when no specs found."""
        from migrate import extract_spec_refs

        text = "Just a regular description without specs"
        refs = extract_spec_refs(text)

        assert refs == []

    def test_handles_none_text(self):
        """Should handle None text gracefully."""
        from migrate import extract_spec_refs

        refs = extract_spec_refs(None)
        assert refs == []


class TestPriorityMapping:
    """Test priority conversion between trackers."""

    def test_beads_to_chainlink_mapping(self):
        """Should map Beads numeric priorities to Chainlink strings."""
        from migrate import map_beads_priority

        assert map_beads_priority(0) == "critical"
        assert map_beads_priority(1) == "high"
        assert map_beads_priority(2) == "medium"
        assert map_beads_priority(3) == "low"
        assert map_beads_priority(4) == "low"

    def test_chainlink_to_beads_mapping(self):
        """Should map Chainlink string priorities to Beads numeric."""
        from migrate import map_chainlink_priority

        assert map_chainlink_priority("critical") == 0
        assert map_chainlink_priority("high") == 1
        assert map_chainlink_priority("medium") == 2
        assert map_chainlink_priority("low") == 3

    def test_case_insensitive_chainlink_mapping(self):
        """Should handle case-insensitive Chainlink priorities."""
        from migrate import map_chainlink_priority

        assert map_chainlink_priority("HIGH") == 1
        assert map_chainlink_priority("Medium") == 2

    def test_default_for_unknown_priority(self):
        """Should default to medium for unknown priorities."""
        from migrate import map_beads_priority, map_chainlink_priority

        assert map_beads_priority(99) == "medium"
        assert map_chainlink_priority("unknown") == 2


class TestMetadataEmbedding:
    """Test metadata embedding in task subjects."""

    def test_embed_priority(self):
        """Should embed priority as prefix."""
        from migrate import embed_metadata_in_subject

        subject = embed_metadata_in_subject("Fix bug", priority=1)
        assert subject == "[P1] Fix bug"

    def test_embed_type(self):
        """Should embed issue type as prefix."""
        from migrate import embed_metadata_in_subject

        subject = embed_metadata_in_subject("Add feature", issue_type="feature")
        assert subject == "[feature] Add feature"

    def test_embed_both(self):
        """Should embed both priority and type."""
        from migrate import embed_metadata_in_subject

        subject = embed_metadata_in_subject("Critical bug", priority=0, issue_type="bug")
        assert subject == "[P0] [bug] Critical bug"

    def test_no_embedding_with_none(self):
        """Should return original title when no metadata."""
        from migrate import embed_metadata_in_subject

        subject = embed_metadata_in_subject("Plain title")
        assert subject == "Plain title"


class TestMetadataExtraction:
    """Test metadata extraction from task subjects."""

    def test_extract_priority_only(self):
        """Should extract priority from subject."""
        from migrate import extract_metadata_from_subject

        title, priority, issue_type = extract_metadata_from_subject("[P1] Fix bug")

        assert title == "Fix bug"
        assert priority == 1
        assert issue_type == "task"  # Default

    def test_extract_type_only(self):
        """Should extract type from subject."""
        from migrate import extract_metadata_from_subject

        title, priority, issue_type = extract_metadata_from_subject("[bug] Fix error")

        assert title == "Fix error"
        assert priority == 2  # Default
        assert issue_type == "bug"

    def test_extract_both(self):
        """Should extract both priority and type."""
        from migrate import extract_metadata_from_subject

        title, priority, issue_type = extract_metadata_from_subject(
            "[P0] [feature] New login"
        )

        assert title == "New login"
        assert priority == 0
        assert issue_type == "feature"

    def test_extract_plain_subject(self):
        """Should handle plain subjects without metadata."""
        from migrate import extract_metadata_from_subject

        title, priority, issue_type = extract_metadata_from_subject("Plain title")

        assert title == "Plain title"
        assert priority == 2  # Default medium
        assert issue_type == "task"  # Default


class TestLabelEmbedding:
    """Test label embedding in descriptions."""

    def test_embed_labels(self):
        """Should append labels to description."""
        from migrate import embed_labels_in_description

        desc = embed_labels_in_description("Original description", ["urgent", "frontend"])

        assert "Original description" in desc
        assert "Labels: urgent, frontend" in desc

    def test_no_labels(self):
        """Should return unchanged description with no labels."""
        from migrate import embed_labels_in_description

        desc = embed_labels_in_description("Original", [])
        assert desc == "Original"


class TestLabelExtraction:
    """Test label extraction from descriptions."""

    def test_extract_labels(self):
        """Should extract labels from description footer."""
        from migrate import extract_labels_from_description

        text = "Description text\n\n---\nLabels: bug, urgent, P1"
        desc, labels = extract_labels_from_description(text)

        assert desc == "Description text"
        assert len(labels) == 3
        assert "bug" in labels
        assert "urgent" in labels

    def test_no_labels_in_description(self):
        """Should return empty labels when none embedded."""
        from migrate import extract_labels_from_description

        desc, labels = extract_labels_from_description("Plain description")

        assert desc == "Plain description"
        assert labels == []


class TestMigrateBeadsToChainlink:
    """Test Beads to Chainlink migration."""

    def test_fails_without_beads_dir(self, tmp_path: Path):
        """Should fail if .beads directory doesn't exist."""
        from migrate import migrate_beads_to_chainlink

        result = migrate_beads_to_chainlink(tmp_path, dry_run=True)

        assert result.success is False
        assert ".beads/ directory not found" in result.errors

    def test_dry_run_creates_no_issues(self, tmp_path: Path):
        """Should not create issues in dry run mode."""
        from migrate import migrate_beads_to_chainlink

        # Create mock beads setup
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        (beads_dir / "issues.jsonl").write_text(
            '{"id": "bd-001", "title": "Test Issue", "priority": 2}\n'
        )

        with patch("migrate.subprocess.run") as mock_run:
            # Mock chainlink check
            mock_run.return_value = MagicMock(returncode=0)

            result = migrate_beads_to_chainlink(tmp_path, dry_run=True)

            # Should report issue but not actually create
            assert result.issues_migrated == 1
            assert len(result.mappings) == 1


class TestMigrateChainlinkToBeads:
    """Test Chainlink to Beads migration."""

    def test_fails_without_chainlink_dir(self, tmp_path: Path):
        """Should fail if .chainlink directory doesn't exist."""
        from migrate import migrate_chainlink_to_beads

        result = migrate_chainlink_to_beads(tmp_path, dry_run=True)

        assert result.success is False
        assert ".chainlink/ directory not found" in result.errors


class TestMigrateBeadsToBuiltin:
    """Test Beads to Builtin migration."""

    def test_fails_without_beads_dir(self, tmp_path: Path):
        """Should fail if .beads directory doesn't exist."""
        from migrate import migrate_beads_to_builtin

        result = migrate_beads_to_builtin(tmp_path, dry_run=True)

        assert result.success is False
        assert ".beads/ directory not found" in result.errors

    def test_dry_run_reports_issues(self, tmp_path: Path):
        """Should report issues in dry run without creating."""
        from migrate import migrate_beads_to_builtin

        # Create mock beads setup
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        (beads_dir / "issues.jsonl").write_text(
            '{"id": "bd-001", "title": "Test", "priority": 1, "issue_type": "bug"}\n'
        )

        result = migrate_beads_to_builtin(tmp_path, dry_run=True)

        assert result.issues_migrated == 1
        assert result.mappings[0].source_id == "bd-001"


class TestMigrateBuiltinToBeads:
    """Test Builtin to Beads migration."""

    def test_succeeds_with_no_tasks(self, tmp_path: Path):
        """Should succeed when no builtin tasks exist."""
        from migrate import migrate_builtin_to_beads

        with patch("migrate.subprocess.run") as mock_run:
            # Mock bd check as available
            mock_run.return_value = MagicMock(returncode=0)

            with patch("migrate.builtin_provider.list_tasks") as mock_list:
                mock_list.return_value = []

                result = migrate_builtin_to_beads(tmp_path, dry_run=True)

                assert result.success is True
                assert result.issues_migrated == 0


class TestSaveMappingFile:
    """Test migration mapping file saving."""

    def test_saves_mapping_json(self, tmp_path: Path):
        """Should save mapping file in JSON format."""
        from migrate import IssueMapping, MigrationResult, save_mapping_file

        result = MigrationResult(
            success=True,
            source="beads",
            target="builtin",
            issues_migrated=2,
            dependencies_migrated=1,
            mappings=[
                IssueMapping("bd-001", "1", "First", ["SPEC-01.01"]),
                IssueMapping("bd-002", "2", "Second", []),
            ],
        )

        save_mapping_file(result, tmp_path)

        mapping_file = tmp_path / ".claude" / "dp-migration-map.json"
        assert mapping_file.exists()

        data = json.loads(mapping_file.read_text())
        assert data["source"] == "beads"
        assert data["target"] == "builtin"
        assert len(data["mappings"]) == 2


class TestUpdateConfig:
    """Test config file updating after migration."""

    def test_updates_tracker_setting(self, tmp_path: Path):
        """Should update task_tracker in config file."""
        from migrate import update_config

        # Create config file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        config_file = claude_dir / "dp-config.yaml"
        config_file.write_text(
            'version: "2.0"\n'
            'task_tracker: beads\n'
            'enforcement: guided\n'
        )

        update_config("builtin", tmp_path)

        content = config_file.read_text()
        assert "task_tracker: builtin" in content
        # Should preserve other settings
        assert 'version: "2.0"' in content

    def test_handles_missing_config(self, tmp_path: Path):
        """Should handle missing config file gracefully."""
        from migrate import update_config

        # Should not raise
        update_config("builtin", tmp_path)
