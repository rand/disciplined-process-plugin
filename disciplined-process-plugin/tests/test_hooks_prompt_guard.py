"""
Tests for prompt_guard.py hook.

@trace SPEC-02.70
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestExtractSpecReferences:
    """Test spec reference extraction from text."""

    def test_extracts_bracketed_spec(self):
        """Should extract [SPEC-XX.YY] format."""
        from prompt_guard import extract_spec_references

        text = "Please implement [SPEC-01.05] as described"
        refs = extract_spec_references(text)
        assert refs == ["SPEC-01.05"]

    def test_extracts_unbracketed_spec(self):
        """Should extract SPEC-XX.YY format without brackets."""
        from prompt_guard import extract_spec_references

        text = "See SPEC-03.12 for details"
        refs = extract_spec_references(text)
        assert refs == ["SPEC-03.12"]

    def test_extracts_multiple_specs(self):
        """Should extract multiple specs from text."""
        from prompt_guard import extract_spec_references

        text = "Implement [SPEC-01.01] and [SPEC-01.02] together"
        refs = extract_spec_references(text)
        assert len(refs) == 2
        assert "SPEC-01.01" in refs
        assert "SPEC-01.02" in refs

    def test_returns_empty_for_no_specs(self):
        """Should return empty list when no specs found."""
        from prompt_guard import extract_spec_references

        text = "Just a regular prompt without any spec references"
        refs = extract_spec_references(text)
        assert refs == []

    def test_case_insensitive(self):
        """Should match case-insensitively."""
        from prompt_guard import extract_spec_references

        text = "Check spec-01.05 for requirements"
        refs = extract_spec_references(text)
        assert refs == ["SPEC-01.05"]


class TestValidateSpecExists:
    """Test spec existence validation."""

    def test_returns_true_when_no_spec_dir(self, tmp_path: Path):
        """Should return True when spec directory doesn't exist."""
        from prompt_guard import validate_spec_exists

        result = validate_spec_exists("SPEC-01.01", tmp_path)
        assert result is True

    def test_returns_true_when_spec_found(self, tmp_path: Path):
        """Should return True when spec exists in files."""
        from prompt_guard import validate_spec_exists

        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "01-feature.md"
        spec_file.write_text("[SPEC-01.01] This is a spec requirement")

        result = validate_spec_exists("SPEC-01.01", tmp_path)
        assert result is True

    def test_returns_false_when_spec_not_found(self, tmp_path: Path):
        """Should return False when spec not in any file."""
        from prompt_guard import validate_spec_exists

        spec_dir = tmp_path / "docs" / "spec"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "01-feature.md"
        spec_file.write_text("[SPEC-01.01] Only this spec exists")

        result = validate_spec_exists("SPEC-99.99", tmp_path)
        assert result is False


class TestDetectLanguageFromPrompt:
    """Test language detection from prompts."""

    def test_detects_python(self):
        """Should detect Python from prompt."""
        from prompt_guard import detect_language_from_prompt

        prompts = [
            "Write a Python script",
            "Create a .py file",
            "Run pytest tests",
            "Install with pip",
        ]
        for prompt in prompts:
            langs = detect_language_from_prompt(prompt)
            assert "python" in langs, f"Failed for: {prompt}"

    def test_detects_typescript(self):
        """Should detect TypeScript from prompt."""
        from prompt_guard import detect_language_from_prompt

        prompts = [
            "Create a TypeScript file",
            "Add a .tsx component",
            "Run npm install",
            "Use yarn to add packages",
        ]
        for prompt in prompts:
            langs = detect_language_from_prompt(prompt)
            assert "typescript" in langs, f"Failed for: {prompt}"

    def test_detects_rust(self):
        """Should detect Rust from prompt."""
        from prompt_guard import detect_language_from_prompt

        prompts = [
            "Write Rust code",
            "Create a .rs file",
            "Run cargo build",
            "Use rustc compiler",
        ]
        for prompt in prompts:
            langs = detect_language_from_prompt(prompt)
            assert "rust" in langs, f"Failed for: {prompt}"

    def test_detects_multiple_languages(self):
        """Should detect multiple languages."""
        from prompt_guard import detect_language_from_prompt

        prompt = "Create a Python backend and TypeScript frontend"
        langs = detect_language_from_prompt(prompt)
        assert "python" in langs
        assert "typescript" in langs

    def test_returns_empty_for_no_language(self):
        """Should return empty when no language detected."""
        from prompt_guard import detect_language_from_prompt

        prompt = "What time is it?"
        langs = detect_language_from_prompt(prompt)
        assert langs == []


class TestGetLanguageRules:
    """Test language-specific rules loading."""

    def test_returns_empty_when_no_rules_dir(self, tmp_path: Path):
        """Should return empty string when rules dir doesn't exist."""
        from prompt_guard import get_language_rules

        result = get_language_rules(["python"], tmp_path)
        assert result == ""

    def test_loads_rules_for_language(self, tmp_path: Path):
        """Should load rules for detected language."""
        from prompt_guard import get_language_rules

        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        python_rules = rules_dir / "python.md"
        python_rules.write_text("Use type hints for all functions")

        result = get_language_rules(["python"], tmp_path)
        assert "type hints" in result

    def test_loads_multiple_language_rules(self, tmp_path: Path):
        """Should load rules for multiple languages."""
        from prompt_guard import get_language_rules

        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "python.md").write_text("Python rules here")
        (rules_dir / "typescript.md").write_text("TypeScript rules here")

        result = get_language_rules(["python", "typescript"], tmp_path)
        assert "Python rules" in result
        assert "TypeScript rules" in result


class TestMain:
    """Test main entry point."""

    def test_returns_zero_on_empty_prompt(self):
        """Should return 0 when no prompt provided."""
        with patch("prompt_guard.get_project_dir") as mock_dir:
            mock_dir.return_value = Path(".")
            with patch("prompt_guard.get_config"):
                with patch("prompt_guard.get_prompt_from_stdin") as mock_stdin:
                    mock_stdin.return_value = ""

                    from prompt_guard import main

                    result = main()
                    assert result == 0

    def test_returns_zero_on_exception(self):
        """Should return 0 even on exception (graceful degradation)."""
        with patch("prompt_guard.get_project_dir") as mock_dir:
            mock_dir.side_effect = Exception("Test error")
            with patch("prompt_guard.feedback"):
                from prompt_guard import main

                result = main()
                assert result == 0
