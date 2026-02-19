# @trace SPEC-07
"""Tests for spec_decompose/invoke.py — decomposer invocation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.spec_decompose.invoke import (
    DecomposeParams,
    _build_user_message,
    _read_agent_prompt,
    build_subagent_prompt,
    invoke_via_api,
)


class TestDecomposeParams:
    """Tests for DecomposeParams dataclass."""

    def test_defaults(self) -> None:
        params = DecomposeParams(spec_text="test", spec_files=["a.md"])
        assert params.context_window == 200_000
        assert params.holes_strategy == "graph"
        assert params.model == "opus"
        assert params.existing_state is None
        assert params.constitution is None
        assert params.auto_resolve is False
        assert params.existing_code_path is None

    def test_is_diff_false(self) -> None:
        params = DecomposeParams(spec_text="t", spec_files=["a.md"])
        assert params.is_diff is False

    def test_is_diff_true(self) -> None:
        params = DecomposeParams(
            spec_text="t",
            spec_files=["a.md"],
            existing_state={"tasks": []},
        )
        assert params.is_diff is True


class TestBuildUserMessage:
    """Tests for _build_user_message."""

    def test_basic_message(self) -> None:
        params = DecomposeParams(
            spec_text="# My Spec\nRequirement one.",
            spec_files=["docs/spec.md"],
        )
        msg = _build_user_message(params)
        assert "200,000 tokens" in msg
        assert "docs/spec.md" in msg
        assert "# My Spec" in msg
        assert "graph" in msg

    def test_includes_constitution(self) -> None:
        params = DecomposeParams(
            spec_text="spec",
            spec_files=["s.md"],
            constitution="Be concise. Be correct.",
        )
        msg = _build_user_message(params)
        assert "Constitution / Principles" in msg
        assert "Be concise. Be correct." in msg

    def test_includes_existing_state_for_diff(self) -> None:
        params = DecomposeParams(
            spec_text="spec",
            spec_files=["s.md"],
            existing_state={"tasks": [{"id": "t1", "title": "Task 1"}]},
        )
        msg = _build_user_message(params)
        assert "Existing State" in msg
        assert "diff" in msg.lower()
        assert "t1" in msg

    def test_ends_with_output_instructions(self) -> None:
        params = DecomposeParams(spec_text="spec", spec_files=["s.md"])
        msg = _build_user_message(params)
        assert "valid JSON" in msg

    def test_includes_existing_code_path(self, tmp_path: Path) -> None:
        # Create a small Python file
        code_dir = tmp_path / "src"
        code_dir.mkdir()
        (code_dir / "main.py").write_text("print('hello')")

        params = DecomposeParams(
            spec_text="spec",
            spec_files=["s.md"],
            existing_code_path=str(code_dir),
        )
        msg = _build_user_message(params)
        assert "Existing Codebase" in msg
        assert "main.py" in msg


class TestReadAgentPrompt:
    """Tests for _read_agent_prompt."""

    def test_reads_from_plugin_root(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "decomposer.md").write_text(
            "---\nname: decomposer\n---\n# Decomposer Instructions\nDo this."
        )
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(tmp_path)}):
            prompt = _read_agent_prompt()
        assert "Decomposer Instructions" in prompt
        assert "---" not in prompt  # Frontmatter stripped

    def test_reads_from_relative_path(self) -> None:
        # This should find the actual agents/decomposer.md
        prompt = _read_agent_prompt()
        # It may or may not find it depending on CWD, but shouldn't crash
        assert isinstance(prompt, str)

    def test_returns_empty_when_not_found(self, tmp_path: Path) -> None:
        # Point CLAUDE_PLUGIN_ROOT to an empty dir (no agents/)
        empty_dir = tmp_path / "empty_plugin"
        empty_dir.mkdir()
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(empty_dir)}):
            # Also patch __file__ path so fallback doesn't find it
            with patch(
                "tools.spec_decompose.invoke.__file__",
                str(tmp_path / "fake" / "invoke.py"),
            ):
                prompt = _read_agent_prompt()
        assert prompt == ""

    def test_handles_no_frontmatter(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "decomposer.md").write_text("Just plain content.")
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(tmp_path)}):
            prompt = _read_agent_prompt()
        assert prompt == "Just plain content."


class TestBuildSubagentPrompt:
    """Tests for build_subagent_prompt."""

    def test_returns_user_message(self) -> None:
        params = DecomposeParams(spec_text="my spec", spec_files=["a.md"])
        prompt = build_subagent_prompt(params)
        assert "my spec" in prompt
        assert "## Decomposition Request" in prompt


class TestInvokeViaApi:
    """Tests for invoke_via_api (mocked)."""

    def test_raises_without_anthropic(self) -> None:
        params = DecomposeParams(spec_text="spec", spec_files=["a.md"])
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic"):
                invoke_via_api(params)

    def test_successful_invocation(self) -> None:
        params = DecomposeParams(spec_text="spec", spec_files=["a.md"])
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"epic": {"title": "Test"}, "tasks": [], "holes": []}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = invoke_via_api(params)

        assert result == {"epic": {"title": "Test"}, "tasks": [], "holes": []}
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-6"
        assert call_kwargs["max_tokens"] == 16384

    def test_model_mapping(self) -> None:
        params = DecomposeParams(
            spec_text="spec", spec_files=["a.md"], model="sonnet"
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"tasks": []}')]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            invoke_via_api(params)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    def test_custom_model_passthrough(self) -> None:
        params = DecomposeParams(
            spec_text="spec",
            spec_files=["a.md"],
            model="claude-3-haiku-20240307",
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"tasks": []}')]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            invoke_via_api(params)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-haiku-20240307"
