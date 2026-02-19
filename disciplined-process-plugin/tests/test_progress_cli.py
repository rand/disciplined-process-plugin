# @trace SPEC-08
"""Tests for progress_report/cli.py — CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.progress_report.cli import build_parser, main
from tools.progress_report.extractor import GitState, ProjectState


def _empty_state() -> ProjectState:
    """Create a minimal empty ProjectState for testing."""
    return ProjectState(
        tasks=[],
        git=GitState(current_branch="main", recent_commits=[], files_changed=[]),
    )


class TestBuildParser:
    """Tests for the argument parser."""

    def test_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        assert args.trigger is None
        assert args.no_broadcast is False
        assert args.watch is False
        assert args.config is None
        assert args.output_dir is None
        assert args.epic_title == "Project"
        assert args.project_root == "."
        assert args.format == "both"
        assert args.poll_interval is None
        assert args.slack_webhook is None
        assert args.discord_webhook is None
        assert args.email_to is None

    def test_trigger_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--trigger", "Phase 1 complete"])
        assert args.trigger == "Phase 1 complete"

    def test_watch_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--watch"])
        assert args.watch is True

    def test_no_broadcast_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--no-broadcast"])
        assert args.no_broadcast is True

    def test_format_choices(self) -> None:
        parser = build_parser()
        for fmt in ("markdown", "json", "both"):
            args = parser.parse_args(["--format", fmt])
            assert args.format == fmt

    def test_poll_interval(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--poll-interval", "30"])
        assert args.poll_interval == 30

    def test_broadcast_overrides(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--slack-webhook", "https://hooks.slack.com/test",
            "--discord-webhook", "https://discord.com/api/test",
            "--email-to", "a@b.com", "c@d.com",
        ])
        assert args.slack_webhook == "https://hooks.slack.com/test"
        assert args.discord_webhook == "https://discord.com/api/test"
        assert args.email_to == ["a@b.com", "c@d.com"]

    def test_config_path(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--config", "/path/to/config.yaml"])
        assert args.config == "/path/to/config.yaml"


class TestMain:
    """Tests for the main entry point."""

    def test_one_shot_mode(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "progress"
        mock_state = _empty_state()

        with patch(
            "tools.progress_report.extractor.extract_state", return_value=mock_state
        ):
            exit_code = main([
                "--output-dir", str(output_dir),
                "--no-broadcast",
                "--project-root", str(tmp_path),
            ])

        assert exit_code == 0
        # Check that report files were created
        assert output_dir.exists()

    def test_custom_trigger(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "progress"
        mock_state = _empty_state()

        with patch(
            "tools.progress_report.extractor.extract_state", return_value=mock_state
        ):
            exit_code = main([
                "--trigger", "Phase 1 complete",
                "--output-dir", str(output_dir),
                "--no-broadcast",
                "--project-root", str(tmp_path),
            ])

        assert exit_code == 0

    def test_watch_mode_starts_daemon(self, tmp_path: Path) -> None:
        mock_daemon = MagicMock()

        with patch(
            "tools.progress_report.watch.WatchDaemon",
            return_value=mock_daemon,
        ):
            exit_code = main([
                "--watch",
                "--output-dir", str(tmp_path),
                "--project-root", str(tmp_path),
            ])

        assert exit_code == 0
        mock_daemon.start.assert_called_once()

    def test_broadcast_overrides_applied(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "progress"
        mock_state = _empty_state()

        with patch(
            "tools.progress_report.extractor.extract_state", return_value=mock_state
        ), patch(
            "tools.progress_report.broadcast.broadcast_report", return_value=["slack"]
        ) as mock_broadcast:
            exit_code = main([
                "--slack-webhook", "https://hooks.slack.com/test",
                "--output-dir", str(output_dir),
                "--project-root", str(tmp_path),
            ])

        assert exit_code == 0

    def test_format_json_only(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        output_dir = tmp_path / "progress"
        mock_state = _empty_state()

        with patch(
            "tools.progress_report.extractor.extract_state", return_value=mock_state
        ):
            exit_code = main([
                "--format", "json",
                "--output-dir", str(output_dir),
                "--no-broadcast",
                "--project-root", str(tmp_path),
            ])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "JSON written to" in captured.out
