# @trace SPEC-08
"""Broadcast channels for progress reports.

Each channel is a simple function that takes report content and delivers it.
No heavy dependencies — uses subprocess for curl-based delivery.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tools.shared.config import (
    BroadcastConfig,
    DiscordConfig,
    EmailConfig,
    SlackConfig,
    WebhookConfig,
)


def broadcast_report(
    config: BroadcastConfig,
    markdown_content: str,
    json_data: dict[str, Any],
    trigger: str,
    output_dir: Path | None = None,
) -> list[str]:
    """Broadcast a report to all configured channels.

    Args:
        config: Broadcast configuration.
        markdown_content: Full report markdown.
        json_data: Machine-readable report data.
        trigger: Trigger that caused this report.
        output_dir: Where file output goes.

    Returns:
        List of channels that were successfully delivered to.
    """
    delivered: list[str] = []

    if config.slack.enabled and _trigger_matches(config.slack.on_triggers, trigger):
        if send_slack(config.slack, markdown_content, json_data):
            delivered.append("slack")

    if config.discord.enabled and _trigger_matches(config.discord.on_triggers, trigger):
        if send_discord(config.discord, markdown_content, json_data):
            delivered.append("discord")

    if config.email.enabled and _trigger_matches(config.email.on_triggers, trigger):
        if send_email(config.email, markdown_content):
            delivered.append("email")

    if config.webhook.enabled and _trigger_matches(config.webhook.on_triggers, trigger):
        if send_webhook(config.webhook, markdown_content, json_data):
            delivered.append("webhook")

    return delivered


def _trigger_matches(on_triggers: list[str], trigger: str) -> bool:
    """Check if a trigger matches the channel's on_triggers filter."""
    if "all" in on_triggers:
        return True
    return trigger in on_triggers


def format_slack_summary(json_data: dict[str, Any]) -> str:
    """Format a Slack-friendly summary from report JSON."""
    tasks = json_data.get("tasks", {})
    holes = json_data.get("holes", {})
    trigger = json_data.get("trigger", "on_demand")

    total = tasks.get("total", 0)
    completed = tasks.get("completed", 0)
    ready = tasks.get("ready", 0)
    pct = int(json_data.get("epic_progress", 0) * 100)

    lines = [
        f"*Progress Report*",
        f"*Trigger:* {trigger}",
        "",
        f"✅ {completed}/{total} tasks complete ({pct}%)",
    ]

    if ready > 0:
        lines.append(f"🆕 {ready} tasks ready for execution")

    discovered = json_data.get("discovered_issues", [])
    if discovered:
        lines.append(f"⚠️ {len(discovered)} new issue(s) discovered")

    open_holes = json_data.get("open_holes", [])
    if open_holes:
        human_holes = sum(
            1 for h in open_holes if h.get("urgency") == "high"
        )
        lines.append(
            f"🕳️ {len(open_holes)} open hole(s)"
            + (f" ({human_holes} need human decision)" if human_holes else "")
        )

    ready_ids = json_data.get("ready_task_ids", [])
    if ready_ids:
        lines.append(f"*Ready:* {', '.join(ready_ids[:5])}")

    return "\n".join(lines)


def send_slack(
    config: SlackConfig,
    markdown_content: str,
    json_data: dict[str, Any],
) -> bool:
    """Send to Slack via webhook."""
    if not config.webhook_url:
        return False

    if config.format == "summary":
        text = format_slack_summary(json_data)
    else:
        text = markdown_content[:3000]  # Slack message limit

    payload = {"text": text}
    if config.channel:
        payload["channel"] = config.channel

    return _post_json(config.webhook_url, payload)


def format_discord_summary(json_data: dict[str, Any]) -> str:
    """Format a Discord-friendly summary."""
    # Discord uses similar markdown but slightly different formatting
    return format_slack_summary(json_data).replace("*", "**")


def send_discord(
    config: DiscordConfig,
    markdown_content: str,
    json_data: dict[str, Any],
) -> bool:
    """Send to Discord via webhook."""
    if not config.webhook_url:
        return False

    if config.format == "summary":
        content = format_discord_summary(json_data)
    else:
        content = markdown_content[:2000]  # Discord limit

    payload = {"content": content}
    return _post_json(config.webhook_url, payload)


def send_email(
    config: EmailConfig,
    markdown_content: str,
) -> bool:
    """Send via mailx/sendmail."""
    if not config.to:
        return False

    try:
        for recipient in config.to:
            subprocess.run(
                ["mailx", "-s", "Progress Report", recipient],
                input=markdown_content,
                text=True,
                capture_output=True,
                timeout=10,
            )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def send_webhook(
    config: WebhookConfig,
    markdown_content: str,
    json_data: dict[str, Any],
) -> bool:
    """Send to a generic webhook."""
    if not config.url:
        return False

    if config.payload == "json":
        return _post_json(config.url, json_data)
    else:
        return _post_text(config.url, markdown_content)


def _post_json(url: str, data: dict[str, Any]) -> bool:
    """POST JSON via curl."""
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(data),
                url,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _post_text(url: str, text: str) -> bool:
    """POST text via curl."""
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                "-H",
                "Content-Type: text/markdown",
                "-d",
                text,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
