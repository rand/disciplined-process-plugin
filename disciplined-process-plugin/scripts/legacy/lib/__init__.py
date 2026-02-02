"""
Disciplined Process Plugin - Python utilities library.

This package provides shared utilities for the Python-based hooks.
"""

from .config import (
    DPConfig,
    ConfigVersion,
    EnforcementLevel,
    TaskTracker,
    DegradationAction,
    get_config,
    reload_config,
    migrate_v1_to_v2,
)
from .providers import (
    ProviderStatus,
    check_cli_available,
    check_provider_available,
    get_project_dir,
    get_ready_count,
    sync_tracker,
    feedback,
    error,
    output,
    handle_degradation,
)
from .degradation import (
    DegradationLevel,
    HealthStatus,
    SystemState,
    run_health_checks,
    get_current_level,
    is_feature_available,
    lock_level,
    unlock_level,
    reset_to_full,
    get_status_report,
)

__all__ = [
    # Config
    "DPConfig",
    "ConfigVersion",
    "EnforcementLevel",
    "TaskTracker",
    "DegradationAction",
    "get_config",
    "reload_config",
    "migrate_v1_to_v2",
    # Providers
    "ProviderStatus",
    "check_cli_available",
    "check_provider_available",
    "get_project_dir",
    "get_ready_count",
    "sync_tracker",
    "feedback",
    "error",
    "output",
    "handle_degradation",
    # Degradation
    "DegradationLevel",
    "HealthStatus",
    "SystemState",
    "run_health_checks",
    "get_current_level",
    "is_feature_available",
    "lock_level",
    "unlock_level",
    "reset_to_full",
    "get_status_report",
]
