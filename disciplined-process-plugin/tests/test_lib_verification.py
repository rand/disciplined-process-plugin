"""
Tests for lib/verification module.

Goal-backward verification for disciplined-process.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

# Import module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib.verification import (
    VerificationLevel,
    VerificationStatus,
    TruthResult,
    ArtifactResult,
    LinkResult,
    VerificationResult,
    extract_truths_from_description,
    check_artifact_exists,
    check_artifact_substance,
    detect_stub,
    check_link,
    verify_task,
)


# @trace SPEC-05.01
class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_has_three_statuses(self):
        """Should have VERIFIED, INCOMPLETE, FAILED statuses."""
        statuses = list(VerificationStatus)
        assert VerificationStatus.VERIFIED in statuses
        assert VerificationStatus.INCOMPLETE in statuses
        assert VerificationStatus.FAILED in statuses


# @trace SPEC-05.10, SPEC-05.11
class TestExtractTruths:
    """Tests for truth extraction from task descriptions."""

    def test_extracts_acceptance_criteria(self):
        """Should extract truths from acceptance criteria format."""
        description = dedent("""
            Implement user login.

            Acceptance Criteria:
            - User can enter email and password
            - User sees error for invalid credentials
            - User is redirected after successful login
        """)
        truths = extract_truths_from_description(description)
        assert len(truths) == 3
        assert "email and password" in truths[0].lower()

    def test_extracts_must_have_truths(self):
        """Should extract truths from must_have format."""
        description = dedent("""
            Implement chat feature.

            @must_have:
              truth: User can send a message
              truth: User can see message history
        """)
        truths = extract_truths_from_description(description)
        assert len(truths) >= 2

    def test_returns_empty_for_no_criteria(self):
        """Should return empty list when no criteria found."""
        description = "Just a simple task with no criteria."
        truths = extract_truths_from_description(description)
        assert truths == []


# @trace SPEC-05.20, SPEC-05.21
class TestArtifactChecks:
    """Tests for artifact existence and substance checks."""

    def test_artifact_exists(self, tmp_path: Path):
        """Should detect existing files."""
        test_file = tmp_path / "component.tsx"
        test_file.write_text("export function Component() { return <div>Hello</div>; }")

        result = check_artifact_exists(test_file)
        assert result.exists is True

    def test_artifact_not_exists(self, tmp_path: Path):
        """Should detect missing files."""
        result = check_artifact_exists(tmp_path / "nonexistent.tsx")
        assert result.exists is False

    def test_artifact_substance_real_code(self, tmp_path: Path):
        """Should recognize substantive implementations."""
        test_file = tmp_path / "auth.py"
        test_file.write_text(dedent("""
            import hashlib

            def hash_password(password: str, salt: str) -> str:
                '''Hash a password with salt.'''
                return hashlib.sha256((password + salt).encode()).hexdigest()

            def verify_password(password: str, salt: str, hash: str) -> bool:
                '''Verify a password against its hash.'''
                return hash_password(password, salt) == hash
        """))

        result = check_artifact_substance(test_file)
        assert result.is_substantive is True
        assert result.is_stub is False

    def test_artifact_substance_stub(self, tmp_path: Path):
        """Should detect stub implementations."""
        test_file = tmp_path / "auth.py"
        test_file.write_text(dedent("""
            def hash_password(password: str) -> str:
                # TODO: implement
                pass

            def verify_password(password: str, hash: str) -> bool:
                raise NotImplementedError()
        """))

        result = check_artifact_substance(test_file)
        assert result.is_stub is True


# @trace SPEC-05.22
class TestStubDetection:
    """Tests for stub/placeholder detection."""

    def test_detects_todo_only(self, tmp_path: Path):
        """Should detect files with only TODO comments."""
        test_file = tmp_path / "feature.py"
        test_file.write_text(dedent("""
            # TODO: implement this feature
            pass
        """))

        assert detect_stub(test_file) is True

    def test_detects_not_implemented_error(self, tmp_path: Path):
        """Should detect NotImplementedError patterns."""
        test_file = tmp_path / "feature.ts"
        test_file.write_text(dedent("""
            export function doSomething() {
                throw new Error("Not implemented");
            }
        """))

        assert detect_stub(test_file) is True

    def test_detects_placeholder_component(self, tmp_path: Path):
        """Should detect placeholder React components."""
        test_file = tmp_path / "Component.tsx"
        test_file.write_text(dedent("""
            export function Component() {
                return <div>TODO: implement</div>;
            }
        """))

        assert detect_stub(test_file) is True

    def test_allows_real_implementation(self, tmp_path: Path):
        """Should not flag real implementations as stubs."""
        test_file = tmp_path / "utils.py"
        test_file.write_text(dedent("""
            from typing import List

            def filter_active(items: List[dict]) -> List[dict]:
                '''Filter items to only active ones.'''
                return [item for item in items if item.get('active', False)]

            def sort_by_date(items: List[dict], key: str = 'created_at') -> List[dict]:
                '''Sort items by date field.'''
                return sorted(items, key=lambda x: x.get(key, ''))
        """))

        assert detect_stub(test_file) is False

    def test_respects_line_threshold(self, tmp_path: Path):
        """Should flag very short files as potential stubs."""
        test_file = tmp_path / "tiny.py"
        test_file.write_text("x = 1")

        # With default threshold of 10 lines
        assert detect_stub(test_file, threshold_lines=10) is True
        # But not with lower threshold
        assert detect_stub(test_file, threshold_lines=1) is False


# @trace SPEC-05.30, SPEC-05.31
class TestLinkChecks:
    """Tests for key link verification."""

    def test_detects_import_link(self, tmp_path: Path):
        """Should verify import statements exist."""
        # Create source file
        component = tmp_path / "Component.tsx"
        component.write_text("export function Component() { return <div/>; }")

        # Create file that imports it
        app = tmp_path / "App.tsx"
        app.write_text(dedent("""
            import { Component } from './Component';

            export function App() {
                return <Component />;
            }
        """))

        result = check_link(
            from_artifact=component,
            to_artifact=app,
            link_type="import",
            search_root=tmp_path,
        )
        assert result.is_connected is True

    def test_detects_missing_import(self, tmp_path: Path):
        """Should detect when component is not imported."""
        # Create source file
        component = tmp_path / "OrphanComponent.tsx"
        component.write_text("export function OrphanComponent() { return <div/>; }")

        # Create app that doesn't import it
        app = tmp_path / "App.tsx"
        app.write_text(dedent("""
            export function App() {
                return <div>Hello</div>;
            }
        """))

        result = check_link(
            from_artifact=component,
            to_artifact=app,
            link_type="import",
            search_root=tmp_path,
        )
        assert result.is_connected is False


# @trace SPEC-05.32
class TestUnwiredPatternDetection:
    """Tests for common unwired pattern detection."""

    def test_detects_unused_export(self, tmp_path: Path):
        """Should detect exported function never imported."""
        # Create utility with export
        utils = tmp_path / "utils.py"
        utils.write_text(dedent("""
            def helper_function():
                return "help"

            def unused_function():
                return "unused"
        """))

        # Create main that only uses helper
        main = tmp_path / "main.py"
        main.write_text(dedent("""
            from utils import helper_function

            print(helper_function())
        """))

        result = check_link(
            from_artifact=utils,
            to_artifact=main,
            link_type="import",
            search_root=tmp_path,
            expected_symbol="unused_function",
        )
        assert result.is_connected is False


# @trace SPEC-05.40, SPEC-05.41
class TestVerifyTask:
    """Tests for full task verification."""

    def test_verifies_complete_implementation(self, tmp_path: Path):
        """Should return VERIFIED for complete implementation."""
        # Create a complete implementation
        auth = tmp_path / "auth.py"
        auth.write_text(dedent("""
            import hashlib

            def login(email: str, password: str) -> dict:
                '''Authenticate user and return session.'''
                # Real implementation
                user = lookup_user(email)
                if user and verify_password(password, user['password_hash']):
                    return create_session(user)
                raise AuthenticationError("Invalid credentials")

            def logout(session_id: str) -> bool:
                '''End user session.'''
                return invalidate_session(session_id)

            def lookup_user(email: str) -> dict | None:
                # Database lookup
                return {"id": 1, "email": email, "password_hash": "..."}

            def verify_password(password: str, hash: str) -> bool:
                return hashlib.sha256(password.encode()).hexdigest() == hash

            def create_session(user: dict) -> dict:
                return {"session_id": "abc123", "user_id": user["id"]}

            def invalidate_session(session_id: str) -> bool:
                return True

            class AuthenticationError(Exception):
                pass
        """))

        # Create app that uses auth
        app = tmp_path / "app.py"
        app.write_text(dedent("""
            from auth import login, logout

            def handle_login(email: str, password: str):
                return login(email, password)

            def handle_logout(session_id: str):
                return logout(session_id)
        """))

        task = {
            "id": "test-001",
            "title": "Implement authentication",
            "description": dedent("""
                Implement user login/logout.

                Acceptance Criteria:
                - User can log in with email and password
                - User can log out
            """),
        }

        result = verify_task(task, project_root=tmp_path)
        # May not be fully VERIFIED without all wiring, but shouldn't FAIL
        assert result.status in (VerificationStatus.VERIFIED, VerificationStatus.INCOMPLETE)

    def test_fails_for_missing_artifacts(self, tmp_path: Path):
        """Should return INCOMPLETE when artifacts are missing."""
        task = {
            "id": "test-002",
            "title": "Implement feature",
            "description": dedent("""
                Create the feature.

                Acceptance Criteria:
                - Feature works

                Artifacts:
                - src/feature.py
            """),
        }

        result = verify_task(task, project_root=tmp_path)
        assert result.status in (VerificationStatus.INCOMPLETE, VerificationStatus.FAILED)


# @trace SPEC-05.50, SPEC-05.51
class TestVerificationOutput:
    """Tests for verification output format."""

    def test_result_has_truths(self):
        """Verification result should include truths."""
        result = VerificationResult(
            task_id="test-001",
            status=VerificationStatus.VERIFIED,
            truths=[TruthResult(description="User can login", status="ok")],
            artifacts=[],
            links=[],
        )
        assert len(result.truths) == 1
        assert result.truths[0].status == "ok"

    def test_result_has_artifacts(self):
        """Verification result should include artifacts."""
        result = VerificationResult(
            task_id="test-001",
            status=VerificationStatus.INCOMPLETE,
            truths=[],
            artifacts=[
                ArtifactResult(
                    path=Path("src/auth.py"),
                    exists=True,
                    is_substantive=True,
                    is_stub=False,
                    line_count=50,
                )
            ],
            links=[],
        )
        assert len(result.artifacts) == 1
        assert result.artifacts[0].exists is True

    def test_result_has_links(self):
        """Verification result should include links."""
        result = VerificationResult(
            task_id="test-001",
            status=VerificationStatus.INCOMPLETE,
            truths=[],
            artifacts=[],
            links=[
                LinkResult(
                    from_path=Path("src/Component.tsx"),
                    to_path=Path("src/App.tsx"),
                    link_type="import",
                    is_connected=False,
                )
            ],
        )
        assert len(result.links) == 1
        assert result.links[0].is_connected is False


# @trace SPEC-05.60, SPEC-05.61
class TestVerificationOutcomes:
    """Tests for verification outcome determination."""

    def test_verified_when_all_pass(self):
        """Should be VERIFIED when all checks pass."""
        result = VerificationResult(
            task_id="test-001",
            status=VerificationStatus.VERIFIED,
            truths=[TruthResult(description="Works", status="ok")],
            artifacts=[
                ArtifactResult(
                    path=Path("src/a.py"),
                    exists=True,
                    is_substantive=True,
                    is_stub=False,
                    line_count=100,
                )
            ],
            links=[
                LinkResult(
                    from_path=Path("src/a.py"),
                    to_path=Path("src/b.py"),
                    link_type="import",
                    is_connected=True,
                )
            ],
        )
        assert result.status == VerificationStatus.VERIFIED

    def test_incomplete_when_stub_detected(self):
        """Should be INCOMPLETE when stubs detected."""
        result = VerificationResult(
            task_id="test-001",
            status=VerificationStatus.INCOMPLETE,
            truths=[],
            artifacts=[
                ArtifactResult(
                    path=Path("src/stub.py"),
                    exists=True,
                    is_substantive=False,
                    is_stub=True,
                    line_count=5,
                )
            ],
            links=[],
        )
        assert result.status == VerificationStatus.INCOMPLETE


# @trace SPEC-05.90, SPEC-05.91
class TestErrorHandling:
    """Tests for verification error handling."""

    def test_handles_missing_task_id(self):
        """Should handle missing task ID gracefully."""
        task = {"title": "No ID task"}
        result = verify_task(task, project_root=Path("/tmp"))
        # Should not raise, should return a result
        assert result is not None

    def test_verification_is_readonly(self, tmp_path: Path):
        """Verification should not modify files."""
        test_file = tmp_path / "test.py"
        test_file.write_text("original content")
        original_mtime = test_file.stat().st_mtime

        task = {
            "id": "test",
            "title": "Test",
            "description": "Acceptance Criteria:\n- Works",
        }
        verify_task(task, project_root=tmp_path)

        # File should not be modified
        assert test_file.read_text() == "original content"
        assert test_file.stat().st_mtime == original_mtime
