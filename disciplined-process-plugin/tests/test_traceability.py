"""
Tests for traceability module.

Covers:
- Spec parsing from markdown files
- @trace marker extraction
- Issue link parsing
- Coverage report generation
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

# Import module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from traceability import (
    ISSUE_LINK_PATTERN,
    SPEC_ID_PATTERN,
    TRACE_PATTERN,
    SpecReference,
    TraceMarker,
    TraceCoverage,
    find_trace_markers,
    format_coverage_report,
    generate_coverage_report,
    parse_all_specs,
    parse_specs_from_file,
)


class TestSpecIdPattern:
    """Tests for SPEC_ID_PATTERN regex."""

    def test_matches_section_only(self):
        """[SPEC-01] should match with section only."""
        match = SPEC_ID_PATTERN.search("[SPEC-01]")
        assert match is not None
        assert match.group(1) == "01"
        assert match.group(2) is None

    def test_matches_section_and_paragraph(self):
        """[SPEC-01.03] should match with section and paragraph."""
        match = SPEC_ID_PATTERN.search("[SPEC-01.03]")
        assert match is not None
        assert match.group(1) == "01"
        assert match.group(2) == "03"

    def test_matches_in_line(self):
        """Should find spec ID embedded in text."""
        match = SPEC_ID_PATTERN.search("Requirement [SPEC-05.12] states that...")
        assert match is not None
        assert match.group(1) == "05"
        assert match.group(2) == "12"

    def test_no_match_without_brackets(self):
        """SPEC-01 without brackets should not match."""
        match = SPEC_ID_PATTERN.search("SPEC-01")
        assert match is None

    @given(st.integers(min_value=0, max_value=99))
    def test_matches_any_two_digit_section(self, section: int):
        """Should match any two-digit section number."""
        spec_text = f"[SPEC-{section:02d}]"
        match = SPEC_ID_PATTERN.search(spec_text)
        assert match is not None
        assert match.group(1) == f"{section:02d}"


class TestIssueLinkPattern:
    """Tests for ISSUE_LINK_PATTERN regex."""

    def test_matches_chainlink_link(self):
        """Should match chainlink issue links."""
        match = ISSUE_LINK_PATTERN.search("<!-- chainlink:15 -->")
        assert match is not None
        assert match.group(1) == "chainlink"
        assert match.group(2) == "15"

    def test_matches_beads_link(self):
        """Should match beads issue links."""
        match = ISSUE_LINK_PATTERN.search("<!-- beads:bd-a1b2 -->")
        assert match is not None
        assert match.group(1) == "beads"
        assert match.group(2) == "bd-a1b2"

    def test_matches_with_extra_spaces(self):
        """Should match with varying whitespace."""
        match = ISSUE_LINK_PATTERN.search("<!--   chainlink:1   -->")
        assert match is not None
        assert match.group(2) == "1"

    def test_no_match_for_other_comments(self):
        """Should not match regular HTML comments."""
        match = ISSUE_LINK_PATTERN.search("<!-- This is a regular comment -->")
        assert match is None


class TestTracePattern:
    """Tests for TRACE_PATTERN regex."""

    def test_matches_basic_trace(self):
        """@trace SPEC-01.03 should match."""
        match = TRACE_PATTERN.search("# @trace SPEC-01.03")
        assert match is not None
        assert match.group(1) == "01"
        assert match.group(2) == "03"
        assert match.group(3) is None

    def test_matches_trace_with_sub_item(self):
        """@trace SPEC-01.03.a should match with sub-item."""
        match = TRACE_PATTERN.search("# @trace SPEC-01.03.a")
        assert match is not None
        assert match.group(1) == "01"
        assert match.group(2) == "03"
        assert match.group(3) == "a"

    def test_matches_in_various_comment_styles(self):
        """Should match in Python, JS, and other comment styles."""
        test_cases = [
            "# @trace SPEC-01.01",
            "// @trace SPEC-01.01",
            "/* @trace SPEC-01.01 */",
            "   @trace SPEC-01.01  # validation",
        ]
        for case in test_cases:
            match = TRACE_PATTERN.search(case)
            assert match is not None, f"Failed to match: {case}"

    @given(
        st.integers(min_value=1, max_value=99),
        st.integers(min_value=1, max_value=99),
    )
    def test_matches_any_valid_spec_id(self, section: int, paragraph: int):
        """Should match any valid SPEC-XX.YY format."""
        trace_text = f"@trace SPEC-{section:02d}.{paragraph:02d}"
        match = TRACE_PATTERN.search(trace_text)
        assert match is not None


class TestParseSpecsFromFile:
    """Tests for parse_specs_from_file function."""

    def test_parses_specs_from_markdown(self, project_with_specs: Path):
        """Should parse all specs from a markdown file."""
        spec_file = project_with_specs / "docs" / "spec" / "01-authentication.md"
        specs = parse_specs_from_file(spec_file)

        assert len(specs) == 4  # SPEC-01, SPEC-01.01, SPEC-01.02, SPEC-01.03

        # Check SPEC-01 (section header)
        spec_01 = next(s for s in specs if s.spec_id == "SPEC-01")
        assert spec_01.issue_link == "chainlink:1"

        # Check SPEC-01.01
        spec_01_01 = next(s for s in specs if s.spec_id == "SPEC-01.01")
        assert spec_01_01.issue_link == "chainlink:2"
        assert "email/password" in spec_01_01.title

        # Check SPEC-01.03 (no issue link)
        spec_01_03 = next(s for s in specs if s.spec_id == "SPEC-01.03")
        assert spec_01_03.issue_link is None

    def test_returns_empty_for_nonexistent_file(self, temp_project_dir: Path):
        """Should return empty list for nonexistent file."""
        fake_file = temp_project_dir / "nonexistent.md"
        specs = parse_specs_from_file(fake_file)
        assert specs == []

    def test_returns_empty_for_file_without_specs(self, temp_project_dir: Path):
        """Should return empty list for file without spec markers."""
        plain_file = temp_project_dir / "plain.md"
        plain_file.write_text("# Just a title\n\nSome regular content.")
        specs = parse_specs_from_file(plain_file)
        assert specs == []


class TestParseAllSpecs:
    """Tests for parse_all_specs function."""

    def test_parses_all_specs_in_directory(self, project_with_specs: Path):
        """Should parse specs from all markdown files in directory."""
        spec_dir = project_with_specs / "docs" / "spec"
        specs = parse_all_specs(spec_dir)

        assert len(specs) >= 4
        spec_ids = [s.spec_id for s in specs]
        assert "SPEC-01" in spec_ids
        assert "SPEC-01.01" in spec_ids

    def test_returns_sorted_by_spec_id(self, project_with_specs: Path):
        """Should return specs sorted by spec_id."""
        spec_dir = project_with_specs / "docs" / "spec"
        specs = parse_all_specs(spec_dir)

        spec_ids = [s.spec_id for s in specs]
        assert spec_ids == sorted(spec_ids)

    def test_returns_empty_for_nonexistent_directory(self, temp_project_dir: Path):
        """Should return empty list for nonexistent directory."""
        fake_dir = temp_project_dir / "nonexistent"
        specs = parse_all_specs(fake_dir)
        assert specs == []


class TestFindTraceMarkers:
    """Tests for find_trace_markers function."""

    def test_finds_markers_in_python_files(self, project_with_code: Path):
        """Should find @trace markers in Python files."""
        src_dir = project_with_code / "src"
        markers = find_trace_markers([src_dir])

        assert len(markers) >= 2
        spec_ids = [m.spec_id for m in markers]
        assert "SPEC-01.01" in spec_ids
        assert "SPEC-01.02" in spec_ids

    def test_finds_markers_with_sub_items(self, project_with_code: Path):
        """Should find @trace markers with sub-items like SPEC-01.01.a."""
        src_dir = project_with_code / "src"
        markers = find_trace_markers([src_dir])

        sub_markers = [m for m in markers if ".a" in m.spec_id]
        assert len(sub_markers) >= 1
        assert "SPEC-01.01.a" in [m.spec_id for m in sub_markers]

    def test_returns_correct_line_numbers(self, project_with_code: Path):
        """Should return correct line numbers for markers."""
        src_dir = project_with_code / "src"
        markers = find_trace_markers([src_dir])

        # Verify line numbers point to actual trace markers
        for marker in markers:
            content = marker.file_path.read_text()
            lines = content.split("\n")
            line = lines[marker.line_number - 1]
            assert "@trace" in line

    def test_searches_multiple_directories(self, project_with_code: Path):
        """Should search multiple directories."""
        src_dir = project_with_code / "src"
        tests_dir = project_with_code / "tests"

        markers = find_trace_markers([src_dir, tests_dir])

        # Should have markers from both src and tests
        src_markers = [m for m in markers if "src" in str(m.file_path)]
        test_markers = [m for m in markers if "tests" in str(m.file_path)]

        assert len(src_markers) > 0
        assert len(test_markers) > 0


class TestGenerateCoverageReport:
    """Tests for generate_coverage_report function."""

    def test_generates_coverage_for_project(self, project_with_code: Path):
        """Should generate coverage report with specs and traces."""
        coverage = generate_coverage_report(project_with_code)

        assert len(coverage) >= 3

        # Find coverage for SPEC-01.01
        cov_01_01 = next(
            (c for c in coverage if c.spec.spec_id == "SPEC-01.01"), None
        )
        assert cov_01_01 is not None
        assert cov_01_01.trace_count > 0  # Has traces in code and tests

    def test_coverage_includes_test_locations(self, project_with_code: Path):
        """Should include test file locations in coverage."""
        coverage = generate_coverage_report(project_with_code)

        # Find coverage with test traces
        has_tests = any(c.test_count > 0 for c in coverage)
        assert has_tests


class TestFormatCoverageReport:
    """Tests for format_coverage_report function."""

    def test_formats_as_text(self, project_with_code: Path):
        """Should format coverage as readable text."""
        coverage = generate_coverage_report(project_with_code)
        report = format_coverage_report(coverage, project_with_code)

        assert "Spec Coverage Report" in report
        assert "Summary:" in report
        assert "SPEC-01" in report

    def test_includes_status_indicators(self, project_with_code: Path):
        """Should include status indicators [x], [!], [ ]."""
        coverage = generate_coverage_report(project_with_code)
        report = format_coverage_report(coverage, project_with_code)

        # Should have some indicator
        assert "[" in report and "]" in report


class TestPropertyBasedTraceability:
    """Property-based tests for traceability functions."""

    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=20)
    def test_spec_parsing_preserves_all_specs(
        self, spec_ids: list[tuple[int, int]]
    ):
        """All specs in a file should be found by parsing."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate spec content
            lines = ["# Test Spec\n"]
            for section, paragraph in spec_ids:
                lines.append(f"[SPEC-{section:02d}.{paragraph:02d}] Test requirement\n")

            spec_file = Path(tmpdir) / "test_spec.md"
            spec_file.write_text("\n".join(lines))

            parsed = parse_specs_from_file(spec_file)

            # All input specs should be found
            for section, paragraph in spec_ids:
                expected_id = f"SPEC-{section:02d}.{paragraph:02d}"
                assert any(
                    s.spec_id == expected_id for s in parsed
                ), f"Missing {expected_id}"

    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=20),
                st.integers(min_value=1, max_value=20),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=10)
    def test_trace_finding_finds_all_markers(
        self, trace_ids: list[tuple[int, int]]
    ):
        """All @trace markers in code should be found."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir(exist_ok=True)

            # Generate code with traces
            lines = ["# Test code\n"]
            for section, paragraph in trace_ids:
                lines.append(f"# @trace SPEC-{section:02d}.{paragraph:02d}\n")
                lines.append(f"def func_{section}_{paragraph}(): pass\n")

            code_file = src_dir / "test_code.py"
            code_file.write_text("\n".join(lines))

            markers = find_trace_markers([src_dir])

            # All traces should be found
            for section, paragraph in trace_ids:
                expected_id = f"SPEC-{section:02d}.{paragraph:02d}"
                assert any(
                    m.spec_id == expected_id for m in markers
                ), f"Missing trace {expected_id}"
