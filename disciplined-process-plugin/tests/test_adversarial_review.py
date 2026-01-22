"""
Tests for adversarial_review module.

Covers:
- Critique parsing from adversary responses
- Hallucination detection
- Context gathering and formatting
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

# Import module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from adversarial_review import (
    AdversaryResponse,
    Critique,
    ReviewContext,
    detect_hallucinations,
    format_context_for_adversary,
    format_critique_output,
    get_changed_files,
    get_git_diff,
    parse_adversary_response,
    validate_critique,
)


class TestCritiqueDataclass:
    """Tests for Critique dataclass."""

    def test_creates_with_required_fields(self):
        """Should create critique with required fields."""
        critique = Critique(
            category="LOGIC",
            file_path="auth.py",
            line_number=42,
            description="Missing null check",
        )
        assert critique.category == "LOGIC"
        assert critique.line_number == 42
        assert critique.is_hallucination is False

    def test_default_severity_is_medium(self):
        """Default severity should be MEDIUM."""
        critique = Critique(
            category="LOGIC",
            file_path="auth.py",
            line_number=1,
            description="Test",
        )
        assert critique.severity == "MEDIUM"


class TestParseAdversaryResponse:
    """Tests for parse_adversary_response function."""

    def test_parses_no_issues_found(self):
        """Should detect 'no issues found' response."""
        response = parse_adversary_response("No issues found.")
        assert response.no_issues is True
        assert len(response.critiques) == 0

    def test_parses_no_issues_case_insensitive(self):
        """Should detect 'NO ISSUES FOUND' regardless of case."""
        response = parse_adversary_response("NO ISSUES FOUND")
        assert response.no_issues is True

        response = parse_adversary_response("No Issues Found.")
        assert response.no_issues is True

    def test_parses_single_critique(self):
        """Should parse a single critique block."""
        raw = """[LOGIC] auth.py:45
Function returns early without checking is_active flag.

Why it's wrong:
Deactivated users can still authenticate.

Suggested fix:
Add is_active check before return.
"""
        response = parse_adversary_response(raw)

        assert response.no_issues is False
        assert len(response.critiques) == 1

        critique = response.critiques[0]
        assert critique.category == "LOGIC"
        assert critique.file_path == "auth.py"
        assert critique.line_number == 45
        assert "returns early" in critique.description

    def test_parses_multiple_critiques(self):
        """Should parse multiple critique blocks."""
        raw = """[LOGIC] auth.py:45
Missing null check.

[SECURITY] auth.py:78
Password comparison vulnerable.

