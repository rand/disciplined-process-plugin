"""
Tests for init_wizard.py initialization script.

@trace SPEC-01.10
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestWizardConfig:
    """Test WizardConfig dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        from init_wizard import WizardConfig
        from lib.config import TaskTracker

        config = WizardConfig()
        assert config.project_name == ""
        assert config.languages == []
        assert config.task_tracker == TaskTracker.BEADS
        assert config.enforcement == "guided"
        assert config.adversarial_enabled is True

    def test_custom_values(self):
        """Should accept custom values."""
        from init_wizard import WizardConfig
        from lib.config import TaskTracker

        config = WizardConfig(
            project_name="my-project",
            languages=["python", "rust"],
            task_tracker=TaskTracker.BUILTIN,
            enforcement="strict",
        )
        assert config.project_name == "my-project"
        assert config.languages == ["python", "rust"]
        assert config.task_tracker == TaskTracker.BUILTIN
        assert config.enforcement == "strict"


class TestDetectProjectName:
    """Test project name detection."""

    def test_from_package_json(self, tmp_path: Path):
        """Should detect name from package.json."""
        from init_wizard import detect_project_name

        package = tmp_path / "package.json"
        package.write_text('{"name": "my-node-project"}')

        name = detect_project_name(tmp_path)
        assert name == "my-node-project"

    def test_from_pyproject_toml(self, tmp_path: Path):
        """Should detect name from pyproject.toml."""
        from init_wizard import detect_project_name

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "my-python-project"\nversion = "1.0"')

        name = detect_project_name(tmp_path)
        assert name == "my-python-project"

    def test_from_cargo_toml(self, tmp_path: Path):
        """Should detect name from Cargo.toml."""
        from init_wizard import detect_project_name

        cargo = tmp_path / "Cargo.toml"
        cargo.write_text('[package]\nname = "my-rust-project"')

        name = detect_project_name(tmp_path)
        assert name == "my-rust-project"

    def test_fallback_to_directory_name(self, tmp_path: Path):
        """Should fallback to directory name when no package files."""
        from init_wizard import detect_project_name

        name = detect_project_name(tmp_path)
        assert name == tmp_path.name


class TestDetectLanguages:
    """Test language detection from files."""

    def test_detects_python(self, tmp_path: Path):
        """Should detect Python from .py files."""
        from init_wizard import detect_languages

        (tmp_path / "main.py").write_text("print('hello')")
        langs = detect_languages(tmp_path)
        assert "python" in langs

    def test_detects_typescript(self, tmp_path: Path):
        """Should detect TypeScript from .ts files."""
        from init_wizard import detect_languages

        (tmp_path / "app.ts").write_text("const x = 1;")
        langs = detect_languages(tmp_path)
        assert "typescript" in langs

    def test_detects_rust(self, tmp_path: Path):
        """Should detect Rust from .rs files."""
        from init_wizard import detect_languages

        (tmp_path / "lib.rs").write_text("fn main() {}")
        langs = detect_languages(tmp_path)
        assert "rust" in langs

    def test_detects_multiple_languages(self, tmp_path: Path):
        """Should detect multiple languages."""
        from init_wizard import detect_languages

        (tmp_path / "app.py").write_text("")
        (tmp_path / "lib.ts").write_text("")
        (tmp_path / "main.go").write_text("")

        langs = detect_languages(tmp_path)
        assert len(langs) >= 2

    def test_limits_to_three_languages(self, tmp_path: Path):
        """Should limit results to 3 languages."""
        from init_wizard import detect_languages

        # Create files for many languages
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.ts").write_text("")
        (tmp_path / "c.go").write_text("")
        (tmp_path / "d.rs").write_text("")
        (tmp_path / "e.java").write_text("")

        langs = detect_languages(tmp_path)
        assert len(langs) <= 3

    def test_empty_for_no_code_files(self, tmp_path: Path):
        """Should return empty for directory with no code."""
        from init_wizard import detect_languages

        (tmp_path / "readme.md").write_text("")
        langs = detect_languages(tmp_path)
        assert langs == []


