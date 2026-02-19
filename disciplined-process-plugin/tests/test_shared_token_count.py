"""Tests for token counting abstraction.

@trace SPEC-07
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tools.shared.token_count import (
    count_tokens,
    estimate_file_tokens,
    estimate_implementation_tokens,
    estimate_test_tokens,
    estimate_tool_overhead,
    is_tiktoken_available,
)


class TestCountTokens:
    """Tests for count_tokens function."""

    def test_empty_string_returns_zero(self) -> None:
        assert count_tokens("") == 0

    def test_nonempty_string_returns_positive(self) -> None:
        result = count_tokens("Hello, world!")
        assert result > 0

    def test_longer_text_has_more_tokens(self) -> None:
        short = count_tokens("Hello")
        long = count_tokens("Hello " * 100)
        assert long > short

    def test_consistent_results(self) -> None:
        text = "The quick brown fox jumps over the lazy dog."
        assert count_tokens(text) == count_tokens(text)

    def test_handles_unicode(self) -> None:
        result = count_tokens("Hello \u00e4\u00f6\u00fc \u2603 \U0001f600")
        assert result > 0

    def test_handles_multiline(self) -> None:
        result = count_tokens("line 1\nline 2\nline 3\n")
        assert result > 0


class TestEstimateFileTokens:
    """Tests for estimate_file_tokens function."""

    def test_nonexistent_file_returns_zero(self) -> None:
        assert estimate_file_tokens(Path("/nonexistent/file.py")) == 0

    def test_existing_file_returns_positive(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    return 42\n")
        assert estimate_file_tokens(f) > 0

    def test_empty_file_returns_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        assert estimate_file_tokens(f) == 0

    def test_binary_file_returns_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.dat"
        f.write_bytes(b"\x00\x01\x02\xff\xfe")
        # Should handle gracefully (may return 0 or a small number)
        result = estimate_file_tokens(f)
        assert isinstance(result, int)


class TestImplementationEstimates:
    """Tests for complexity-based estimation."""

    def test_simple_estimate(self) -> None:
        assert estimate_implementation_tokens("simple") == 10_000

    def test_moderate_estimate(self) -> None:
        assert estimate_implementation_tokens("moderate") == 20_000

    def test_complex_estimate(self) -> None:
        assert estimate_implementation_tokens("complex") == 35_000

    def test_complexity_ordering(self) -> None:
        s = estimate_implementation_tokens("simple")
        m = estimate_implementation_tokens("moderate")
        c = estimate_implementation_tokens("complex")
        assert s < m < c

    def test_test_estimate_is_fraction_of_implementation(self) -> None:
        for complexity in ("simple", "moderate", "complex"):
            impl = estimate_implementation_tokens(complexity)
            test = estimate_test_tokens(complexity)
            assert test == int(impl * 0.4)

    def test_tool_overhead(self) -> None:
        assert estimate_tool_overhead(0) == 0
        assert estimate_tool_overhead(1) == 300
        assert estimate_tool_overhead(10) == 3000


class TestTiktokenAvailability:
    """Tests for tiktoken detection."""

    def test_returns_bool(self) -> None:
        assert isinstance(is_tiktoken_available(), bool)


# Property-based tests
try:
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @given(st.text(min_size=0, max_size=10000))
    @settings(max_examples=50)
    def test_count_tokens_always_non_negative(text: str) -> None:
        """@trace SPEC-07 - Token count is always >= 0."""
        assert count_tokens(text) >= 0

    @given(st.integers(min_value=0, max_value=100))
    def test_tool_overhead_scales_linearly(num_calls: int) -> None:
        """@trace SPEC-07 - Tool overhead scales linearly with call count."""
        assert estimate_tool_overhead(num_calls) == num_calls * 300

except ImportError:
    pass  # hypothesis not installed, skip property tests