[PLACEHOLDER] utils.py:10
TODO comment should be implemented.
"""
        response = parse_adversary_response(raw)

        assert len(response.critiques) == 3
        categories = [c.category for c in response.critiques]
        assert "LOGIC" in categories
        assert "SECURITY" in categories
        assert "PLACEHOLDER" in categories

    def test_preserves_raw_response(self):
        """Should preserve the raw response text."""
        raw = "Some response text"
        response = parse_adversary_response(raw)
        assert response.raw_response == raw


class TestValidateCritique:
    """Tests for validate_critique function."""

    def test_detects_nonexistent_file(self, temp_project_dir: Path):
        """Should flag critique for nonexistent file as hallucination."""
        critique = Critique(
            category="LOGIC",
            file_path="nonexistent.py",
            line_number=10,
            description="Some issue",
        )

        validated = validate_critique(critique, temp_project_dir)

        assert validated.is_hallucination is True
        assert "does not exist" in validated.hallucination_reason

    def test_detects_invalid_line_number(self, temp_project_dir: Path):
        """Should flag critique with invalid line number."""
        # Create a file with 5 lines
        test_file = temp_project_dir / "short.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5")

        critique = Critique(
            category="LOGIC",
            file_path="short.py",
            line_number=100,  # Way beyond file length
            description="Some issue",
        )

        validated = validate_critique(critique, temp_project_dir)

        assert validated.is_hallucination is True
        assert "does not exist" in validated.hallucination_reason

    def test_detects_referenced_name_not_in_file(self, temp_project_dir: Path):
        """Should flag critique referencing nonexistent function/variable."""
        test_file = temp_project_dir / "code.py"
        test_file.write_text("def real_function():\n    pass\n")

        critique = Critique(
            category="LOGIC",
            file_path="code.py",
            line_number=1,
            description="The function `nonexistent_function` has a bug",
        )

        validated = validate_critique(critique, temp_project_dir)

        assert validated.is_hallucination is True
        assert "nonexistent_function" in validated.hallucination_reason

    def test_valid_critique_not_flagged(self, temp_project_dir: Path):
        """Valid critique should not be flagged as hallucination."""
        test_file = temp_project_dir / "code.py"
        test_file.write_text("def authenticate():\n    return True\n")

        critique = Critique(
            category="LOGIC",
            file_path="code.py",
            line_number=1,
            description="The `authenticate` function lacks proper validation",
        )

        validated = validate_critique(critique, temp_project_dir)

        assert validated.is_hallucination is False
        assert validated.hallucination_reason == ""


class TestDetectHallucinations:
    """Tests for detect_hallucinations function."""

    def test_validates_all_critiques(self, temp_project_dir: Path):
        """Should validate all critiques in response."""
        # Create one valid file
        (temp_project_dir / "real.py").write_text("x = 1\n")

        response = AdversaryResponse(
            critiques=[
                Critique(
                    category="LOGIC",
                    file_path="real.py",
                    line_number=1,
                    description="Issue",
                ),
                Critique(
                    category="LOGIC",
                    file_path="fake.py",
                    line_number=1,
                    description="Issue",
                ),
            ]
        )

        validated = detect_hallucinations(response, temp_project_dir)

        # Second critique should be flagged
        assert validated.critiques[0].is_hallucination is False
        assert validated.critiques[1].is_hallucination is True


class TestFormatContextForAdversary:
    """Tests for format_context_for_adversary function."""

    def test_includes_diff(self):
        """Should include diff in formatted output."""
        context = ReviewContext(
            diff="+ new line\n- old line",
            files_changed=["file.py"],
            specs={},
            tests={},
            previous_critiques=[],
        )

        formatted = format_context_for_adversary(context)

        assert "Files Changed" in formatted
        assert "+ new line" in formatted

    def test_truncates_large_diff(self):
        """Should truncate diffs larger than 10000 chars."""
        large_diff = "x" * 15000
        context = ReviewContext(
            diff=large_diff,
            files_changed=["file.py"],
            specs={},
            tests={},
            previous_critiques=[],
        )

        formatted = format_context_for_adversary(context)

        assert len(formatted) < len(large_diff)
        assert "truncated" in formatted.lower()

    def test_includes_specs_when_present(self):
        """Should include specs section when specs are provided."""
        context = ReviewContext(
            diff="some diff",
            files_changed=["file.py"],
            specs={"SPEC-01.01": "User can log in"},
            tests={},
            previous_critiques=[],
        )

        formatted = format_context_for_adversary(context)

        assert "Relevant Specs" in formatted
        assert "SPEC-01.01" in formatted

    def test_includes_previous_critiques(self):
        """Should include previous critiques section."""
        context = ReviewContext(
            diff="some diff",
            files_changed=["file.py"],
            specs={},
            tests={},
            previous_critiques=["Fixed null check", "Added validation"],
        )

        formatted = format_context_for_adversary(context)

        assert "Previous Critiques" in formatted
        assert "Fixed null check" in formatted


class TestFormatCritiqueOutput:
    """Tests for format_critique_output function."""

    def test_formats_no_issues(self):
        """Should format 'no issues' response."""
        response = AdversaryResponse(no_issues=True)
        output = format_critique_output(response, iteration=1)

        assert "No issues found" in output
        assert "Iteration 1" in output

    def test_formats_critiques_with_numbers(self):
        """Should format critiques with numbered list."""
        response = AdversaryResponse(
            critiques=[
                Critique(
                    category="LOGIC",
                    file_path="auth.py",
                    line_number=45,
                    description="Missing check",
                ),
                Critique(
                    category="SECURITY",
                    file_path="auth.py",
                    line_number=78,
                    description="Timing attack",
                ),
            ]
        )

        output = format_critique_output(response, iteration=2)

        assert "1. [LOGIC]" in output
        assert "2. [SECURITY]" in output
        assert "auth.py:45" in output
        assert "auth.py:78" in output

    def test_includes_hallucination_flag(self):
        """Should include hallucination warning when flagged."""
        response = AdversaryResponse(
            critiques=[
                Critique(
                    category="LOGIC",
                    file_path="auth.py",
                    line_number=45,
                    description="Issue",
                    is_hallucination=True,
                    hallucination_reason="File does not exist",
                ),
            ]
        )

        output = format_critique_output(response, iteration=1)

        assert "HALLUCINATION" in output
        assert "File does not exist" in output

    def test_includes_options_menu(self):
        """Should include options menu for non-empty critiques."""
        response = AdversaryResponse(
            critiques=[
                Critique(
                    category="LOGIC",
                    file_path="auth.py",
                    line_number=45,
                    description="Issue",
                ),
            ]
        )

        output = format_critique_output(response, iteration=1)

        assert "[A]ccept" in output
        assert "[R]eject" in output
        assert "[D]one" in output


class TestPropertyBasedAdversarialReview:
    """Property-based tests for adversarial review functions."""

    @given(st.integers(min_value=1, max_value=1000))
    def test_line_number_validation(self, line_num: int):
        """Critiques with line numbers beyond file should be flagged."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project_dir = Path(tmpdir)
            # File with exactly 10 lines
            test_file = temp_project_dir / "test.py"
            test_file.write_text("\n".join(f"line{i}" for i in range(10)))

            critique = Critique(
                category="LOGIC",
                file_path="test.py",
                line_number=line_num,
                description="Issue",
            )

            validated = validate_critique(critique, temp_project_dir)

            if line_num > 10:
                assert validated.is_hallucination is True
            # Note: line_num <= 10 may or may not be hallucination depending on content

    @given(
        st.lists(
            st.sampled_from(["LOGIC", "SECURITY", "PLACEHOLDER", "ERROR", "CONVENTION"]),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=10)
    def test_multiple_categories_parsed(self, categories: list[str]):
        """Should correctly parse critiques with various categories."""
        lines = []
        for i, cat in enumerate(categories):
            lines.append(f"[{cat}] file{i}.py:{i+1}")
            lines.append(f"Description for {cat}")
            lines.append("")

        raw = "\n".join(lines)
        response = parse_adversary_response(raw)

        # All categories should be present in parsed critiques
        parsed_cats = [c.category for c in response.critiques]
        for cat in categories:
            assert cat in parsed_cats

    @given(st.text(min_size=1, max_size=100).filter(lambda x: "issue" not in x.lower()))
    def test_arbitrary_text_doesnt_crash(self, text: str):
        """Parser should handle arbitrary text without crashing."""
        # Should not raise exception
        response = parse_adversary_response(text)
        assert isinstance(response, AdversaryResponse)
