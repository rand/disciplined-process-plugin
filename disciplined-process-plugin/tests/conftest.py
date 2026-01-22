"""
Pytest configuration and shared fixtures for disciplined-process-plugin tests.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory with basic structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create basic structure
        (project / "docs" / "spec").mkdir(parents=True)
        (project / "docs" / "adr").mkdir(parents=True)
        (project / "src").mkdir(parents=True)
        (project / "tests").mkdir(parents=True)
        (project / ".claude").mkdir(parents=True)

        yield project


@pytest.fixture
def project_with_specs(temp_project_dir: Path) -> Path:
    """Create a project with sample specs."""
    spec_file = temp_project_dir / "docs" / "spec" / "01-authentication.md"
    spec_file.write_text("""# Authentication
[SPEC-01] <!-- chainlink:1 -->

## Requirements

[SPEC-01.01] User can log in with email/password <!-- chainlink:2 -->

The system shall authenticate users via email and password.

[SPEC-01.02] User can reset password via email <!-- chainlink:3 -->

The system shall send a password reset link valid for 24 hours.

[SPEC-01.03] Session expires after 30 minutes of inactivity

No issue linked to this one.
""")

    return temp_project_dir


@pytest.fixture
def project_with_code(project_with_specs: Path) -> Path:
    """Create a project with traced code."""
    code_file = project_with_specs / "src" / "auth.py"
    code_file.write_text('''"""Authentication module."""

# @trace SPEC-01.01
def authenticate_user(email: str, password: str) -> bool:
    """Authenticate a user."""
    # @trace SPEC-01.01.a - Email validation
    if not email or "@" not in email:
        return False
    return True


# @trace SPEC-01.02
def reset_password(email: str) -> bool:
    """Send password reset email."""
    return True
''')

    test_file = project_with_specs / "tests" / "test_auth.py"
    test_file.write_text('''"""Tests for auth module."""

# @trace SPEC-01.01
def test_authenticate_user():
    """Test user authentication."""
    pass


# @trace SPEC-01.02
def test_reset_password():
    """Test password reset."""
    pass
''')

    return project_with_specs


@pytest.fixture
def config_dict() -> dict[str, Any]:
    """Sample configuration dictionary."""
    return {
        "version": "2.0",
        "project": {
            "name": "test-project",
            "languages": ["python", "typescript"],
        },
        "task_tracker": "beads",
        "enforcement": "guided",
        "adversarial_review": {
            "enabled": True,
            "model": "gemini-2.5-flash",
            "max_iterations": 5,
        },
        "specs": {
            "directory": "docs/spec/",
            "id_format": "SPEC-{section:02d}.{item:02d}",
        },
        "adrs": {
            "directory": "docs/adr/",
        },
    }


@pytest.fixture
def dp_config_file(temp_project_dir: Path, config_dict: dict[str, Any]) -> Path:
    """Create a dp-config.yaml file in the project."""
    import yaml

    config_path = temp_project_dir / ".claude" / "dp-config.yaml"
    config_path.write_text(yaml.dump(config_dict))
    return config_path
