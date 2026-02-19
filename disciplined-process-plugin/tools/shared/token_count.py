# @trace SPEC-07
"""Token counting abstraction with graceful fallback.

Wraps tiktoken for accurate token counting. Falls back to a character-based
heuristic (len(text) // 4) if tiktoken is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

_tiktoken_available = True
_encoding_cache: dict[str, object] = {}

try:
    import tiktoken
except ImportError:
    _tiktoken_available = False
    tiktoken = None  # type: ignore[assignment]


def _get_encoding(model: str = "cl100k_base") -> object | None:
    """Get or cache a tiktoken encoding."""
    if not _tiktoken_available:
        return None
    if model not in _encoding_cache:
        try:
            _encoding_cache[model] = tiktoken.get_encoding(model)
        except Exception:
            return None
    return _encoding_cache[model]


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken, with fallback heuristic.

    Args:
        text: The text to count tokens for.
        model: The tiktoken encoding name (default: cl100k_base).

    Returns:
        Token count (exact if tiktoken available, approximate otherwise).
    """
    enc = _get_encoding(model)
    if enc is not None:
        try:
            return len(enc.encode(text))  # type: ignore[union-attr]
        except Exception:
            pass
    # Fallback: ~4 chars per token is a reasonable approximation
    return len(text) // 4


def estimate_file_tokens(path: Path, model: str = "cl100k_base") -> int:
    """Count tokens in a file. Returns 0 if file doesn't exist or can't be read."""
    try:
        text = path.read_text(encoding="utf-8")
        return count_tokens(text, model)
    except (OSError, UnicodeDecodeError):
        return 0


Complexity = Literal["simple", "moderate", "complex"]

# Calibrated estimates for implementation token consumption
_IMPLEMENTATION_ESTIMATES: dict[Complexity, int] = {
    "simple": 10_000,
    "moderate": 20_000,
    "complex": 35_000,
}

# Test code is ~40% of implementation estimate
_TEST_RATIO = 0.4

# Tool call overhead per estimated call
_TOOL_CALL_OVERHEAD = 300


def estimate_implementation_tokens(complexity: Complexity) -> int:
    """Estimate implementation token consumption by complexity level."""
    return _IMPLEMENTATION_ESTIMATES[complexity]


def estimate_test_tokens(complexity: Complexity) -> int:
    """Estimate test token consumption (~40% of implementation)."""
    return int(_IMPLEMENTATION_ESTIMATES[complexity] * _TEST_RATIO)


def estimate_tool_overhead(num_calls: int) -> int:
    """Estimate tool call overhead tokens."""
    return num_calls * _TOOL_CALL_OVERHEAD


def is_tiktoken_available() -> bool:
    """Check if tiktoken is available for accurate counting."""
    return _tiktoken_available
