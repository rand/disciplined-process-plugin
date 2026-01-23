"""
Tests for lib/config module.

Covers:
- Configuration dataclasses
- Enum values
- Configuration parsing
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

# Import module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.config import (
    ADRConfig,
    AdversarialConfig,
    BeadsConfig,
    BuiltinConfig,
    ChainlinkConfig,
    ConfigVersion,
    DegradationAction,
    EnforcementLevel,
    SpecConfig,
    TaskTracker,
    TestingConfig,
)


class TestEnforcementLevel:
    """Tests for EnforcementLevel enum."""

    def test_has_three_levels(self):
        """Should have exactly three enforcement levels."""
        levels = list(EnforcementLevel)
        assert len(levels) == 3

    def test_strict_value(self):
        """Strict level should have correct value."""
        assert EnforcementLevel.STRICT.value == "strict"

    def test_guided_value(self):
        """Guided level should have correct value."""
        assert EnforcementLevel.GUIDED.value == "guided"

    def test_minimal_value(self):
        """Minimal level should have correct value."""
        assert EnforcementLevel.MINIMAL.value == "minimal"

    def test_can_compare_levels(self):
        """Should be able to compare enforcement levels."""
        assert EnforcementLevel.STRICT != EnforcementLevel.GUIDED
        assert EnforcementLevel.GUIDED != EnforcementLevel.MINIMAL


class TestTaskTracker:
    """Tests for TaskTracker enum."""

    def test_has_expected_trackers(self):
        """Should have all expected tracker types."""
        tracker_values = [t.value for t in TaskTracker]
        assert "chainlink" in tracker_values
        assert "beads" in tracker_values
        assert "builtin" in tracker_values
        assert "github" in tracker_values
        assert "linear" in tracker_values
        assert "markdown" in tracker_values
        assert "none" in tracker_values

    def test_builtin_value(self):
        """Builtin tracker should have correct value."""
        assert TaskTracker.BUILTIN.value == "builtin"


class TestDegradationAction:
    """Tests for DegradationAction enum."""

    def test_has_expected_actions(self):
        """Should have warn, skip, and fail actions."""
        action_values = [a.value for a in DegradationAction]
        assert "warn" in action_values
        assert "skip" in action_values
        assert "fail" in action_values


class TestConfigVersion:
    """Tests for ConfigVersion enum."""

    def test_has_v1_and_v2(self):
        """Should have both v1 and v2 versions."""
        versions = [v.value for v in ConfigVersion]
        assert "1.0" in versions
        assert "2.0" in versions


class TestChainlinkConfig:
    """Tests for ChainlinkConfig dataclass."""

    def test_default_sessions_enabled(self):
        """Sessions should be enabled by default."""
        config = ChainlinkConfig()
        assert config.sessions is True

    def test_default_milestones_enabled(self):
        """Milestones should be enabled by default."""
        config = ChainlinkConfig()
        assert config.milestones is True

    def test_default_time_tracking_disabled(self):
        """Time tracking should be disabled by default."""
        config = ChainlinkConfig()
        assert config.time_tracking is False

    def test_default_rules_path(self):
        """Default rules path should be set."""
        config = ChainlinkConfig()
        assert config.rules_path == ".claude/rules/"

    def test_custom_values(self):
        """Should accept custom values."""
        config = ChainlinkConfig(
            sessions=False,
            milestones=False,
            time_tracking=True,
            rules_path="custom/path/",
        )
        assert config.sessions is False
        assert config.time_tracking is True
        assert config.rules_path == "custom/path/"


class TestBeadsConfig:
    """Tests for BeadsConfig dataclass."""

    def test_default_auto_sync_enabled(self):
        """Auto sync should be enabled by default."""
        config = BeadsConfig()
        assert config.auto_sync is True

    def test_default_daemon_enabled(self):
        """Daemon should be enabled by default."""
        config = BeadsConfig()
        assert config.daemon is True

    def test_default_prefix_none(self):
        """Prefix should be None by default."""
        config = BeadsConfig()
        assert config.prefix is None


class TestBuiltinConfig:
    """Tests for BuiltinConfig dataclass."""

    def test_default_task_list_id_none(self):
        """Task list ID should be None by default (auto-generated)."""
        config = BuiltinConfig()
        assert config.task_list_id is None

    def test_default_auto_set_env_enabled(self):
        """Auto-set env var should be enabled by default."""
        config = BuiltinConfig()
        assert config.auto_set_env is True

    def test_custom_task_list_id(self):
        """Should accept custom task list ID."""
        config = BuiltinConfig(task_list_id="my-project-tasks")
        assert config.task_list_id == "my-project-tasks"

    def test_disable_auto_set_env(self):
        """Should allow disabling auto-set env."""
        config = BuiltinConfig(auto_set_env=False)
        assert config.auto_set_env is False


class TestAdversarialConfig:
    """Tests for AdversarialConfig dataclass."""

    def test_default_disabled(self):
        """Adversarial review should be disabled by default."""
        config = AdversarialConfig()
        assert config.enabled is False

    def test_default_model(self):
        """Default model should be gemini-2.0-flash."""
        config = AdversarialConfig()
        assert config.model == "gemini-2.0-flash"

    def test_default_max_iterations(self):
        """Default max iterations should be 3."""
        config = AdversarialConfig()
        assert config.max_iterations == 3

    def test_default_trigger(self):
        """Default trigger should be on_review."""
        config = AdversarialConfig()
        assert config.trigger == "on_review"

    def test_default_fresh_context(self):
        """Fresh context should be enabled by default."""
        config = AdversarialConfig()
        assert config.fresh_context is True

    def test_custom_values(self):
        """Should accept custom values."""
        config = AdversarialConfig(
            enabled=True,
            model="gpt-4",
            max_iterations=10,
        )
        assert config.enabled is True
        assert config.model == "gpt-4"
        assert config.max_iterations == 10


class TestSpecConfig:
    """Tests for SpecConfig dataclass."""

    def test_default_directory(self):
        """Default spec directory should be docs/spec."""
        config = SpecConfig()
        assert config.directory == "docs/spec"

    def test_default_id_format(self):
        """Default ID format should follow SPEC-XX.YY pattern."""
        config = SpecConfig()
        assert "SPEC" in config.id_format
        assert "section" in config.id_format

    def test_default_require_issue_link(self):
        """Require issue link should be False by default."""
        config = SpecConfig()
        assert config.require_issue_link is False


class TestADRConfig:
    """Tests for ADRConfig dataclass."""

    def test_default_directory(self):
        """Default ADR directory should be docs/adr."""
        config = ADRConfig()
        assert config.directory == "docs/adr"

    def test_default_id_format(self):
        """Default ID format should include ADR."""
        config = ADRConfig()
        assert "ADR" in config.id_format

    def test_default_template_none(self):
        """Template should be None by default."""
        config = ADRConfig()
        assert config.template is None


class TestTestingConfigDataclass:
    """Tests for TestingConfig dataclass."""

    def test_default_frameworks_none(self):
        """Default frameworks should be None (auto-detect)."""
        config = TestingConfig()
        assert config.unit_framework is None
        assert config.integration_framework is None
        assert config.property_framework is None
        assert config.e2e_framework is None

    def test_default_directories(self):
        """Default test directories should be set."""
        config = TestingConfig()
        assert config.unit_dir == "tests/unit"
        assert config.integration_dir == "tests/integration"
        assert config.property_dir == "tests/property"
        assert config.e2e_dir == "tests/e2e"


class TestPropertyBasedConfig:
    """Property-based tests for configuration."""

    @given(st.booleans(), st.booleans(), st.booleans())
    def test_chainlink_config_accepts_any_booleans(
        self, sessions: bool, milestones: bool, time_tracking: bool
    ):
        """ChainlinkConfig should accept any combination of booleans."""
        config = ChainlinkConfig(
            sessions=sessions,
            milestones=milestones,
            time_tracking=time_tracking,
        )
        assert config.sessions == sessions
        assert config.milestones == milestones
        assert config.time_tracking == time_tracking

    @given(st.integers(min_value=1, max_value=100))
    def test_adversarial_max_iterations(self, max_iter: int):
        """AdversarialConfig should accept positive iteration counts."""
        config = AdversarialConfig(max_iterations=max_iter)
        assert config.max_iterations == max_iter

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=20)
    def test_spec_directory_paths(self, directory: str):
        """SpecConfig should accept various directory paths."""
        config = SpecConfig(directory=directory)
        assert config.directory == directory
