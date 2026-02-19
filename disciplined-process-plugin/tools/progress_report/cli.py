# @trace SPEC-08
"""CLI entry point for progress-report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for progress-report."""
    parser = argparse.ArgumentParser(
        prog="progress-report",
        description="Generate structured progress reports from project state.",
    )

    parser.add_argument(
        "--trigger",
        type=str,
        default=None,
        help="Manual trigger reason (e.g., 'Phase 1 complete').",
    )
    parser.add_argument(
        "--no-broadcast",
        action="store_true",
        help="File output only, no notifications.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Daemon mode: poll and report on trigger conditions.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to progress-report.yaml config.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for reports (default: docs/progress/).",
    )
    parser.add_argument(
        "--epic-title",
        type=str,
        default="Project",
        help="Title for report header.",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory.",
    )

    # Output format
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "both"],
        default="both",
        help="Output format (default: both).",
    )

    # Watch mode options
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=None,
        help="Seconds between state checks in watch mode (default: 60).",
    )

    # Broadcast overrides
    parser.add_argument(
        "--broadcast",
        type=str,
        default=None,
        help="Channels to notify (comma-separated: file,slack,discord,email,webhook).",
    )
    parser.add_argument(
        "--slack-webhook",
        type=str,
        default=None,
        help="Slack webhook URL (overrides config).",
    )
    parser.add_argument(
        "--discord-webhook",
        type=str,
        default=None,
        help="Discord webhook URL (overrides config).",
    )
    parser.add_argument(
        "--email-to",
        type=str,
        nargs="+",
        default=None,
        help="Email recipient(s) (overrides config).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 = success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    from tools.progress_report.extractor import extract_state
    from tools.progress_report.report import write_report
    from tools.shared.config import ProgressReportConfig

    # Load config
    config_path = Path(args.config) if args.config else None
    config = ProgressReportConfig.load(config_path)

    # Apply CLI overrides to broadcast config
    if hasattr(args, "slack_webhook") and args.slack_webhook:
        config.broadcast.slack.webhook_url = args.slack_webhook
        config.broadcast.slack.enabled = True
    if hasattr(args, "discord_webhook") and args.discord_webhook:
        config.broadcast.discord.webhook_url = args.discord_webhook
        config.broadcast.discord.enabled = True
    if hasattr(args, "email_to") and args.email_to:
        config.broadcast.email.to = args.email_to
        config.broadcast.email.enabled = True

    project_root = Path(args.project_root)
    output_dir = Path(args.output_dir) if args.output_dir else None

    if args.watch:
        from tools.progress_report.watch import WatchDaemon

        if hasattr(args, "poll_interval") and args.poll_interval:
            config.triggers.interval = f"{args.poll_interval}s"

        daemon = WatchDaemon(
            config=config,
            project_root=project_root,
            output_dir=output_dir,
            epic_title=args.epic_title,
            no_broadcast=args.no_broadcast,
        )
        daemon.start()
        return 0

    # One-shot mode
    state = extract_state(project_root)
    trigger_reason = args.trigger or "on_demand"

    md_path, json_path = write_report(
        state,
        trigger_reason=trigger_reason,
        epic_title=args.epic_title,
        output_dir=output_dir,
    )

    # Handle --format flag
    output_format = getattr(args, "format", "both") or "both"
    if output_format in ("markdown", "both"):
        print(f"Report written to: {md_path}")
    if output_format in ("json", "both"):
        print(f"JSON written to: {json_path}")

    # Broadcast if not disabled
    if not args.no_broadcast:
        import json as json_module
        from tools.progress_report.broadcast import broadcast_report

        json_data = json_module.loads(json_path.read_text())
        md_content = md_path.read_text()
        delivered = broadcast_report(
            config.broadcast,
            md_content,
            json_data,
            trigger_reason,
            output_dir,
        )
        if delivered:
            print(f"Broadcast to: {', '.join(delivered)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
