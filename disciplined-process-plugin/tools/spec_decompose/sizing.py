# @trace SPEC-07
"""Context-window sizing model for decomposed tasks.

Implements [SIZE-1] through [SIZE-4] from the context-sizing spec:
- Budget model: how the context window is partitioned
- Overhead ceiling: task description + context files <= 15% of window
- Total consumption ceiling: estimated total <= 80% of window
- Split/merge heuristics
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from tools.shared.token_count import (
    count_tokens,
    estimate_file_tokens,
    estimate_implementation_tokens,
    estimate_test_tokens,
    estimate_tool_overhead,
)


@dataclass
class TokenBudget:
    """Token budget derived from a context window size. [SIZE-1]"""

    context_window: int
    system_overhead: int  # system prompt, CLAUDE.md, agent overhead
    overhead_ceiling: int  # max for task description + context files [SIZE-2]
    total_ceiling: int  # max for estimated total consumption [SIZE-2b]
    working_memory: int  # remaining after overhead

    @property
    def buffer(self) -> int:
        """20% buffer for retries, compaction, exploration."""
        return self.context_window - self.total_ceiling


def compute_budget(
    context_window: int = 200_000,
    system_overhead: int = 8_000,
) -> TokenBudget:
    """Compute the token budget for a given context window. [SIZE-1]

    Args:
        context_window: Total context window size in tokens.
        system_overhead: Estimated system prompt + agent overhead tokens.

    Returns:
        TokenBudget with all limits calculated.
    """
    overhead_ceiling = int(context_window * 0.15)  # [SIZE-2]
    total_ceiling = int(context_window * 0.80)  # [SIZE-2b]
    working_memory = total_ceiling - system_overhead - overhead_ceiling

    return TokenBudget(
        context_window=context_window,
        system_overhead=system_overhead,
        overhead_ceiling=overhead_ceiling,
        total_ceiling=total_ceiling,
        working_memory=max(0, working_memory),
    )


@dataclass
class TaskEstimate:
    """Token estimate for a single task."""

    task_number: int | str
    description_tokens: int
    context_file_tokens: int
    implementation_tokens: int
    test_tokens: int
    tool_overhead_tokens: int

    @property
    def overhead(self) -> int:
        """Description + context files (must fit within overhead ceiling)."""
        return self.description_tokens + self.context_file_tokens

    @property
    def total(self) -> int:
        """Total estimated consumption."""
        return (
            self.description_tokens
            + self.context_file_tokens
            + self.implementation_tokens
            + self.test_tokens
            + self.tool_overhead_tokens
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "overhead": self.overhead,
            "implementation": self.implementation_tokens,
            "tests": self.test_tokens,
            "total": self.total,
        }


Complexity = Literal["simple", "moderate", "complex"]


def _infer_complexity(task: dict[str, Any]) -> Complexity:
    """Infer task complexity from signals in the task dict."""
    signals = task.get("complexity_signals", {})
    conditions = signals.get("conditions", 0)
    error_cases = signals.get("error_cases", 0)
    integrations = signals.get("integrations", 0)

    score = conditions + error_cases + integrations * 2
    if score >= 6:
        return "complex"
    elif score >= 3:
        return "moderate"
    return "simple"


def estimate_task_tokens(
    task: dict[str, Any],
    existing_code: Path | None = None,
) -> TaskEstimate:
    """Estimate total token consumption for a task. [SIZE-1]

    Args:
        task: Task dict with description, context_files, complexity info.
        existing_code: Path to existing codebase for actual file measurements.

    Returns:
        TaskEstimate with all components.
    """
    # Description tokens
    desc = task.get("description", "")
    desc_tokens = count_tokens(desc) if desc else 500  # Default estimate

    # Context file tokens
    ctx_tokens = 0
    for cf in task.get("context_files", []):
        path_str = cf.get("path", "")
        if existing_code and path_str:
            full_path = existing_code / path_str
            actual = estimate_file_tokens(full_path)
            if actual > 0:
                ctx_tokens += actual
                continue
        # Use estimate from the decomposition
        ctx_tokens += cf.get("estimated_tokens", 2000)

    # Implementation + test tokens
    complexity = task.get("complexity", _infer_complexity(task))
    impl_tokens = estimate_implementation_tokens(complexity)
    test_tokens = estimate_test_tokens(complexity)

    # Tool overhead (estimate 10-30 tool calls depending on complexity)
    tool_calls = {"simple": 10, "moderate": 20, "complex": 30}.get(complexity, 20)
    tool_tokens = estimate_tool_overhead(tool_calls)

    return TaskEstimate(
        task_number=task.get("number", 0),
        description_tokens=desc_tokens,
        context_file_tokens=ctx_tokens,
        implementation_tokens=impl_tokens,
        test_tokens=test_tokens,
        tool_overhead_tokens=tool_tokens,
    )


def should_split(estimate: TaskEstimate, budget: TokenBudget) -> bool:
    """Check if a task should be split because it exceeds the budget. [SIZE-3]

    A task should be split if:
    - Its overhead exceeds the overhead ceiling, OR
    - Its total exceeds the total ceiling
    """
    return (
        estimate.overhead > budget.overhead_ceiling
        or estimate.total > budget.total_ceiling
    )


def should_merge(estimate: TaskEstimate) -> bool:
    """Check if a task is trivially small and should be merged. [SIZE-4]

    A task with total estimated consumption <5K tokens creates unnecessary
    context-switching overhead.
    """
    return estimate.total < 5_000


@dataclass
class SizingWarning:
    """Warning from post-hoc sizing validation."""

    task_number: int | str
    task_title: str
    estimated_total: int
    ceiling: int
    message: str


def validate_decomposition_sizing(
    tasks: list[dict[str, Any]],
    context_window: int = 200_000,
) -> list[SizingWarning]:
    """Validate that every task fits within the budget ceiling.

    Checks each task's estimated_tokens against the computed budget.
    Returns warnings for any task that exceeds limits.

    Args:
        tasks: List of task dicts with 'estimated_tokens'.
        context_window: Context window size in tokens.

    Returns:
        List of SizingWarning for over-budget tasks.
    """
    budget = compute_budget(context_window)
    warnings: list[SizingWarning] = []

    for t in tasks:
        est = t.get("estimated_tokens", {})
        total = est.get("total", 0)
        overhead = est.get("overhead", 0)

        if total > budget.total_ceiling:
            warnings.append(SizingWarning(
                task_number=t["number"],
                task_title=t.get("title", ""),
                estimated_total=total,
                ceiling=budget.total_ceiling,
                message=(
                    f"Task {t['number']} ({t.get('title', '')}) estimated at "
                    f"~{total:,} tokens exceeds total ceiling of "
                    f"~{budget.total_ceiling:,} tokens. Consider splitting."
                ),
            ))
        elif overhead > budget.overhead_ceiling:
            warnings.append(SizingWarning(
                task_number=t["number"],
                task_title=t.get("title", ""),
                estimated_total=total,
                ceiling=budget.overhead_ceiling,
                message=(
                    f"Task {t['number']} ({t.get('title', '')}) overhead at "
                    f"~{overhead:,} tokens exceeds overhead ceiling of "
                    f"~{budget.overhead_ceiling:,} tokens. Consider splitting."
                ),
            ))

    return warnings


# Common configurations from the spec
WINDOW_PRESETS: dict[str, int] = {
    "claude-code": 200_000,
    "codex": 128_000,
    "parallel": 64_000,
}
