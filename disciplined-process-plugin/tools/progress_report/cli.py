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

    if args.watch:
        print("Watch mode not yet implemented. Use one-shot mode.", file=sys.stderr)
        return 1

    from tools.progress_report.extractor import extract_state
    from tools.progress_report.report import write_report
    from tools.shared.config import ProgressReportConfig

    # Load config
    config_path = Path(args.config) if args.config else None
    config = ProgressReportConfig.load(config_path)

    # Extract state
    project_root = Path(args.project_root)
    state = extract_state(project_root)

    # Determine trigger
    trigger_reason = args.trigger or "on_demand"

    # Generate report
    output_dir = Path(args.output_dir) if args.output_dir else None
    md_path, json_path = write_report(
        state,
        trigger_reason=trigger_reason,
        epic_title=args.epic_title,
        output_dir=output_dir,
    )

    print(f"Report written to: {md_path}")
    print(f"JSON written to: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
