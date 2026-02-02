"""
Graceful Degradation Framework for disciplined-process.

Implements 5-level degradation with health checks and auto-repair:
- Full: All features working normally
- Reduced: Non-critical features disabled
- Manual: Requires manual intervention for some operations
- Safe: Minimal safe operation mode
- Recovery: Actively attempting to repair issues
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable

from .config import DPConfig, DegradationAction, TaskTracker, get_config
from .providers import check_cli_available, check_provider_available, feedback, get_project_dir


class DegradationLevel(Enum):
    """Degradation levels from most to least capable."""

    FULL = auto()  # All features working
    REDUCED = auto()  # Non-critical features disabled
    MANUAL = auto()  # Manual intervention required
    SAFE = auto()  # Minimal safe operation
    RECOVERY = auto()  # Attempting repair


@dataclass
class HealthStatus:
    """Health status of a component."""

    healthy: bool
    component: str
    message: str
    last_check: datetime = field(default_factory=datetime.now)
    recovery_attempted: bool = False
    recovery_succeeded: bool = False


@dataclass
class SystemState:
    """Overall system state."""

    level: DegradationLevel
    components: dict[str, HealthStatus] = field(default_factory=dict)
    last_transition: datetime = field(default_factory=datetime.now)
    transition_reason: str = ""
    locked: bool = False
    lock_reason: str = ""


# State file for persistence
def get_state_file() -> Path:
    """Get the path to the degradation state file."""
    return get_project_dir() / ".claude" / ".dp-degradation-state.json"


def load_state() -> SystemState:
    """Load system state from file or return default."""
    state_file = get_state_file()

    if state_file.exists():
        try:
            with open(state_file) as f:
                data = json.load(f)
            return _deserialize_state(data)
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    return SystemState(level=DegradationLevel.FULL)


def save_state(state: SystemState) -> None:
    """Save system state to file."""
    state_file = get_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)

    with open(state_file, "w") as f:
        json.dump(_serialize_state(state), f, indent=2)


def _serialize_state(state: SystemState) -> dict[str, Any]:
    """Serialize state to JSON-compatible dict."""
    return {
        "level": state.level.name,
        "last_transition": state.last_transition.isoformat(),
        "transition_reason": state.transition_reason,
        "locked": state.locked,
        "lock_reason": state.lock_reason,
        "components": {
            name: {
                "healthy": status.healthy,
                "component": status.component,
                "message": status.message,
                "last_check": status.last_check.isoformat(),
                "recovery_attempted": status.recovery_attempted,
                "recovery_succeeded": status.recovery_succeeded,
            }
            for name, status in state.components.items()
        },
    }


def _deserialize_state(data: dict[str, Any]) -> SystemState:
    """Deserialize state from JSON dict."""
    components = {}
    for name, comp_data in data.get("components", {}).items():
        components[name] = HealthStatus(
            healthy=comp_data["healthy"],
            component=comp_data["component"],
            message=comp_data["message"],
            last_check=datetime.fromisoformat(comp_data["last_check"]),
            recovery_attempted=comp_data.get("recovery_attempted", False),
            recovery_succeeded=comp_data.get("recovery_succeeded", False),
        )

    return SystemState(
        level=DegradationLevel[data["level"]],
        components=components,
        last_transition=datetime.fromisoformat(data["last_transition"]),
        transition_reason=data.get("transition_reason", ""),
        locked=data.get("locked", False),
        lock_reason=data.get("lock_reason", ""),
    )


# Health Checks


def check_task_tracker_health(config: DPConfig) -> HealthStatus:
    """Check if task tracker is healthy."""
    tracker = config.task_tracker
    project_dir = get_project_dir()

    status = check_provider_available(tracker, project_dir)

    return HealthStatus(
        healthy=status.available,
        component="task_tracker",
        message=status.reason or f"{tracker.value} is healthy",
    )


def check_git_health() -> HealthStatus:
    """Check if git is healthy."""
    project_dir = get_project_dir()

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_dir,
        )
        if result.returncode == 0:
            return HealthStatus(
                healthy=True,
                component="git",
                message="Git repository is healthy",
            )
        else:
            return HealthStatus(
                healthy=False,
                component="git",
                message=f"Git error: {result.stderr.strip()}",
            )
    except subprocess.TimeoutExpired:
        return HealthStatus(
            healthy=False,
            component="git",
            message="Git command timed out",
        )
    except FileNotFoundError:
        return HealthStatus(
            healthy=False,
            component="git",
            message="Git not found",
        )


def check_config_health() -> HealthStatus:
    """Check if config is healthy."""
    try:
        config = get_config()
        return HealthStatus(
            healthy=True,
            component="config",
            message="Configuration loaded successfully",
        )
    except Exception as e:
        return HealthStatus(
            healthy=False,
            component="config",
            message=f"Config error: {e}",
        )


def check_beads_daemon_health() -> HealthStatus:
    """Check if beads daemon is healthy (if beads is the tracker)."""
    try:
        config = get_config()
        if config.task_tracker not in (TaskTracker.BEADS, TaskTracker.CHAINLINK):
            return HealthStatus(
                healthy=True,
                component="beads_daemon",
                message="Beads daemon not applicable",
            )

        if not check_cli_available("bd"):
            return HealthStatus(
                healthy=False,
                component="beads_daemon",
                message="bd CLI not available",
            )

        result = subprocess.run(
            ["bd", "daemon", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 or "running" in result.stdout.lower():
            return HealthStatus(
                healthy=True,
                component="beads_daemon",
                message="Beads daemon is running",
            )
        else:
            return HealthStatus(
                healthy=False,
                component="beads_daemon",
                message="Beads daemon not running",
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        return HealthStatus(
            healthy=False,
            component="beads_daemon",
            message=f"Daemon check failed: {e}",
        )


# Recovery Actions


def attempt_recovery(component: str, state: SystemState) -> bool:
    """Attempt to recover a component."""
    recovery_actions: dict[str, Callable[[], bool]] = {
        "task_tracker": _recover_task_tracker,
        "git": _recover_git,
        "config": _recover_config,
        "beads_daemon": _recover_beads_daemon,
    }

    if component not in recovery_actions:
        return False

    try:
        return recovery_actions[component]()
    except Exception:
        return False


def _recover_task_tracker() -> bool:
    """Attempt to recover task tracker."""
    config = get_config()
    project_dir = get_project_dir()

    if config.task_tracker == TaskTracker.BEADS:
        beads_dir = project_dir / ".beads"
        if not beads_dir.exists():
            try:
                subprocess.run(
                    ["bd", "init"],
                    capture_output=True,
                    timeout=30,
                    cwd=project_dir,
                )
                return (project_dir / ".beads").exists()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False

    return True


def _recover_git() -> bool:
    """Attempt to recover git state."""
    # Git recovery is limited - mostly just checking if we can access it
    project_dir = get_project_dir()

    try:
        result = subprocess.run(
            ["git", "status"],
            capture_output=True,
            timeout=5,
            cwd=project_dir,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _recover_config() -> bool:
    """Attempt to recover config."""
    # Config recovery: try to reload
    try:
        from .config import reload_config
        reload_config()
        return True
    except Exception:
        return False


def _recover_beads_daemon() -> bool:
    """Attempt to recover beads daemon."""
    try:
        # Try to start the daemon
        result = subprocess.run(
            ["bd", "daemon", "start"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# State Transitions


def compute_degradation_level(components: dict[str, HealthStatus]) -> DegradationLevel:
    """Compute the appropriate degradation level based on component health."""
    unhealthy = [c for c in components.values() if not c.healthy]

    if not unhealthy:
        return DegradationLevel.FULL

    unhealthy_names = {c.component for c in unhealthy}

    # Critical components
    if "git" in unhealthy_names:
        return DegradationLevel.SAFE

    # Config issues require manual intervention
    if "config" in unhealthy_names:
        return DegradationLevel.MANUAL

    # Task tracker issues -> reduced mode
    if "task_tracker" in unhealthy_names:
        return DegradationLevel.REDUCED

    # Daemon issues -> reduced mode
    if "beads_daemon" in unhealthy_names:
        return DegradationLevel.REDUCED

    return DegradationLevel.FULL


def transition_to(state: SystemState, new_level: DegradationLevel, reason: str) -> SystemState:
    """Transition to a new degradation level."""
    if state.locked:
        return state

    if state.level != new_level:
        state.level = new_level
        state.last_transition = datetime.now()
        state.transition_reason = reason

    return state


# Main Functions


def run_health_checks() -> SystemState:
    """Run all health checks and return updated state."""
    state = load_state()

    try:
        config = get_config()
    except Exception:
        config = DPConfig()

    # Run health checks
    checks = [
        check_config_health(),
        check_git_health(),
        check_task_tracker_health(config),
    ]

    # Add beads daemon check if applicable
    if config.task_tracker in (TaskTracker.BEADS, TaskTracker.CHAINLINK):
        checks.append(check_beads_daemon_health())

    # Update state with check results
    for check in checks:
        state.components[check.component] = check

    # Compute new level
    new_level = compute_degradation_level(state.components)

    # If degrading, attempt recovery first
    if new_level.value > state.level.value:
        unhealthy = [c for c in state.components.values() if not c.healthy]
        for component in unhealthy:
            if not component.recovery_attempted:
                succeeded = attempt_recovery(component.component, state)
                component.recovery_attempted = True
                component.recovery_succeeded = succeeded

                if succeeded:
                    # Re-check the component
                    if component.component == "task_tracker":
                        state.components["task_tracker"] = check_task_tracker_health(config)
                    elif component.component == "git":
                        state.components["git"] = check_git_health()
                    elif component.component == "config":
                        state.components["config"] = check_config_health()
                    elif component.component == "beads_daemon":
                        state.components["beads_daemon"] = check_beads_daemon_health()

        # Recompute level after recovery
        new_level = compute_degradation_level(state.components)

    # Transition
    if new_level != state.level:
        reason = _build_transition_reason(state, new_level)
        state = transition_to(state, new_level, reason)

    save_state(state)
    return state


def _build_transition_reason(state: SystemState, new_level: DegradationLevel) -> str:
    """Build a human-readable transition reason."""
    unhealthy = [c for c in state.components.values() if not c.healthy]

    if new_level == DegradationLevel.FULL:
        return "All components healthy"
    elif not unhealthy:
        return f"Transitioning to {new_level.name}"
    else:
        components = ", ".join(c.component for c in unhealthy)
        return f"Issues with: {components}"


def get_current_level() -> DegradationLevel:
    """Get the current degradation level."""
    state = load_state()
    return state.level


def is_feature_available(feature: str) -> bool:
    """Check if a feature is available at the current degradation level."""
    level = get_current_level()

    # Feature availability by level
    availability: dict[str, DegradationLevel] = {
        "task_tracking": DegradationLevel.REDUCED,
        "adversarial_review": DegradationLevel.REDUCED,
        "auto_sync": DegradationLevel.REDUCED,
        "pre_commit_checks": DegradationLevel.MANUAL,
        "trace_markers": DegradationLevel.MANUAL,
        "git_operations": DegradationLevel.SAFE,
    }

    min_level = availability.get(feature, DegradationLevel.FULL)
    return level.value <= min_level.value


def lock_level(reason: str) -> None:
    """Lock the current degradation level."""
    state = load_state()
    state.locked = True
    state.lock_reason = reason
    save_state(state)


def unlock_level() -> None:
    """Unlock the degradation level."""
    state = load_state()
    state.locked = False
    state.lock_reason = ""
    save_state(state)


def reset_to_full() -> SystemState:
    """Reset to full degradation level."""
    state = SystemState(level=DegradationLevel.FULL)
    save_state(state)
    return state


def get_status_report() -> dict[str, Any]:
    """Get a detailed status report."""
    state = load_state()

    return {
        "level": state.level.name,
        "level_description": _level_description(state.level),
        "locked": state.locked,
        "lock_reason": state.lock_reason,
        "last_transition": state.last_transition.isoformat(),
        "transition_reason": state.transition_reason,
        "components": {
            name: {
                "healthy": status.healthy,
                "message": status.message,
                "last_check": status.last_check.isoformat(),
                "recovery_attempted": status.recovery_attempted,
                "recovery_succeeded": status.recovery_succeeded,
            }
            for name, status in state.components.items()
        },
        "available_features": {
            feature: is_feature_available(feature)
            for feature in [
                "task_tracking",
                "adversarial_review",
                "auto_sync",
                "pre_commit_checks",
                "trace_markers",
                "git_operations",
            ]
        },
    }


def _level_description(level: DegradationLevel) -> str:
    """Get human-readable description of degradation level."""
    descriptions = {
        DegradationLevel.FULL: "All features working normally",
        DegradationLevel.REDUCED: "Non-critical features disabled",
        DegradationLevel.MANUAL: "Manual intervention required for some operations",
        DegradationLevel.SAFE: "Minimal safe operation mode",
        DegradationLevel.RECOVERY: "Actively attempting to repair issues",
    }
    return descriptions.get(level, "Unknown")
