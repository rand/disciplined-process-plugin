# @trace SPEC-07
"""CLI entry point for spec-decompose.

Usage:
    spec-decompose [options] <spec-files...>
    spec-decompose docs/spec/auth.md --output beads
    spec-decompose --diff docs/spec/auth.md
    spec-decompose docs/spec/auth.md --orchestrate --parallel-slots 4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.spec_decompose.analyzer import read_spec_files
from tools.spec_decompose.validate import (
    parse_decomposition_output,
    save_raw_output,
)
from tools.spec_decompose.output_beads import write_beads_output
from tools.spec_decompose.output_markdown import write_markdown_output
from tools.spec_decompose.invoke import DecomposeParams, build_subagent_prompt
from tools.spec_decompose.graph import validate_dag


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="spec-decompose",
        description="Decompose specifications into dependency-aware work items",
    )

    parser.add_argument(
        "spec_files",
        nargs="+",
        type=Path,
        help="Spec files or directories to decompose",
    )

    parser.add_argument(
        "--output", "-o",
        choices=["beads", "markdown"],
        default="beads",
        help="Output format (default: beads)",
    )

    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Output directory for markdown (default: docs/tasks/)",
    )

    parser.add_argument(
        "--context-window",
        type=int,
        default=200_000,
        help="Target context window in tokens (default: 200000)",
    )

    parser.add_argument(
        "--constitution",
        type=Path,
        default=None,
        help="Path to constitution/principles file",
    )

    # Decomposition mode
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Diff against existing state instead of fresh decompose",
    )

    # Holes
    parser.add_argument(
        "--holes-strategy",
        choices=["graph", "warn", "strict", "assume"],
        default="graph",
        help="How to handle ambiguities (default: graph)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on ambiguities (equivalent to --holes-strategy strict)",
    )

    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="Assume on ambiguities (equivalent to --holes-strategy assume)",
    )

    parser.add_argument(
        "--auto-resolve",
        action="store_true",
        help="Let agents attempt validation/research holes during decomposition",
    )

    # Multi-agent
    parser.add_argument(
        "--orchestrate",
        action="store_true",
        help="Generate orchestration script (orchestrate.sh)",
    )

    parser.add_argument(
        "--parallel-slots",
        type=int,
        default=3,
        help="Max concurrent agents for orchestration (default: 3)",
    )

    # Advanced
    parser.add_argument(
        "--model",
        default="opus",
        help="Model for decomposition subagent (default: opus)",
    )

    parser.add_argument(
        "--existing-code",
        type=Path,
        default=None,
        help="Path to codebase for better file size estimates",
    )

    parser.add_argument(
        "--epic-title",
        type=str,
        default=None,
        help="Override the generated epic title",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show plan without generating output files",
    )

    parser.add_argument(
        "--json-input",
        type=Path,
        default=None,
        help="Read decomposition from a JSON file instead of invoking the subagent",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve holes strategy shortcuts
    if args.strict:
        args.holes_strategy = "strict"
    elif args.best_effort:
        args.holes_strategy = "assume"

    # Read spec files
    bundle = read_spec_files(args.spec_files)
    if not bundle.files:
        print("Error: No spec files found", file=sys.stderr)
        return 1

    print(f"Read {len(bundle.files)} spec file(s), ~{bundle.total_tokens:,} tokens")
    if bundle.needs_sharding:
        print("Warning: Spec exceeds 150K tokens, sharding recommended")

    # Get decomposition data
    data: dict[str, Any] | None = None

    if args.json_input:
        # Read from pre-computed JSON
        try:
            data = json.loads(args.json_input.read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading JSON input: {e}", file=sys.stderr)
            return 1
    else:
        # Build params for subagent invocation
        constitution = None
        if args.constitution and args.constitution.exists():
            constitution = args.constitution.read_text()

        params = DecomposeParams(
            spec_text=bundle.combined_text,
            spec_files=[str(f.path) for f in bundle.files],
            context_window=args.context_window,
            holes_strategy=args.holes_strategy,
            model=args.model,
            constitution=constitution,
            auto_resolve=args.auto_resolve,
            existing_code_path=str(args.existing_code) if args.existing_code else None,
        )

        # Print the subagent prompt for manual invocation
        prompt = build_subagent_prompt(params)
        print(f"\nDecomposition prompt ({len(prompt):,} chars).")
        print("Invoke the decomposer subagent with this prompt, then provide")
        print("the JSON output via --json-input.\n")
        print("For Claude Code: use Task tool with subagent_type=decomposer")
        print("For API: use spec-decompose with anthropic SDK (pip install anthropic)")

        # Save prompt for reference
        prompt_path = Path("decompose-prompt.md")
        prompt_path.write_text(prompt)
        print(f"\nPrompt saved to {prompt_path}")
        return 0

    # Validate the decomposition
    result = parse_decomposition_output(json.dumps(data))
    if not result.is_valid:
        print("Validation errors:", file=sys.stderr)
        for e in result.errors:
            print(f"  - {e}", file=sys.stderr)
        if result.raw_output:
            save_path = save_raw_output(result.raw_output)
            print(f"Raw output saved to {save_path}", file=sys.stderr)
        return 1

    if result.warnings:
        for w in result.warnings:
            print(f"Warning: {w}")

    # Validate DAG
    tasks = data.get("tasks", [])
    holes = data.get("holes", [])
    dag_errors = validate_dag(tasks, holes)
    if dag_errors:
        print("DAG validation errors:", file=sys.stderr)
        for e in dag_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    # Dry run: just show the plan
    if args.dry_run:
        from tools.spec_decompose.output_beads import generate_plan_markdown
        print(generate_plan_markdown(data))
        return 0

    # Diff mode: generate incremental update instead of fresh plan
    if args.diff:
        from tools.spec_decompose.diff import (
            compute_diff,
            snapshot_from_beads_json,
            snapshot_from_state_yaml,
            write_diff_output,
        )
        import subprocess

        # Get existing state from Beads or state.yaml
        existing: list = []
        task_dir = args.dir or Path("docs/tasks")
        state_yaml = Path(task_dir) / "state.yaml"
        if state_yaml.exists():
            existing = snapshot_from_state_yaml(state_yaml)
        else:
            try:
                result = subprocess.run(
                    ["bd", "list", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    existing = snapshot_from_beads_json(
                        json.loads(result.stdout)
                    )
            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                pass

        if not existing:
            print("Warning: No existing state found. Diff will treat all items as new.")

        diff_result = compute_diff(existing, data)
        output_dir = args.dir or Path(".")
        diff_md, diff_sh = write_diff_output(
            diff_result,
            spec_source=", ".join(str(f.path) for f in bundle.files),
            output_dir=output_dir,
            existing_tasks=existing,
        )
        print(f"Diff plan: {diff_md}")
        print(f"Diff script: {diff_sh}")
        print(f"\nReview the diff, then run: bash {diff_sh}")
        return 0

    # Generate output
    if args.output == "beads":
        plan_md, plan_sh = write_beads_output(
            data, epic_title=args.epic_title
        )
        print(f"Plan: {plan_md}")
        print(f"Script: {plan_sh}")
        print(f"\nReview the plan, then run: bash {plan_sh}")
    else:
        output_dir = args.dir or Path("docs/tasks")
        out = write_markdown_output(
            data,
            output_dir=output_dir,
            spec_files=[str(f.path) for f in bundle.files],
        )
        print(f"Output directory: {out}")

    # Orchestration scripts
    if args.orchestrate:
        from tools.spec_decompose.orchestration import write_orchestration_output

        orch_dir = args.dir or Path(".")
        orch_paths = write_orchestration_output(
            data,
            parallel_slots=args.parallel_slots,
            output_dir=orch_dir,
            include_pull_loop=True,
        )
        for p in orch_paths:
            print(f"Orchestration: {p}")
        print(f"\nAfter running the plan, execute: bash orchestrate.sh")

    return 0


if __name__ == "__main__":
    sys.exit(main())
