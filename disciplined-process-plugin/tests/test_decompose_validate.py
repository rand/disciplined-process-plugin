"""Tests for JSON parsing and schema validation.

@trace SPEC-07
"""

from __future__ import annotations

import json

import pytest

from tools.spec_decompose.validate import (
    ValidationResult,
    parse_decomposition_output,
    save_raw_output,
)


# Sample valid decomposition output
VALID_OUTPUT = {
    "spec_source": ["docs/spec/auth.md"],
    "epic": {"title": "Authentication System", "description": "Auth module"},
    "tasks": [
        {
            "number": 1,
            "title": "Configure OAuth",
            "description": "Set up OAuth provider",
            "depends_on_tasks": [],
        },
        {
            "number": 2,
            "title": "Token exchange",
            "description": "Implement token exchange",
            "depends_on_tasks": [1],
        },
    ],
    "holes": [
        {
            "number": "H001",
            "title": "Session revocation behavior",
            "hole_type": "clarification",
            "blocks_tasks": [2],
        }
    ],
}


class TestParseDecompositionOutput:
    """Tests for the 5-layer parsing pipeline."""

    def test_valid_json(self) -> None:
        raw = json.dumps(VALID_OUTPUT)
        result = parse_decomposition_output(raw)
        assert result.is_valid
        assert result.data is not None
        assert len(result.data["tasks"]) == 2

    def test_json_with_markdown_fences(self) -> None:
        raw = f"```json\n{json.dumps(VALID_OUTPUT)}\n```"
        result = parse_decomposition_output(raw)
        assert result.is_valid

    def test_json_with_bare_fences(self) -> None:
        raw = f"```\n{json.dumps(VALID_OUTPUT)}\n```"
        result = parse_decomposition_output(raw)
        assert result.is_valid

    def test_json_with_trailing_commas(self) -> None:
        raw = json.dumps(VALID_OUTPUT)
        # Add trailing commas
        raw = raw.replace("}", ",}")
        raw = raw.replace("],", "],")
        result = parse_decomposition_output(raw)
        assert result.is_valid

    def test_empty_input(self) -> None:
        result = parse_decomposition_output("")
        assert not result.is_valid
        assert "Empty output" in result.errors[0]

    def test_non_json(self) -> None:
        result = parse_decomposition_output("This is not JSON at all")
        assert not result.is_valid
        assert "Failed to parse" in result.errors[0]

    def test_json_array_not_object(self) -> None:
        result = parse_decomposition_output("[1, 2, 3]")
        assert not result.is_valid
        assert "not a JSON object" in result.errors[0]

    def test_missing_required_keys(self) -> None:
        raw = json.dumps({"epic": {"title": "Test"}})
        result = parse_decomposition_output(raw)
        assert not result.is_valid
        assert any("Missing required" in e for e in result.errors)

    def test_duplicate_task_numbers(self) -> None:
        bad = {**VALID_OUTPUT, "tasks": [
            {"number": 1, "title": "A", "description": "A", "depends_on_tasks": []},
            {"number": 1, "title": "B", "description": "B", "depends_on_tasks": []},
        ]}
        result = parse_decomposition_output(json.dumps(bad))
        assert not result.is_valid
        assert any("Duplicate task" in e for e in result.errors)

    def test_invalid_hole_type(self) -> None:
        bad = {**VALID_OUTPUT, "holes": [
            {"number": "H001", "title": "Bad", "hole_type": "invalid_type",
             "blocks_tasks": []},
        ]}
        result = parse_decomposition_output(json.dumps(bad))
        assert not result.is_valid
        assert any("invalid type" in e for e in result.errors)

    def test_warnings_for_missing_optional(self) -> None:
        minimal = {
            "spec_source": ["test.md"],
            "epic": {"title": "Test"},
            "tasks": [
                {"number": 1, "title": "T", "description": "D",
                 "depends_on_tasks": []},
            ],
        }
        result = parse_decomposition_output(json.dumps(minimal))
        assert result.is_valid
        assert len(result.warnings) > 0

    def test_raw_output_preserved(self) -> None:
        raw = "not json"
        result = parse_decomposition_output(raw)
        assert result.raw_output == raw


class TestSaveRawOutput:
    """Tests for raw output saving."""

    def test_saves_to_file(self, tmp_path) -> None:
        path = tmp_path / "raw.txt"
        result = save_raw_output("test output", path)
        assert result.exists()
        content = result.read_text()
        assert "test output" in content

    def test_includes_instructions(self, tmp_path) -> None:
        path = tmp_path / "raw.txt"
        save_raw_output("test", path)
        content = path.read_text()
        assert "Parsing Failed" in content
        assert "Common issues" in content
