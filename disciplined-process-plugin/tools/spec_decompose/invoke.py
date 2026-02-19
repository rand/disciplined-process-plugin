# @trace SPEC-07
"""Decomposer invocation — dispatch to subagent or API.

Dual-path strategy:
1. Primary (Claude Code): When CLAUDE_PLUGIN_ROOT is set, the /dp:decompose
   command instructs the main agent to use the Task tool with the decomposer
   subagent.
2. Fallback (Standalone): Uses anthropic SDK to make a direct API call.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.shared.token_count import count_tokens


@dataclass
class DecomposeParams:
    """Parameters for a decomposition invocation."""

    spec_text: str
    spec_files: list[str]
    context_window: int = 200_000
    holes_strategy: str = "graph"
    model: str = "opus"
    existing_state: dict[str, Any] | None = None  # For diff mode
    constitution: str | None = None
    auto_resolve: bool = False

    @property
    def is_diff(self) -> bool:
        return self.existing_state is not None


def _build_user_message(params: DecomposeParams) -> str:
    """Build the user message for the decomposer."""
    parts: list[str] = []

    parts.append(f"## Decomposition Request")
    parts.append(f"Context window: {params.context_window:,} tokens")
    parts.append(f"Holes strategy: {params.holes_strategy}")
    parts.append(f"Spec files: {', '.join(params.spec_files)}")
    parts.append(f"Spec size: ~{count_tokens(params.spec_text):,} tokens")
    parts.append("")

    if params.constitution:
        parts.append("## Constitution / Principles")
        parts.append(params.constitution)
        parts.append("")

    parts.append("## Specification")
    parts.append(params.spec_text)
    parts.append("")

    if params.existing_state:
        parts.append("## Existing State (for diff mode)")
        parts.append("Produce a diff rather than a fresh decomposition.")
        parts.append(json.dumps(params.existing_state, indent=2))
        parts.append("")

    parts.append("## Output")
    parts.append("Produce valid JSON matching the output schema. No markdown fences.")

    return "\n".join(parts)


def _read_agent_prompt() -> str:
    """Read the decomposer agent definition for use as system prompt."""
    # Try plugin-relative path
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if plugin_root:
        agent_path = Path(plugin_root) / "agents" / "decomposer.md"
        if agent_path.exists():
            content = agent_path.read_text()
            # Strip frontmatter
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    return content[end + 3:].strip()
            return content

    # Fallback: look relative to this file
    this_dir = Path(__file__).parent
    agent_path = this_dir.parent.parent / "agents" / "decomposer.md"
    if agent_path.exists():
        content = agent_path.read_text()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return content[end + 3:].strip()
        return content

    return ""


def invoke_via_api(params: DecomposeParams) -> dict[str, Any]:
    """Invoke the decomposer via the Anthropic API (standalone mode).

    Requires the 'anthropic' package (optional dependency).

    Args:
        params: Decomposition parameters.

    Returns:
        Parsed JSON dict from the decomposer.

    Raises:
        ImportError: If anthropic is not installed.
        RuntimeError: If the API call fails.
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required for standalone API invocation. "
            "Install it with: pip install anthropic"
        )

    system_prompt = _read_agent_prompt()
    user_message = _build_user_message(params)

    model_map = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
    }
    model = model_map.get(params.model, params.model)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=16384,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text
    return json.loads(raw)


def build_subagent_prompt(params: DecomposeParams) -> str:
    """Build the prompt for invoking via Claude Code Task tool.

    This is used by the /dp:decompose command to instruct the main agent
    to dispatch to the decomposer subagent.

    Args:
        params: Decomposition parameters.

    Returns:
        Prompt string for the Task tool.
    """
    return _build_user_message(params)
