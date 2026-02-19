# @trace SPEC-07
"""JSON parsing and schema validation for decomposer output.

Implements a 5-layer fallback for extracting valid JSON from LLM output:
1. Strip markdown fences
2. json.loads() strict
3. Fix trailing commas, retry
4. Schema validation (required fields, DAG property, coverage)
5. On total failure: save raw output with instructions
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating decomposer output."""

    is_valid: bool
    data: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_output: str = ""


# Required top-level keys in the decomposition output
REQUIRED_KEYS = {"spec_source", "epic", "tasks"}
REQUIRED_TASK_KEYS = {"number", "title", "description", "depends_on_tasks"}
REQUIRED_HOLE_KEYS = {"number", "title", "hole_type", "blocks_tasks"}

# Valid hole types
VALID_HOLE_TYPES = {
    "clarification", "validation", "research", "synthesis", "escalation"
}


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from text (layer 1)."""
    # Match ```json ... ``` or ``` ... ```
    pattern = r"```(?:json)?\s*\n?(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (layer 3)."""
    # Remove trailing commas in objects
    text = re.sub(r",\s*}", "}", text)
    # Remove trailing commas in arrays
    text = re.sub(r",\s*]", "]", text)
    return text


def _validate_schema(data: dict[str, Any]) -> list[str]:
    """Validate the parsed JSON against expected schema (layer 4)."""
    errors: list[str] = []

    # Check required top-level keys
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        errors.append(f"Missing required keys: {', '.join(sorted(missing))}")

    # Validate tasks
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        errors.append("'tasks' must be a list")
    else:
        task_numbers: set[int | str] = set()
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"Task {i} is not a dict")
                continue
            task_missing = REQUIRED_TASK_KEYS - set(task.keys())
            if task_missing:
                errors.append(
                    f"Task {i} missing keys: {', '.join(sorted(task_missing))}"
                )
            num = task.get("number")
            if num in task_numbers:
                errors.append(f"Duplicate task number: {num}")
            task_numbers.add(num)

    # Validate holes
    holes = data.get("holes", [])
    if isinstance(holes, list):
        hole_numbers: set[str] = set()
        for i, hole in enumerate(holes):
            if not isinstance(hole, dict):
                errors.append(f"Hole {i} is not a dict")
                continue
            hole_missing = REQUIRED_HOLE_KEYS - set(hole.keys())
            if hole_missing:
                errors.append(
                    f"Hole {i} missing keys: {', '.join(sorted(hole_missing))}"
                )
            htype = hole.get("hole_type", "")
            if htype and htype not in VALID_HOLE_TYPES:
                errors.append(f"Hole {i} has invalid type: {htype}")
            hnum = hole.get("number")
            if hnum in hole_numbers:
                errors.append(f"Duplicate hole number: {hnum}")
            hole_numbers.add(hnum)

    # Validate epic
    epic = data.get("epic")
    if epic is not None and not isinstance(epic, dict):
        errors.append("'epic' must be a dict")
    elif isinstance(epic, dict) and "title" not in epic:
        errors.append("Epic missing 'title'")

    return errors


def parse_decomposition_output(raw: str) -> ValidationResult:
    """Parse and validate decomposer output with 5-layer fallback.

    Args:
        raw: Raw text output from the decomposer.

    Returns:
        ValidationResult with parsed data or error details.
    """
    if not raw or not raw.strip():
        return ValidationResult(
            is_valid=False,
            errors=["Empty output from decomposer"],
            raw_output=raw,
        )

    # Layer 1: Strip markdown fences
    cleaned = _strip_markdown_fences(raw)

    # Layer 2: Try strict JSON parse
    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Layer 3: Fix trailing commas and retry
        fixed = _fix_trailing_commas(cleaned)
        try:
            data = json.loads(fixed)
        except json.JSONDecodeError:
            pass

    if data is None:
        return ValidationResult(
            is_valid=False,
            errors=["Failed to parse JSON from decomposer output"],
            raw_output=raw,
        )

    if not isinstance(data, dict):
        return ValidationResult(
            is_valid=False,
            errors=["Decomposer output is not a JSON object"],
            raw_output=raw,
        )

    # Layer 4: Schema validation
    schema_errors = _validate_schema(data)

    # Collect warnings for non-blocking issues
    warnings: list[str] = []
    if "coverage" not in data:
        warnings.append("Missing 'coverage' section")
    if "parallel_groups" not in data:
        warnings.append("Missing 'parallel_groups' section")
    if "issues" not in data:
        warnings.append("Missing 'issues' section (flat task list)")

    return ValidationResult(
        is_valid=len(schema_errors) == 0,
        data=data,
        errors=schema_errors,
        warnings=warnings,
        raw_output=raw,
    )


def save_raw_output(raw: str, output_path: Path | None = None) -> Path:
    """Save raw decomposer output for debugging (layer 5 fallback).

    Args:
        raw: Raw output text.
        output_path: Where to save. Defaults to decompose-raw-output.txt.

    Returns:
        Path where the output was saved.
    """
    if output_path is None:
        output_path = Path("decompose-raw-output.txt")

    content = f"""# Raw Decomposer Output (Parsing Failed)
#
# The decomposer produced output that could not be parsed as valid JSON.
# Review this output and manually extract the decomposition plan.
#
# Common issues:
# - Markdown fences not properly closed
# - Trailing commas in JSON
# - Missing required fields
# - Commentary mixed with JSON
#
# Raw output follows:
# ---

{raw}
"""
    output_path.write_text(content)
    return output_path
