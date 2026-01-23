"""
End-to-end integration tests for disciplined-process plugin.

These tests verify that all major components work together correctly.
They exercise the core library without requiring external dependencies
like beads or chainlink CLIs.

@trace SPEC-00.02
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


class TestConfigLoading:
    """Test configuration loading and parsing. @trace SPEC-01.10"""

    def test_default_config_loads(self):
        """Default config should load with expected defaults."""
        from lib.config import DPConfig, TaskTracker

        config = DPConfig()
        assert config.task_tracker == TaskTracker.CHAINLINK
        assert config.version is not None

    def test_config_from_yaml(self, tmp_path: Path):
        """Config should load from YAML file. @trace SPEC-01.10"""
        from lib.config import DPConfig, TaskTracker

        config_file = tmp_path / ".claude" / "dp-config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(
            """
version: "2.0"
task_tracker: beads
beads:
  auto_sync: true
  prefix: "test"
"""
        )

        config = DPConfig.load(config_file)
        assert config.task_tracker == TaskTracker.BEADS
        assert config.beads.prefix == "test"


class TestVerificationSystem:
    """Test goal-backward verification. @trace SPEC-05"""

    def test_extract_truths_from_acceptance_criteria(self):
        """Should extract truths from acceptance criteria. @trace SPEC-05.10"""
        from lib.verification import extract_truths_from_description

        desc = """
        Acceptance Criteria:
        - User can log in with email and password
        - Invalid credentials display error message
        - Session persists across page refresh
        """
        truths = extract_truths_from_description(desc)
        assert len(truths) == 3
        # truths are returned as strings
        assert any("log in" in t.lower() for t in truths)

    def test_detect_stub_file(self, tmp_path: Path):
        """Should detect stub files. @trace SPEC-05.22"""
        from lib.verification import detect_stub

        # Stub file
        stub_file = tmp_path / "stub.py"
        stub_file.write_text("def not_implemented():\n    raise NotImplementedError()")
        assert detect_stub(stub_file) is True

        # Real implementation
        real_file = tmp_path / "real.py"
        real_file.write_text(
            """
def real_function():
    data = fetch_data()
    processed = transform(data)
    validated = validate(processed)
    return save(validated)

def another_function():
    items = get_items()
    for item in items:
        process(item)
    return len(items)
"""
        )
        assert detect_stub(real_file) is False

    def test_artifact_existence_check(self, tmp_path: Path):
        """Should verify artifact exists. @trace SPEC-05.21"""
        from lib.verification import check_artifact_exists

        # Existing file
        existing = tmp_path / "exists.py"
        existing.write_text("# content")
        result = check_artifact_exists(existing)
        assert result.exists is True

        # Missing file
        missing = tmp_path / "missing.py"
        result = check_artifact_exists(missing)
        assert result.exists is False


class TestTraceabilitySystem:
    """Test spec traceability. @trace SPEC-02"""

    def test_spec_id_pattern_matches(self):
        """Should match valid spec IDs. @trace SPEC-02.11"""
        import re

        from traceability import SPEC_ID_PATTERN

        assert re.search(SPEC_ID_PATTERN, "[SPEC-01]")
        assert re.search(SPEC_ID_PATTERN, "[SPEC-01.05]")
        assert re.search(SPEC_ID_PATTERN, "[SPEC-12.34]")
        assert not re.search(SPEC_ID_PATTERN, "SPEC-01")  # Missing brackets

    def test_trace_marker_pattern_matches(self):
        """Should match valid trace markers. @trace SPEC-02.21"""
        import re

        from traceability import TRACE_PATTERN

        # Python style
        assert re.search(TRACE_PATTERN, "# @trace SPEC-01.05")
        # JavaScript/TypeScript style
        assert re.search(TRACE_PATTERN, "// @trace SPEC-01.05")
        # With sub-item
        assert re.search(TRACE_PATTERN, "# @trace SPEC-01.05.01")


class TestPlanValidation:
    """Test pre-execution plan validation. @trace SPEC-06"""

    def test_empty_plan_passes(self):
        """Empty plan should pass validation. @trace SPEC-06.10"""
        from lib.plan_validation import ValidationStatus, validate_plan

        result = validate_plan(specs=[], tasks=[])
        assert result.status == ValidationStatus.PASS

    def test_validates_spec_coverage(self):
        """Should check if specs have implementing tasks. @trace SPEC-06.10"""
        from lib.plan_validation import ValidationStatus, validate_plan

        specs = [{"id": "SPEC-01.01", "title": "User can log in"}]
        tasks = []  # No tasks implementing the spec

        result = validate_plan(specs=specs, tasks=tasks)
        # Should warn about orphan spec
        assert result.status == ValidationStatus.WARN
        assert len(result.warnings) > 0
        assert any("SPEC-01.01" in w for w in result.warnings)


class TestProviderDetection:
    """Test task tracker provider detection. @trace SPEC-01.11"""

    def test_none_provider_always_available(self):
        """None provider should always be available. @trace SPEC-01.80"""
        from lib.providers import TaskTracker, check_provider_available

        status = check_provider_available(TaskTracker.NONE, Path("."))
        assert status.available is True

    def test_builtin_provider_always_available(self):
        """Builtin provider should always be available. @trace SPEC-01.80"""
        from lib.providers import TaskTracker, check_provider_available

        status = check_provider_available(TaskTracker.BUILTIN, Path("."))
        assert status.available is True


class TestDegradationFramework:
    """Test graceful degradation. @trace SPEC-01.90"""

    def test_degradation_levels_exist(self):
        """Should have defined degradation levels."""
        from lib.degradation import DegradationLevel

        assert hasattr(DegradationLevel, "FULL")
        assert hasattr(DegradationLevel, "REDUCED")
        assert hasattr(DegradationLevel, "MANUAL")

    def test_get_current_level(self):
        """Should be able to get current degradation level."""
        from lib.degradation import DegradationLevel, get_current_level

        level = get_current_level()
        assert isinstance(level, DegradationLevel)


class TestBuiltinProvider:
    """Test Claude Code builtin task provider. @trace SPEC-01.80"""

    def test_generates_task_list_id(self):
        """Should generate consistent task list ID from path."""
        from lib.builtin_provider import get_task_list_id

        # Same path should give same ID
        id1 = get_task_list_id(Path("/some/project"))
        id2 = get_task_list_id(Path("/some/project"))
        assert id1 == id2

        # Different path should give different ID
        id3 = get_task_list_id(Path("/other/project"))
        assert id1 != id3
