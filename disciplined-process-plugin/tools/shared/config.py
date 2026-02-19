# @trace SPEC-08
"""Configuration loading for progress-report.

Reads .claude/progress-report.yaml with graceful defaults
when the file doesn't exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TriggerConfig:
    """Trigger condition configuration."""

    interval: str = "30m"
    tasks_completed: int = 3
    issue_completed: bool = True
    epic_milestone: bool = True
    on_failure: bool = True
    on_rework: bool = True
    on_blocker: bool = True
    hole_created: bool = True
    hole_resolved: bool = True
    all_work_hole_blocked: bool = True
    on_demand: bool = True


@dataclass
class BroadcastChannelConfig:
    """Configuration for a single broadcast channel."""

    enabled: bool = False
    on_triggers: list[str] = field(default_factory=lambda: ["all"])


@dataclass
class SlackConfig(BroadcastChannelConfig):
    webhook_url: str = ""
    channel: str = ""
    format: str = "summary"


@dataclass
class DiscordConfig(BroadcastChannelConfig):
    webhook_url: str = ""
    format: str = "summary"


@dataclass
class EmailConfig(BroadcastChannelConfig):
    to: list[str] = field(default_factory=list)


@dataclass
class WebhookConfig(BroadcastChannelConfig):
    url: str = ""
    method: str = "POST"
    payload: str = "json"


@dataclass
class BroadcastConfig:
    """All broadcast channel configurations."""

    file: bool = True
    agent_brief: str = "docs/progress/latest.md"
    email: EmailConfig = field(default_factory=EmailConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)


@dataclass
class ProgressReportConfig:
    """Complete progress-report configuration."""

    triggers: TriggerConfig = field(default_factory=TriggerConfig)
    broadcast: BroadcastConfig = field(default_factory=BroadcastConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> ProgressReportConfig:
        """Load config from YAML file with graceful defaults.

        Args:
            config_path: Path to progress-report.yaml.
                Defaults to .claude/progress-report.yaml.

        Returns:
            ProgressReportConfig with values from file or defaults.
        """
        if config_path is None:
            config_path = Path(".claude/progress-report.yaml")

        if not config_path.exists():
            return cls()

        try:
            raw = yaml.safe_load(config_path.read_text())
        except (yaml.YAMLError, OSError):
            return cls()

        if not isinstance(raw, dict):
            return cls()

        return cls._from_dict(raw)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ProgressReportConfig:
        """Build config from a parsed YAML dict."""
        config = cls()

        # Triggers
        triggers_raw = data.get("triggers", {})
        if isinstance(triggers_raw, dict):
            for key in (
                "interval",
                "tasks_completed",
                "issue_completed",
                "epic_milestone",
                "on_failure",
                "on_rework",
                "on_blocker",
                "hole_created",
                "hole_resolved",
                "all_work_hole_blocked",
                "on_demand",
            ):
                if key in triggers_raw:
                    setattr(config.triggers, key, triggers_raw[key])

        # Broadcast
        bcast_raw = data.get("broadcast", {})
        if isinstance(bcast_raw, dict):
            if "file" in bcast_raw:
                config.broadcast.file = bcast_raw["file"]
            if "agent_brief" in bcast_raw:
                config.broadcast.agent_brief = bcast_raw["agent_brief"]

            # Slack
            slack_raw = bcast_raw.get("slack", {})
            if isinstance(slack_raw, dict):
                config.broadcast.slack = SlackConfig(
                    enabled=slack_raw.get("enabled", False),
                    webhook_url=slack_raw.get("webhook_url", ""),
                    channel=slack_raw.get("channel", ""),
                    on_triggers=slack_raw.get("on_triggers", ["all"]),
                    format=slack_raw.get("format", "summary"),
                )

            # Discord
            discord_raw = bcast_raw.get("discord", {})
            if isinstance(discord_raw, dict):
                config.broadcast.discord = DiscordConfig(
                    enabled=discord_raw.get("enabled", False),
                    webhook_url=discord_raw.get("webhook_url", ""),
                    on_triggers=discord_raw.get("on_triggers", ["all"]),
                    format=discord_raw.get("format", "summary"),
                )

            # Email
            email_raw = bcast_raw.get("email", {})
            if isinstance(email_raw, dict):
                config.broadcast.email = EmailConfig(
                    enabled=email_raw.get("enabled", False),
                    to=email_raw.get("to", []),
                    on_triggers=email_raw.get("on_triggers", ["all"]),
                )

            # Webhook
            webhook_raw = bcast_raw.get("webhook", {})
            if isinstance(webhook_raw, dict):
                config.broadcast.webhook = WebhookConfig(
                    enabled=webhook_raw.get("enabled", False),
                    url=webhook_raw.get("url", ""),
                    method=webhook_raw.get("method", "POST"),
                    payload=webhook_raw.get("payload", "json"),
                    on_triggers=webhook_raw.get("on_triggers", ["all"]),
                )

        return config


def parse_interval(interval: str) -> int:
    """Parse an interval string (e.g., '30m', '1h') to seconds.

    Args:
        interval: String like '30m', '1h', '90s'.

    Returns:
        Number of seconds.
    """
    interval = interval.strip().lower()
    if interval.endswith("m"):
        return int(interval[:-1]) * 60
    elif interval.endswith("h"):
        return int(interval[:-1]) * 3600
    elif interval.endswith("s"):
        return int(interval[:-1])
    else:
        # Assume minutes if no suffix
        return int(interval) * 60