class TestCheckCliAvailable:
    """Test CLI availability checking."""

    def test_detects_available_command(self):
        """Should detect available system commands."""
        from init_wizard import check_cli_available

        # ls should be available on all Unix systems
        assert check_cli_available("ls") is True

    def test_detects_unavailable_command(self):
        """Should return False for non-existent commands."""
        from init_wizard import check_cli_available

        assert check_cli_available("definitely-not-a-real-command-xyz") is False


class TestCheckTrackerAvailability:
    """Test tracker availability detection."""

    def test_builtin_always_available(self, tmp_path: Path):
        """Builtin tracker should always be available."""
        from init_wizard import check_tracker_availability

        trackers = check_tracker_availability(tmp_path)
        assert trackers["builtin"]["available"] is True
        assert trackers["builtin"]["initialized"] is True

    def test_none_always_available(self, tmp_path: Path):
        """None tracker should always be available."""
        from init_wizard import check_tracker_availability

        trackers = check_tracker_availability(tmp_path)
        assert trackers["none"]["available"] is True

    def test_markdown_always_available(self, tmp_path: Path):
        """Markdown tracker should always be available."""
        from init_wizard import check_tracker_availability

        trackers = check_tracker_availability(tmp_path)
        assert trackers["markdown"]["available"] is True

    def test_beads_initialized_detection(self, tmp_path: Path):
        """Should detect initialized beads directory."""
        from init_wizard import check_tracker_availability

        (tmp_path / ".beads").mkdir()
        trackers = check_tracker_availability(tmp_path)
        assert trackers["beads"]["initialized"] is True


class TestCreateConfigFile:
    """Test config file creation."""

    def test_creates_config_file(self, tmp_path: Path):
        """Should create dp-config.yaml."""
        from init_wizard import WizardConfig, create_config_file
        from lib.config import TaskTracker

        config = WizardConfig(
            project_name="test-project",
            languages=["python"],
            task_tracker=TaskTracker.BEADS,
        )

        create_config_file(config, tmp_path)

        config_file = tmp_path / ".claude" / "dp-config.yaml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "test-project" in content
        assert "beads" in content
        assert "python" in content

    def test_creates_claude_directory(self, tmp_path: Path):
        """Should create .claude directory if missing."""
        from init_wizard import WizardConfig, create_config_file

        config = WizardConfig(project_name="test")
        create_config_file(config, tmp_path)

        assert (tmp_path / ".claude").is_dir()


class TestCreateSettingsFile:
    """Test settings.json creation."""

    def test_creates_settings_with_hooks(self, tmp_path: Path):
        """Should create settings.json with hooks configured."""
        from init_wizard import WizardConfig, create_settings_file

        config = WizardConfig()
        (tmp_path / ".claude").mkdir()
        create_settings_file(config, tmp_path)

        settings_file = tmp_path / ".claude" / "settings.json"
        assert settings_file.exists()

        settings = json.loads(settings_file.read_text())
        assert "hooks" in settings
        assert "SessionStart" in settings["hooks"]
        assert "UserPromptSubmit" in settings["hooks"]

    def test_preserves_existing_settings(self, tmp_path: Path):
        """Should preserve existing settings when adding hooks."""
        from init_wizard import WizardConfig, create_settings_file

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text('{"existing": "value"}')

        config = WizardConfig()
        create_settings_file(config, tmp_path)

        settings = json.loads(settings_file.read_text())
        # New hooks should be added
        assert "hooks" in settings


class TestCreateLanguageRules:
    """Test language rules creation."""

    def test_creates_python_rules(self, tmp_path: Path):
        """Should create Python rules file."""
        from init_wizard import create_language_rules

        created = create_language_rules(["python"], tmp_path)

        assert len(created) == 1
        rules_file = tmp_path / ".claude" / "rules" / "python.md"
        assert rules_file.exists()
        content = rules_file.read_text()
        assert "type hints" in content

    def test_creates_multiple_rules(self, tmp_path: Path):
        """Should create rules for multiple languages."""
        from init_wizard import create_language_rules

        created = create_language_rules(["python", "typescript", "rust"], tmp_path)

        assert len(created) == 3
        assert (tmp_path / ".claude" / "rules" / "python.md").exists()
        assert (tmp_path / ".claude" / "rules" / "typescript.md").exists()
        assert (tmp_path / ".claude" / "rules" / "rust.md").exists()

    def test_ignores_unknown_languages(self, tmp_path: Path):
        """Should skip languages without defined rules."""
        from init_wizard import create_language_rules

        created = create_language_rules(["python", "unknown-lang"], tmp_path)

        assert len(created) == 1
        assert ".claude/rules/python.md" in created


