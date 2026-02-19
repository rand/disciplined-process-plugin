# @trace SPEC-08
"""Tests for progress-report configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.shared.config import (
    BroadcastConfig,
    ProgressReportConfig,
    TriggerConfig,
    parse_interval,
)


class TestProgressReportConfig:
    def test_defaults(self):
        config = ProgressReportConfig()
        assert config.triggers.interval == "30m"
        assert config.triggers.tasks_completed == 3
        assert config.triggers.on_demand is True
        assert config.broadcast.file is True
        assert config.broadcast.slack.enabled is False

    def test_load_missing_file(self, tmp_path: Path):
        config = ProgressReportConfig.load(tmp_path / "nonexistent.yaml")
        assert config.triggers.interval == "30m"  # Uses defaults

    def test_load_empty_file(self, tmp_path: Path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")
        config = ProgressReportConfig.load(config_path)
        assert config.triggers.interval == "30m"

    def test_load_full_config(self, tmp_path: Path):
        config_data = {
            "triggers": {
                "interval": "15m",
                "tasks_completed": 5,
                "issue_completed": False,
                "hole_created": True,
            },
            "broadcast": {
                "file": True,
                "agent_brief": "custom/path.md",
                "slack": {
                    "enabled": True,
                    "webhook_url": "https://hooks.slack.com/test",
                    "channel": "#dev",
                    "on_triggers": ["issue_completed"],
                    "format": "full",
                },
                "discord": {
                    "enabled": True,
                    "webhook_url": "https://discord.com/api/test",
                },
                "email": {
                    "enabled": True,
                    "to": ["dev@example.com"],
                },
                "webhook": {
                    "enabled": True,
                    "url": "https://example.com/hook",
                    "method": "POST",
                    "payload": "json",
                },
            },
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config_data))

        config = ProgressReportConfig.load(config_path)
        assert config.triggers.interval == "15m"
        assert config.triggers.tasks_completed == 5
        assert config.triggers.issue_completed is False
        assert config.broadcast.agent_brief == "custom/path.md"
        assert config.broadcast.slack.enabled is True
        assert config.broadcast.slack.webhook_url == "https://hooks.slack.com/test"
        assert config.broadcast.slack.channel == "#dev"
        assert config.broadcast.slack.format == "full"
        assert config.broadcast.discord.enabled is True
        assert config.broadcast.email.enabled is True
        assert config.broadcast.email.to == ["dev@example.com"]
        assert config.broadcast.webhook.enabled is True
        assert config.broadcast.webhook.url == "https://example.com/hook"

    def test_load_partial_config(self, tmp_path: Path):
        config_data = {
            "triggers": {"interval": "1h"},
        }
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config_data))

        config = ProgressReportConfig.load(config_path)
        assert config.triggers.interval == "1h"
        assert config.triggers.tasks_completed == 3  # Default preserved
        assert config.broadcast.file is True  # Default preserved

    def test_load_invalid_yaml(self, tmp_path: Path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("not: valid: yaml: {{{}}")
        config = ProgressReportConfig.load(config_path)
        # Falls back to defaults
        assert config.triggers.interval == "30m"

    def test_load_non_dict_yaml(self, tmp_path: Path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("just a string")
        config = ProgressReportConfig.load(config_path)
        assert config.triggers.interval == "30m"


class TestParseInterval:
    def test_minutes(self):
        assert parse_interval("30m") == 1800

    def test_hours(self):
        assert parse_interval("1h") == 3600

    def test_seconds(self):
        assert parse_interval("90s") == 90

    def test_bare_number(self):
        assert parse_interval("15") == 900  # Assumes minutes

    def test_whitespace(self):
        assert parse_interval("  30m  ") == 1800

    def test_case_insensitive(self):
        assert parse_interval("30M") == 1800
