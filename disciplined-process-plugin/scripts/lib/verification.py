"""
Goal-backward verification for disciplined-process.

Verifies that work achieves its intended goal, not just that tasks were completed.

@trace SPEC-05
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class VerificationLevel(Enum):
    """Levels of verification depth."""

    TRUTHS = "truths"
    ARTIFACTS = "artifacts"
    LINKS = "links"


class VerificationStatus(Enum):
    """Outcome of verification."""

    VERIFIED = "verified"  # All checks pass
    INCOMPLETE = "incomplete"  # Some checks not yet satisfied
    FAILED = "failed"  # Verification errors occurred


@dataclass
class TruthResult:
    """Result of verifying a truth (observable behavior)."""

    description: str
    status: str  # "ok", "fail", "?"


@dataclass
class ArtifactResult:
    """Result of verifying an artifact exists with substance."""

    path: Path
    exists: bool
    is_substantive: bool = True
    is_stub: bool = False
    line_count: int = 0
    details: str = ""


@dataclass
class LinkResult:
    """Result of verifying a key link between artifacts."""

    from_path: Path
    to_path: Path
    link_type: str  # "import", "call", "route", "query"
    is_connected: bool
    details: str = ""


@dataclass
class VerificationResult:
    """Complete verification result for a task."""

    task_id: str
    status: VerificationStatus
    truths: list[TruthResult] = field(default_factory=list)
    artifacts: list[ArtifactResult] = field(default_factory=list)
    links: list[LinkResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# @trace SPEC-05.10, SPEC-05.11
def extract_truths_from_description(description: str) -> list[str]:
    """
    Extract truths (acceptance criteria) from task description.

    Looks for:
    - "Acceptance Criteria:" followed by bullet points
    - "@must_have:" sections with "truth:" fields
    - "Success Criteria:" sections
    """
    truths: list[str] = []

    # Pattern 1: Acceptance Criteria bullet points
    ac_match = re.search(
        r"Acceptance\s+Criteria:\s*\n((?:\s*[-*]\s*.+\n?)+)",
        description,
        re.IGNORECASE,
    )
    if ac_match:
        bullets = ac_match.group(1)
        for line in bullets.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*")):
                truth = line.lstrip("-* ").strip()
                if truth:
                    truths.append(truth)

    # Pattern 2: @must_have truth: fields
    must_have_truths = re.findall(
        r"truth:\s*(.+?)(?:\n|$)",
        description,
        re.IGNORECASE,
    )
    truths.extend([t.strip() for t in must_have_truths if t.strip()])

    # Pattern 3: Success Criteria
    sc_match = re.search(
        r"Success\s+Criteria:\s*\n((?:\s*[-*]\s*.+\n?)+)",
        description,
        re.IGNORECASE,
    )
    if sc_match:
        bullets = sc_match.group(1)
        for line in bullets.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*")):
                truth = line.lstrip("-* ").strip()
                if truth and truth not in truths:
                    truths.append(truth)

    return truths


# @trace SPEC-05.20
def check_artifact_exists(path: Path) -> ArtifactResult:
    """Check if an artifact file exists."""
    exists = path.exists() and path.is_file()
    return ArtifactResult(
        path=path,
        exists=exists,
        is_substantive=False if not exists else True,
        line_count=0 if not exists else len(path.read_text().splitlines()),
    )


# @trace SPEC-05.21
def check_artifact_substance(path: Path) -> ArtifactResult:
    """Check if artifact has substantive implementation (not a stub)."""
    if not path.exists():
        return ArtifactResult(
            path=path, exists=False, is_substantive=False, is_stub=False
        )

    content = path.read_text()
    lines = content.splitlines()
    line_count = len(lines)
    is_stub = detect_stub(path)

    return ArtifactResult(
        path=path,
        exists=True,
        is_substantive=not is_stub,
        is_stub=is_stub,
        line_count=line_count,
    )


# @trace SPEC-05.22
def detect_stub(path: Path, threshold_lines: int = 10) -> bool:
    """
    Detect if a file is a stub/placeholder implementation.

    Checks for:
    - Files with only TODO/FIXME/pass statements
    - NotImplementedError patterns
    - Placeholder component text
    - Very short files (under threshold) with no real content
    """
    if not path.exists():
        return False

    content = path.read_text()
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # Filter out empty lines and comments for analysis
    code_lines = [
        l
        for l in lines
        if not l.startswith("#") and not l.startswith("//") and not l.startswith("*")
    ]

    # Check for actual function/class definitions with bodies
    has_definitions = bool(re.search(
        r"(?:def|function|class|const|let|var)\s+\w+.*(?::|=>|{)",
        content
    ))
    has_return_statements = bool(re.search(r"\breturn\b", content))

    # Check line threshold - but allow files with real definitions
    if len(code_lines) < threshold_lines:
        # Allow small files that have actual definitions and returns
        if has_definitions and has_return_statements:
            # Further check: are returns meaningful (not just pass/None/TODO)?
            meaningful_returns = re.findall(r"return\s+(.+)", content)
            has_meaningful_return = any(
                r.strip() not in ("None", "pass", "...", "")
                and "NotImplemented" not in r
                and "TODO" not in r.upper()
                and "PLACEHOLDER" not in r.upper()
                for r in meaningful_returns
            )
            if has_meaningful_return:
                return False

        # Check for any meaningful content
        has_meaningful_content = any(
            len(l) > 15 and "todo" not in l.lower() and "pass" not in l.lower()
            for l in code_lines
        )
        if not has_meaningful_content:
            return True

    # Stub patterns
    stub_patterns = [
        r"^\s*pass\s*$",
        r"^\s*\.\.\.\s*$",  # Python ellipsis
        r"raise\s+NotImplementedError",
        r'throw\s+new\s+Error\s*\(\s*["\']Not\s+implemented',
        r"TODO:\s*implement",
        r"FIXME:\s*implement",
        r">\s*TODO",  # JSX placeholder with space
        r">TODO",  # JSX placeholder without space
        r">\s*PLACEHOLDER",
        r">\s*Coming soon",
    ]

    # Count stub indicators
    stub_count = 0
    for pattern in stub_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        stub_count += len(matches)

    # If majority of non-trivial lines are stubs, it's a stub file
    non_trivial_lines = len([l for l in code_lines if len(l) > 5])
    if non_trivial_lines > 0 and stub_count / max(non_trivial_lines, 1) > 0.3:
        return True

    # Check for placeholder-only content
    placeholder_patterns = [
        r"^(?:export\s+)?(?:function|const|class)\s+\w+.*\{\s*(?:return\s+)?(?:<div>|<>)?\s*(?:TODO|PLACEHOLDER|Coming soon)",
    ]
    for pattern in placeholder_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return True

    return False


# @trace SPEC-05.30, SPEC-05.31
def check_link(
    from_artifact: Path,
    to_artifact: Path,
    link_type: str,
    search_root: Path,
    expected_symbol: str | None = None,
) -> LinkResult:
    """
    Check if a link exists between two artifacts.

    Args:
        from_artifact: Source file (the one being imported/called)
        to_artifact: Target file (the one doing the importing/calling)
        link_type: Type of link ("import", "call", "route")
        search_root: Root directory for relative path resolution
        expected_symbol: Specific symbol to look for (optional)
    """
    if not to_artifact.exists():
        return LinkResult(
            from_path=from_artifact,
            to_path=to_artifact,
            link_type=link_type,
            is_connected=False,
            details="Target file does not exist",
        )

    content = to_artifact.read_text()

    # Get the module/component name from the source
    source_name = from_artifact.stem

    if link_type == "import":
        # If expected_symbol is provided, we need to verify that specific symbol is imported
        if expected_symbol:
            # Check if the specific symbol appears in an import statement
            symbol_import_patterns = [
                # Python: from X import symbol or from X import a, symbol, b
                rf"from\s+{source_name}\s+import\s+[^#\n]*\b{expected_symbol}\b",
                # JS/TS: import { symbol } from or import { a, symbol } from
                rf"import\s+\{{[^}}]*\b{expected_symbol}\b[^}}]*\}}\s+from",
                # Default import: import symbol from
                rf"import\s+{expected_symbol}\s+from",
            ]

            for pattern in symbol_import_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return LinkResult(
                        from_path=from_artifact,
                        to_path=to_artifact,
                        link_type=link_type,
                        is_connected=True,
                        details=f"Found import of {expected_symbol}",
                    )

            return LinkResult(
                from_path=from_artifact,
                to_path=to_artifact,
                link_type=link_type,
                is_connected=False,
                details=f"Symbol {expected_symbol} not imported from {source_name}",
            )

        # No specific symbol - just check if module is imported at all
        import_patterns = [
            # Python: from X import Y or import X
            rf"from\s+['\"]?\.?/?{source_name}['\"]?\s+import",
            rf"import\s+['\"]?\.?/?{source_name}['\"]?",
            # JS/TS: import { X } from './Y' or import X from './Y'
            rf"import\s+.*from\s+['\"]\.?/?{source_name}['\"]",
            rf"import\s+{source_name}\s+from",
            # require
            rf"require\s*\(\s*['\"]\.?/?{source_name}['\"]",
        ]

        for pattern in import_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return LinkResult(
                    from_path=from_artifact,
                    to_path=to_artifact,
                    link_type=link_type,
                    is_connected=True,
                    details=f"Found import of {source_name}",
                )

    return LinkResult(
        from_path=from_artifact,
        to_path=to_artifact,
        link_type=link_type,
        is_connected=False,
        details=f"No {link_type} of {source_name} found in {to_artifact.name}",
    )


# @trace SPEC-05.40, SPEC-05.41
def verify_task(
    task: dict[str, Any],
    project_root: Path,
    artifact_patterns: list[str] | None = None,
) -> VerificationResult:
    """
    Verify a task achieved its goal using goal-backward verification.

    Args:
        task: Task dict with id, title, description
        project_root: Project root directory
        artifact_patterns: Glob patterns for artifact discovery

    Returns:
        VerificationResult with truths, artifacts, links checked
    """
    task_id = task.get("id", "unknown")
    description = task.get("description", "")
    errors: list[str] = []

    # Extract truths from description
    truth_strings = extract_truths_from_description(description)
    truths: list[TruthResult] = []

    for truth_str in truth_strings:
        # For now, mark as needing human verification
        # Future: could attempt automated verification for some patterns
        truths.append(TruthResult(description=truth_str, status="?"))

    # Extract artifacts from description
    artifact_results: list[ArtifactResult] = []
    artifact_pattern = re.compile(r"Artifacts?:\s*\n((?:\s*[-*]\s*.+\n?)+)", re.IGNORECASE)
    artifact_match = artifact_pattern.search(description)

    if artifact_match:
        bullets = artifact_match.group(1)
        for line in bullets.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*")):
                artifact_path = line.lstrip("-* ").strip()
                if artifact_path:
                    full_path = project_root / artifact_path
                    result = check_artifact_substance(full_path)
                    artifact_results.append(result)

    # Determine overall status
    # @trace SPEC-05.60
    has_failed_truths = any(t.status == "fail" for t in truths)
    has_missing_artifacts = any(not a.exists for a in artifact_results)
    has_stubs = any(a.is_stub for a in artifact_results)
    has_unverified_truths = any(t.status == "?" for t in truths)

    if errors:
        status = VerificationStatus.FAILED
    elif has_failed_truths or has_missing_artifacts:
        status = VerificationStatus.FAILED
    elif has_stubs or has_unverified_truths:
        status = VerificationStatus.INCOMPLETE
    elif len(truths) == 0 and len(artifact_results) == 0:
        # No criteria to verify - consider incomplete
        status = VerificationStatus.INCOMPLETE
    else:
        status = VerificationStatus.VERIFIED

    return VerificationResult(
        task_id=task_id,
        status=status,
        truths=truths,
        artifacts=artifact_results,
        links=[],  # Links would be extracted from must_have key_links
        errors=errors,
    )


def format_verification_result(result: VerificationResult) -> str:
    """Format verification result for display."""
    lines = [f"Verifying: {result.task_id}", ""]

    if result.truths:
        lines.append("Truths:")
        for truth in result.truths:
            status_icon = {"ok": "[ok]", "fail": "[FAIL]", "?": "[?]"}.get(
                truth.status, "[?]"
            )
            lines.append(f"  {status_icon} {truth.description}")
        lines.append("")

    if result.artifacts:
        lines.append("Artifacts:")
        for artifact in result.artifacts:
            if not artifact.exists:
                status = "[FAIL]"
                detail = "missing"
            elif artifact.is_stub:
                status = "[STUB]"
                detail = f"{artifact.line_count} lines, stub detected"
            else:
                status = "[ok]"
                detail = f"{artifact.line_count} lines"
            lines.append(f"  {status} {artifact.path} ({detail})")
        lines.append("")

    if result.links:
        lines.append("Links:")
        for link in result.links:
            status = "[ok]" if link.is_connected else "[FAIL]"
            lines.append(
                f"  {status} {link.from_path.name} -> {link.to_path.name} ({link.link_type})"
            )
        lines.append("")

    if result.errors:
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  - {error}")
        lines.append("")

    lines.append(f"Status: {result.status.value.upper()}")

    return "\n".join(lines)