class TestCreateSpecTemplate:
    """Test spec template creation."""

    def test_creates_overview_spec(self, tmp_path: Path):
        """Should create 00-overview.md spec file."""
        from init_wizard import create_spec_template

        create_spec_template(tmp_path)

        spec_file = tmp_path / "docs" / "spec" / "00-overview.md"
        assert spec_file.exists()
        content = spec_file.read_text()
        assert "[SPEC-00]" in content
        assert "[SPEC-00.01]" in content


class TestCreateAdrTemplate:
    """Test ADR template creation."""

    def test_creates_adr_template(self, tmp_path: Path):
        """Should create ADR template file."""
        from init_wizard import create_adr_template

        create_adr_template(tmp_path)

        template = tmp_path / "docs" / "adr" / "template.md"
        assert template.exists()
        content = template.read_text()
        assert "Status" in content
        assert "Context" in content
        assert "Decision" in content

    def test_creates_initial_adr(self, tmp_path: Path):
        """Should create initial ADR for adopting disciplined process."""
        from init_wizard import create_adr_template

        create_adr_template(tmp_path)

        initial = tmp_path / "docs" / "adr" / "0001-adopt-disciplined-process.md"
        assert initial.exists()
        content = initial.read_text()
        assert "Accepted" in content
        assert "disciplined-process" in content


class TestExecuteSetup:
    """Test full setup execution."""

    def test_creates_all_expected_files(self, tmp_path: Path):
        """Should create all setup files."""
        from init_wizard import WizardConfig, execute_setup
        from lib.config import TaskTracker

        config = WizardConfig(
            project_name="test-project",
            languages=["python"],
            task_tracker=TaskTracker.BUILTIN,  # Avoid external dependencies
        )

        results = execute_setup(config, tmp_path)

        assert results["success"] is True
        assert ".claude/dp-config.yaml" in results["created"]
        assert ".claude/settings.json" in results["created"]
        assert "docs/spec/00-overview.md" in results["created"]

    def test_handles_errors_gracefully(self, tmp_path: Path):
        """Should handle errors and report them."""
        from init_wizard import WizardConfig, execute_setup

        # Make directory read-only to cause errors
        config = WizardConfig()

        with patch("init_wizard.create_config_file") as mock:
            mock.side_effect = PermissionError("Cannot write")
            results = execute_setup(config, tmp_path)

            assert results["success"] is False
            assert len(results["errors"]) > 0


class TestRunWizard:
    """Test wizard runner."""

    def test_detects_project_info(self, tmp_path: Path):
        """Should detect project name and languages."""
        from init_wizard import run_wizard

        (tmp_path / "package.json").write_text('{"name": "detected-name"}')
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.ts").write_text("")

        config = run_wizard(tmp_path)

        assert config.project_name == "detected-name"
        assert "typescript" in config.languages

    def test_prefers_beads_when_available(self, tmp_path: Path):
        """Should prefer Beads tracker when CLI is available."""
        from init_wizard import run_wizard
        from lib.config import TaskTracker

        with patch("init_wizard.check_cli_available") as mock:
            mock.return_value = True
            config = run_wizard(tmp_path)

            assert config.task_tracker == TaskTracker.BEADS

    def test_falls_back_to_builtin(self, tmp_path: Path):
        """Should fall back to Builtin when no CLIs available."""
        from init_wizard import run_wizard
        from lib.config import TaskTracker

        with patch("init_wizard.check_cli_available") as mock:
            mock.return_value = False
            config = run_wizard(tmp_path)

            assert config.task_tracker == TaskTracker.BUILTIN
