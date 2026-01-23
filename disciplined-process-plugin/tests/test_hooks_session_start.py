"""
Tests for session_start.py hook.

@trace SPEC-01.90
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRunStartupHealthCheck:
    """Test startup health check function."""

    def test_returns_level_from_health_checks(self):
        """Should return degradation level from health checks."""
        import sys

        sys.path.insert(0, "scripts")
        from lib.degradation import DegradationLevel

        with patch("scripts.session_start.run_health_checks") as mock:
            mock_state = MagicMock()
            mock_state.level = DegradationLevel.FULL
            mock.return_value = mock_state

            from scripts.session_start import run_startup_health_check

            level = run_startup_health_check()
            assert level == DegradationLevel.FULL

    def test_returns_full_on_exception(self):
        """Should return FULL level on exception."""
        import sys

        sys.path.insert(0, "scripts")
        from lib.degradation import DegradationLevel

        with patch("scripts.session_start.run_health_checks") as mock:
            mock.side_effect = Exception("Health check failed")

            from scripts.session_start import run_startup_health_check

            level = run_startup_health_check()
            assert level == DegradationLevel.FULL


class TestShowDegradationStatus:
    """Test degradation status display."""

    def test_no_output_for_full_level(self):
        """Should not output anything for FULL level."""
        import sys

        sys.path.insert(0, "scripts")
        from lib.degradation import DegradationLevel

        with patch("scripts.session_start.feedback") as mock_feedback:
            from scripts.session_start import show_degradation_status

            show_degradation_status(DegradationLevel.FULL)
            mock_feedback.assert_not_called()

    def test_shows_message_for_reduced_level(self):
        """Should show warning for REDUCED level."""
        import sys

        sys.path.insert(0, "scripts")
        from lib.degradation import DegradationLevel

        with patch("scripts.session_start.feedback") as mock_feedback:
            from scripts.session_start import show_degradation_status

            show_degradation_status(DegradationLevel.REDUCED)
            mock_feedback.assert_called_once()
            call_arg = mock_feedback.call_args[0][0]
            assert "reduced mode" in call_arg.lower()


class TestShowReadyWork:
    """Test ready work display."""

    def test_skips_in_safe_mode(self):
        """Should skip showing work in safe mode."""
        import sys

        sys.path.insert(0, "scripts")
        from lib.config import DPConfig
        from lib.degradation import DegradationLevel

        config = DPConfig()

        with patch("scripts.session_start.get_project_dir") as mock_dir:
            with patch("scripts.session_start.check_provider_available") as mock_check:
                from scripts.session_start import show_ready_work

                show_ready_work(config, DegradationLevel.SAFE)

                # Should not even check provider
                mock_check.assert_not_called()

    def test_skips_for_none_tracker(self):
        """Should skip if tracker is NONE."""
        import sys

        sys.path.insert(0, "scripts")
        from lib.config import DPConfig, TaskTracker
        from lib.degradation import DegradationLevel

        config = DPConfig()
        config.task_tracker = TaskTracker.NONE

        with patch("scripts.session_start.get_project_dir") as mock_dir:
            mock_dir.return_value = Path(".")
            with patch("scripts.session_start.check_provider_available") as mock_check:
                mock_status = MagicMock()
                mock_status.available = True
                mock_check.return_value = mock_status

                with patch("scripts.session_start.get_ready_count") as mock_count:
                    from scripts.session_start import show_ready_work

                    show_ready_work(config, DegradationLevel.FULL)

                    # Should not get ready count for NONE
                    mock_count.assert_not_called()


class TestMain:
    """Test main entry point."""

    def test_main_returns_zero_on_success(self):
        """Main should return 0 on success."""
        import sys

        sys.path.insert(0, "scripts")
        from lib.degradation import DegradationLevel

        with patch("scripts.session_start.run_startup_health_check") as mock_health:
            mock_health.return_value = DegradationLevel.FULL
            with patch("scripts.session_start.get_config") as mock_config:
                mock_config.return_value = MagicMock()
                with patch("scripts.session_start.get_project_dir") as mock_dir:
                    mock_dir.return_value = Path(".")
                    with patch(
                        "scripts.session_start.show_chainlink_session_context"
                    ):
                        with patch("scripts.session_start.show_ready_work"):
                            from scripts.session_start import main

                            result = main()
                            assert result == 0

    def test_main_returns_zero_on_exception(self):
        """Main should return 0 even on exception (graceful degradation)."""
        import sys

        sys.path.insert(0, "scripts")

        with patch("scripts.session_start.run_startup_health_check") as mock:
            mock.side_effect = Exception("Test error")
            with patch("scripts.session_start.feedback"):
                from scripts.session_start import main

                result = main()
                assert result == 0  # Should not crash
