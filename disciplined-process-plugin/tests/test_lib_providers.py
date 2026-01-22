"""
Tests for lib/providers module.

Covers:
- Provider availability checking
- ProviderStatus dataclass
- Warning file management
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies as st

# Import module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.config import TaskTracker
from lib.providers import (
    ProviderStatus,
    check_cli_available,
    check_provider_available,
    get_project_dir,
    get_ready_count,
    should_warn_about_provider,
    sync_tracker,
)


class TestProviderStatus:
    """Tests for ProviderStatus dataclass."""

    def test_creates_with_availability(self):
        """Should create with basic fields."""
        status = ProviderStatus(available=True)
        assert status.available is True

    def test_default_reason_none(self):
        """Reason should default to None."""
        status = ProviderStatus(available=True)
        assert status.reason is None

    def test_default_ready_count_none(self):
        """Ready count should default to None."""
        status = ProviderStatus(available=True)
        assert status.ready_count is None

    def test_with_reason(self):
        """Should store reason information."""
        status = ProviderStatus(
            available=False,
            reason="CLI not found",
        )
        assert status.available is False
        assert status.reason == "CLI not found"


class TestCheckCliAvailable:
    """Tests for check_cli_available function."""

    def test_returns_true_for_common_commands(self):
        """Common commands like 'ls' should be available."""
        # This test depends on the environment
        assert check_cli_available("ls") is True

    def test_returns_false_for_nonexistent_command(self):
        """Nonexistent commands should return False."""
        assert check_cli_available("nonexistent_command_xyz_123") is False


class TestCheckProviderAvailable:
    """Tests for check_provider_available function."""

    def test_beads_unavailable_without_cli(self, temp_project_dir: Path):
        """Beads should be unavailable if bd CLI not found."""
        with patch("lib.providers.check_cli_available", return_value=False):
            status = check_provider_available(TaskTracker.BEADS, temp_project_dir)
            assert status.available is False
            assert "bd" in status.reason.lower()

    def test_beads_unavailable_without_directory(self, temp_project_dir: Path):
        """Beads should be unavailable if .beads/ doesn't exist."""
        with patch("lib.providers.check_cli_available", return_value=True):
            status = check_provider_available(TaskTracker.BEADS, temp_project_dir)
            assert status.available is False
            assert ".beads" in status.reason.lower()

    def test_beads_available_when_configured(self, temp_project_dir: Path):
        """Beads should be available when CLI exists and directory initialized."""
        (temp_project_dir / ".beads").mkdir()
        with patch("lib.providers.check_cli_available", return_value=True):
            status = check_provider_available(TaskTracker.BEADS, temp_project_dir)
            assert status.available is True

    def test_chainlink_unavailable_without_cli(self, temp_project_dir: Path):
        """Chainlink should be unavailable if CLI not found."""
        with patch("lib.providers.check_cli_available", return_value=False):
            status = check_provider_available(TaskTracker.CHAINLINK, temp_project_dir)
            assert status.available is False
            assert "chainlink" in status.reason.lower()

    def test_github_unavailable_without_gh(self, temp_project_dir: Path):
        """GitHub should be unavailable if gh CLI not found."""
        with patch("lib.providers.check_cli_available", return_value=False):
            status = check_provider_available(TaskTracker.GITHUB, temp_project_dir)
            assert status.available is False
            assert "gh" in status.reason.lower()

    def test_markdown_always_available(self, temp_project_dir: Path):
        """Markdown provider should always be available."""
        status = check_provider_available(TaskTracker.MARKDOWN, temp_project_dir)
        assert status.available is True

    def test_none_provider_always_available(self, temp_project_dir: Path):
        """None provider should always be available."""
        status = check_provider_available(TaskTracker.NONE, temp_project_dir)
        assert status.available is True


class TestShouldWarnAboutProvider:
    """Tests for should_warn_about_provider function."""

    def test_returns_true_when_no_warn_file(self, temp_project_dir: Path):
        """Should return True when warn file doesn't exist."""
        warn_file = temp_project_dir / ".dp-provider-warned"
        assert should_warn_about_provider(warn_file) is True

    def test_returns_false_when_recently_warned(self, temp_project_dir: Path):
        """Should return False when warned recently."""
        warn_file = temp_project_dir / ".dp-provider-warned"
        warn_file.touch()
        assert should_warn_about_provider(warn_file) is False


class TestSyncTracker:
    """Tests for sync_tracker function."""

    def test_markdown_sync_always_succeeds(self, temp_project_dir: Path):
        """Markdown sync should always succeed."""
        result = sync_tracker(TaskTracker.MARKDOWN, temp_project_dir)
        assert result is True

    def test_none_sync_always_succeeds(self, temp_project_dir: Path):
        """None provider sync should always succeed."""
        result = sync_tracker(TaskTracker.NONE, temp_project_dir)
        assert result is True


class TestPropertyBasedProviders:
    """Property-based tests for providers module."""

    @given(st.sampled_from(list(TaskTracker)))
    def test_all_trackers_return_status(self, tracker: TaskTracker):
        """All tracker types should return a ProviderStatus."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project_dir = Path(tmpdir)
            with patch("lib.providers.check_cli_available", return_value=False):
                status = check_provider_available(tracker, temp_project_dir)

            assert isinstance(status, ProviderStatus)
            assert isinstance(status.available, bool)

    @given(st.sampled_from([TaskTracker.MARKDOWN, TaskTracker.NONE]))
    def test_always_available_trackers(self, tracker: TaskTracker):
        """Markdown and None should always be available."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project_dir = Path(tmpdir)
            status = check_provider_available(tracker, temp_project_dir)
            assert status.available is True
