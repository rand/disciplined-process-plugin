"""
Tests for lib/degradation module.

Covers:
- DegradationLevel enum and ordering
- HealthStatus dataclass
- SystemState management
- State persistence
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies as st

# Import module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Need to mock get_project_dir before importing degradation
with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/tmp"}):
    from lib.degradation import (
        DegradationLevel,
        HealthStatus,
        SystemState,
        _deserialize_state,
        _serialize_state,
        compute_degradation_level,
        transition_to,
    )


class TestDegradationLevel:
    """Tests for DegradationLevel enum."""

    def test_has_five_levels(self):
        """Should have exactly five degradation levels."""
        levels = list(DegradationLevel)
        assert len(levels) == 5

    def test_level_names(self):
        """Each level should have correct name."""
        assert DegradationLevel.FULL.name == "FULL"
        assert DegradationLevel.REDUCED.name == "REDUCED"
        assert DegradationLevel.MANUAL.name == "MANUAL"
        assert DegradationLevel.SAFE.name == "SAFE"
        assert DegradationLevel.RECOVERY.name == "RECOVERY"

    def test_levels_are_orderable_by_value(self):
        """Levels should be orderable by value for comparison."""
        assert DegradationLevel.FULL.value < DegradationLevel.REDUCED.value
        assert DegradationLevel.REDUCED.value < DegradationLevel.MANUAL.value
        assert DegradationLevel.MANUAL.value < DegradationLevel.SAFE.value
        assert DegradationLevel.SAFE.value < DegradationLevel.RECOVERY.value


class TestHealthStatus:
    """Tests for HealthStatus dataclass."""

    def test_creates_with_required_fields(self):
        """Should create health status with required fields."""
        status = HealthStatus(
            healthy=True,
            component="test_component",
            message="OK",
        )
        assert status.healthy is True
        assert status.component == "test_component"
        assert status.message == "OK"

    def test_default_last_check(self):
        """Last check should default to now."""
        status = HealthStatus(healthy=True, component="test", message="OK")
        assert isinstance(status.last_check, datetime)

    def test_default_recovery_flags(self):
        """Recovery flags should default to False."""
        status = HealthStatus(healthy=True, component="test", message="OK")
        assert status.recovery_attempted is False
        assert status.recovery_succeeded is False

    def test_unhealthy_status(self):
        """Should create unhealthy status."""
        status = HealthStatus(
            healthy=False,
            component="git",
            message="Git not found",
        )
        assert status.healthy is False
        assert "not found" in status.message


class TestSystemState:
    """Tests for SystemState dataclass."""

    def test_creates_with_defaults(self):
        """Should create with sensible defaults."""
        state = SystemState(level=DegradationLevel.FULL)
        assert state.level == DegradationLevel.FULL
        assert state.components == {}
        assert state.locked is False

    def test_add_component_status(self):
        """Should track component health statuses."""
        state = SystemState(level=DegradationLevel.FULL)
        state.components["test"] = HealthStatus(
            healthy=True,
            component="test",
            message="OK",
        )

        assert "test" in state.components
        assert state.components["test"].healthy is True

    def test_locked_state(self):
        """Should track locked state."""
        state = SystemState(
            level=DegradationLevel.MANUAL,
            locked=True,
            lock_reason="Manual intervention",
        )
        assert state.locked is True
        assert state.lock_reason == "Manual intervention"


class TestStateSerialization:
    """Tests for state serialization/deserialization."""

    def test_serialize_state(self):
        """Should serialize state to dict."""
        state = SystemState(
            level=DegradationLevel.REDUCED,
            transition_reason="Test",
        )
        state.components["test"] = HealthStatus(
            healthy=True,
            component="test",
            message="OK",
        )

        data = _serialize_state(state)

        assert data["level"] == "REDUCED"
        assert "test" in data["components"]
        assert data["components"]["test"]["healthy"] is True

    def test_deserialize_state(self):
        """Should deserialize state from dict."""
        data = {
            "level": "MANUAL",
            "last_transition": datetime.now().isoformat(),
            "transition_reason": "Config issue",
            "locked": True,
            "lock_reason": "User locked",
            "components": {
                "config": {
                    "healthy": False,
                    "component": "config",
                    "message": "Invalid config",
                    "last_check": datetime.now().isoformat(),
                    "recovery_attempted": True,
                    "recovery_succeeded": False,
                }
            },
        }

        state = _deserialize_state(data)

        assert state.level == DegradationLevel.MANUAL
        assert state.locked is True
        assert "config" in state.components
        assert state.components["config"].healthy is False

    def test_roundtrip_serialization(self):
        """State should survive serialize/deserialize roundtrip."""
        original = SystemState(
            level=DegradationLevel.SAFE,
            transition_reason="Git issues",
            locked=False,
        )
        original.components["git"] = HealthStatus(
            healthy=False,
            component="git",
            message="Git timeout",
        )

        serialized = _serialize_state(original)
        restored = _deserialize_state(serialized)

        assert restored.level == original.level
        assert restored.transition_reason == original.transition_reason
        assert "git" in restored.components
        assert restored.components["git"].healthy is False


class TestComputeDegradationLevel:
    """Tests for compute_degradation_level function."""

    def test_full_when_all_healthy(self):
        """Should return FULL when all components healthy."""
        components = {
            "git": HealthStatus(healthy=True, component="git", message="OK"),
            "config": HealthStatus(healthy=True, component="config", message="OK"),
            "task_tracker": HealthStatus(healthy=True, component="task_tracker", message="OK"),
        }

        level = compute_degradation_level(components)
        assert level == DegradationLevel.FULL

    def test_safe_when_git_unhealthy(self):
        """Should return SAFE when git is unhealthy."""
        components = {
            "git": HealthStatus(healthy=False, component="git", message="Not found"),
            "config": HealthStatus(healthy=True, component="config", message="OK"),
        }

        level = compute_degradation_level(components)
        assert level == DegradationLevel.SAFE

    def test_manual_when_config_unhealthy(self):
        """Should return MANUAL when config is unhealthy."""
        components = {
            "git": HealthStatus(healthy=True, component="git", message="OK"),
            "config": HealthStatus(healthy=False, component="config", message="Invalid"),
        }

        level = compute_degradation_level(components)
        assert level == DegradationLevel.MANUAL

    def test_reduced_when_task_tracker_unhealthy(self):
        """Should return REDUCED when task tracker is unhealthy."""
        components = {
            "git": HealthStatus(healthy=True, component="git", message="OK"),
            "config": HealthStatus(healthy=True, component="config", message="OK"),
            "task_tracker": HealthStatus(healthy=False, component="task_tracker", message="Not found"),
        }

        level = compute_degradation_level(components)
        assert level == DegradationLevel.REDUCED


class TestTransitionTo:
    """Tests for transition_to function."""

    def test_transitions_when_not_locked(self):
        """Should transition when state is not locked."""
        state = SystemState(level=DegradationLevel.FULL)

        new_state = transition_to(state, DegradationLevel.REDUCED, "Test reason")

        assert new_state.level == DegradationLevel.REDUCED
        assert new_state.transition_reason == "Test reason"

    def test_no_transition_when_locked(self):
        """Should not transition when state is locked."""
        state = SystemState(level=DegradationLevel.FULL, locked=True)

        new_state = transition_to(state, DegradationLevel.SAFE, "Should not happen")

        assert new_state.level == DegradationLevel.FULL

    def test_updates_transition_time(self):
        """Should update last_transition time."""
        state = SystemState(level=DegradationLevel.FULL)
        original_time = state.last_transition

        new_state = transition_to(state, DegradationLevel.REDUCED, "Test")

        assert new_state.last_transition >= original_time


class TestPropertyBasedDegradation:
    """Property-based tests for degradation module."""

    @given(st.sampled_from(list(DegradationLevel)))
    def test_any_level_can_be_set(self, level: DegradationLevel):
        """Any degradation level should be settable."""
        state = SystemState(level=level)
        assert state.level == level

    @given(st.booleans(), st.text(min_size=1, max_size=50))
    def test_health_status_creation(self, healthy: bool, message: str):
        """HealthStatus should accept any valid inputs."""
        status = HealthStatus(healthy=healthy, component="test", message=message)
        assert status.healthy == healthy
        assert status.message == message

    @given(
        st.sampled_from(list(DegradationLevel)),
        st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=20)
    def test_state_serialization_roundtrip(self, level: DegradationLevel, reason: str):
        """State should survive serialization roundtrip."""
        original = SystemState(level=level, transition_reason=reason)

        serialized = _serialize_state(original)
        restored = _deserialize_state(serialized)

        assert restored.level == original.level
        assert restored.transition_reason == original.transition_reason
