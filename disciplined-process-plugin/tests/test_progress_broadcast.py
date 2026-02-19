# @trace SPEC-08
"""Tests for progress report broadcast channels."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.progress_report.broadcast import (
    _trigger_matches,
    broadcast_report,
    format_discord_summary,
    format_slack_summary,
    send_discord,
    send_email,
    send_slack,
    send_webhook,
)
from tools.shared.config import (
    BroadcastConfig,
    DiscordConfig,
    EmailConfig,
    SlackConfig,
    WebhookConfig,
)


@pytest.fixture
def sample_json():
    return {
        "trigger": "issue_completed",
        "epic_progress": 0.33,
        "tasks": {
            "total": 12,
            "completed": 4,
            "in_progress": 1,
            "blocked": 2,
            "ready": 3,
            "open": 5,
        },
        "holes": {
            "total": 3,
            "resolved": 1,
            "open_blocking": 2,
        },
        "ready_task_ids": ["bd-abc", "bd-def", "bd-ghi"],
        "recently_completed": ["bd-xyz"],
        "discovered_issues": ["bd-new"],
        "open_holes": [
            {"id": "H1", "type": "clarification", "urgency": "high"},
            {"id": "H2", "type": "research", "urgency": "medium"},
        ],
    }


class TestTriggerMatches:
    def test_all_matches_everything(self):
        assert _trigger_matches(["all"], "issue_completed") is True
        assert _trigger_matches(["all"], "on_demand") is True

    def test_exact_match(self):
        assert _trigger_matches(["issue_completed", "on_failure"], "issue_completed") is True

    def test_no_match(self):
        assert _trigger_matches(["issue_completed"], "on_demand") is False

    def test_empty_list(self):
        assert _trigger_matches([], "anything") is False


class TestFormatSlackSummary:
    def test_basic_format(self, sample_json):
        text = format_slack_summary(sample_json)
        assert "4/12 tasks complete" in text
        assert "33%" in text
        assert "3 tasks ready" in text
        assert "1 new issue" in text
        assert "2 open hole" in text
        assert "1 need human decision" in text
        assert "bd-abc" in text

    def test_no_ready_tasks(self, sample_json):
        sample_json["tasks"]["ready"] = 0
        sample_json["ready_task_ids"] = []
        text = format_slack_summary(sample_json)
        assert "ready for execution" not in text

    def test_no_holes(self, sample_json):
        sample_json["open_holes"] = []
        text = format_slack_summary(sample_json)
        assert "hole" not in text.lower()


class TestFormatDiscordSummary:
    def test_uses_double_stars(self, sample_json):
        text = format_discord_summary(sample_json)
        assert "**Progress Report**" in text
        # Verify single-star formatting was replaced with double-star
        # (can't just check absence since ** contains * as substring)
        lines = text.split("\n")
        for line in lines:
            # No isolated single-star bold markers
            if "Progress Report" in line:
                assert line.startswith("**")


class TestSendSlack:
    @patch("tools.progress_report.broadcast._post_json")
    def test_sends_summary(self, mock_post, sample_json):
        mock_post.return_value = True
        config = SlackConfig(
            enabled=True,
            webhook_url="https://hooks.slack.com/test",
            channel="#dev",
            format="summary",
        )
        result = send_slack(config, "full markdown", sample_json)
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/test"
        payload = call_args[0][1]
        assert payload["channel"] == "#dev"

    @patch("tools.progress_report.broadcast._post_json")
    def test_sends_full(self, mock_post, sample_json):
        mock_post.return_value = True
        config = SlackConfig(
            enabled=True,
            webhook_url="https://hooks.slack.com/test",
            format="full",
        )
        send_slack(config, "# Full Report\nContent here", sample_json)
        payload = mock_post.call_args[0][1]
        assert "Full Report" in payload["text"]

    def test_empty_url_returns_false(self, sample_json):
        config = SlackConfig(enabled=True, webhook_url="")
        assert send_slack(config, "", sample_json) is False


class TestSendDiscord:
    @patch("tools.progress_report.broadcast._post_json")
    def test_sends(self, mock_post, sample_json):
        mock_post.return_value = True
        config = DiscordConfig(
            enabled=True,
            webhook_url="https://discord.com/api/test",
        )
        result = send_discord(config, "markdown", sample_json)
        assert result is True

    def test_empty_url(self, sample_json):
        config = DiscordConfig(enabled=True, webhook_url="")
        assert send_discord(config, "", sample_json) is False


class TestSendEmail:
    @patch("subprocess.run")
    def test_sends_to_recipients(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        config = EmailConfig(
            enabled=True,
            to=["dev@example.com", "pm@example.com"],
        )
        result = send_email(config, "Report content")
        assert result is True
        assert mock_run.call_count == 2

    def test_empty_recipients(self):
        config = EmailConfig(enabled=True, to=[])
        assert send_email(config, "content") is False

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_mailx_not_found(self, mock_run):
        config = EmailConfig(enabled=True, to=["dev@example.com"])
        assert send_email(config, "content") is False


class TestSendWebhook:
    @patch("tools.progress_report.broadcast._post_json")
    def test_json_payload(self, mock_post, sample_json):
        mock_post.return_value = True
        config = WebhookConfig(
            enabled=True,
            url="https://example.com/hook",
            payload="json",
        )
        result = send_webhook(config, "markdown", sample_json)
        assert result is True
        mock_post.assert_called_once_with("https://example.com/hook", sample_json)

    @patch("tools.progress_report.broadcast._post_text")
    def test_markdown_payload(self, mock_post, sample_json):
        mock_post.return_value = True
        config = WebhookConfig(
            enabled=True,
            url="https://example.com/hook",
            payload="markdown",
        )
        send_webhook(config, "# Report", sample_json)
        mock_post.assert_called_once_with("https://example.com/hook", "# Report")

    def test_empty_url(self, sample_json):
        config = WebhookConfig(enabled=True, url="")
        assert send_webhook(config, "", sample_json) is False


class TestBroadcastReport:
    @patch("tools.progress_report.broadcast.send_slack")
    @patch("tools.progress_report.broadcast.send_discord")
    @patch("tools.progress_report.broadcast.send_webhook")
    def test_broadcasts_to_enabled_channels(
        self, mock_webhook, mock_discord, mock_slack, sample_json
    ):
        mock_slack.return_value = True
        mock_discord.return_value = True
        mock_webhook.return_value = False

        config = BroadcastConfig(
            slack=SlackConfig(
                enabled=True,
                webhook_url="https://slack",
                on_triggers=["all"],
            ),
            discord=DiscordConfig(
                enabled=True,
                webhook_url="https://discord",
                on_triggers=["issue_completed"],
            ),
            webhook=WebhookConfig(
                enabled=True,
                url="https://webhook",
                on_triggers=["on_failure"],
            ),
        )

        delivered = broadcast_report(
            config,
            "markdown",
            sample_json,
            trigger="issue_completed",
        )
        assert "slack" in delivered
        assert "discord" in delivered
        assert "webhook" not in delivered  # trigger doesn't match

    def test_no_enabled_channels(self, sample_json):
        config = BroadcastConfig()
        delivered = broadcast_report(config, "markdown", sample_json, "on_demand")
        assert delivered == []
