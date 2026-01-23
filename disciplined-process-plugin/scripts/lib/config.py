"""
Configuration loading, validation, and migration for disciplined-process.

Supports both v1.0 and v2.0 configuration schemas with automatic migration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ConfigVersion(Enum):
    V1 = "1.0"
    V2 = "2.0"


class EnforcementLevel(Enum):
    STRICT = "strict"
    GUIDED = "guided"
    MINIMAL = "minimal"


class TaskTracker(Enum):
    CHAINLINK = "chainlink"
    BEADS = "beads"
    GITHUB = "github"
    LINEAR = "linear"
    MARKDOWN = "markdown"
    BUILTIN = "builtin"  # Claude Code native task system
    NONE = "none"


class DegradationAction(Enum):
    WARN = "warn"
    SKIP = "skip"
    FAIL = "fail"


@dataclass
class ChainlinkConfig:
    """Chainlink-specific configuration."""

    sessions: bool = True
    milestones: bool = True
    time_tracking: bool = False
    rules_path: str = ".claude/rules/"


@dataclass
class BeadsConfig:
    """Beads-specific configuration."""

    auto_sync: bool = True
    daemon: bool = True
    prefix: str | None = None


@dataclass
class BuiltinConfig:
    """Claude Code builtin task system configuration."""

    task_list_id: str | None = None  # If None, auto-generated from project path hash
    auto_set_env: bool = True  # Auto-set CLAUDE_CODE_TASK_LIST_ID env var


@dataclass
class AdversarialConfig:
    """Adversarial review configuration."""

    enabled: bool = False
    model: str = "gemini-2.0-flash"
    max_iterations: int = 3
    trigger: str = "on_review"  # on_review | on_commit | manual
    fresh_context: bool = True


@dataclass
class SpecConfig:
    """Specification configuration."""

    directory: str = "docs/spec"
    id_format: str = "SPEC-{section:02d}.{item:02d}"
    require_issue_link: bool = False


@dataclass
class ADRConfig:
    """ADR configuration."""

    directory: str = "docs/adr"
    id_format: str = "ADR-{number:04d}"
    template: str | None = None


@dataclass
class TestingConfig:
    """Testing configuration."""

    unit_framework: str | None = None
    integration_framework: str | None = None
    property_framework: str | None = None
    e2e_framework: str | None = None
    unit_dir: str = "tests/unit"
    integration_dir: str = "tests/integration"
    property_dir: str = "tests/property"
    e2e_dir: str = "tests/e2e"


@dataclass
class EnforcementConfig:
    """Enforcement configuration with per-hook overrides."""

    level: EnforcementLevel = EnforcementLevel.GUIDED
    pre_commit_tests: EnforcementLevel | None = None
    trace_markers: EnforcementLevel | None = None
    spec_issue_links: EnforcementLevel | None = None
    task_id_commits: EnforcementLevel | None = None

    def effective_level(self, hook: str) -> EnforcementLevel:
        """Get the effective enforcement level for a specific hook."""
        override = getattr(self, hook, None)
        return override if override is not None else self.level


@dataclass
class DegradationConfig:
    """Graceful degradation configuration."""

    on_tracker_unavailable: DegradationAction = DegradationAction.WARN
    on_rlm_unavailable: DegradationAction = DegradationAction.SKIP
    on_adversary_unavailable: DegradationAction = DegradationAction.SKIP


@dataclass
class DPConfig:
    """Main disciplined-process configuration."""

    version: ConfigVersion = ConfigVersion.V2
    project_name: str = ""
    project_language: str = ""
    task_tracker: TaskTracker = TaskTracker.CHAINLINK
    chainlink: ChainlinkConfig = field(default_factory=ChainlinkConfig)
    beads: BeadsConfig = field(default_factory=BeadsConfig)
    builtin: BuiltinConfig = field(default_factory=BuiltinConfig)
    enforcement: EnforcementConfig = field(default_factory=EnforcementConfig)
    adversarial: AdversarialConfig = field(default_factory=AdversarialConfig)
    specs: SpecConfig = field(default_factory=SpecConfig)
    adrs: ADRConfig = field(default_factory=ADRConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    degradation: DegradationConfig = field(default_factory=DegradationConfig)
    hooks: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str | None = None) -> DPConfig:
        """Load configuration from file, with automatic migration if needed."""
        if path is None:
            # Search standard locations
            for candidate in [
                Path(".claude/dp-config.yaml"),
                Path(".claude/dp-config.yml"),
                Path("dp-config.yaml"),
            ]:
                if candidate.exists():
                    path = candidate
                    break

        if path is None:
            # Return default config
            return cls()

        path = Path(path)
        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        version = data.get("version", "1.0")

        if version == "1.0":
            return cls._from_v1(data)
        elif version == "2.0":
            return cls._from_v2(data)
        else:
            # Unknown version, try v2 parsing
            return cls._from_v2(data)

    @classmethod
    def _from_v1(cls, data: dict[str, Any]) -> DPConfig:
        """Parse v1.0 configuration and migrate to v2 structure."""
        config = cls(version=ConfigVersion.V1)

        # Project info
        project = data.get("project", {})
        config.project_name = project.get("name", "")
        config.project_language = project.get("language", "")

        # Task tracker - v1 used "tracking.provider"
        tracking = data.get("tracking", {})
        provider = tracking.get("provider", "beads")
        try:
            config.task_tracker = TaskTracker(provider)
        except ValueError:
            config.task_tracker = TaskTracker.BEADS

        # Enforcement - v1 used "enforcement.level"
        enforcement = data.get("enforcement", {})
        level = enforcement.get("level", "guided")
        try:
            config.enforcement.level = EnforcementLevel(level)
        except ValueError:
            config.enforcement.level = EnforcementLevel.GUIDED

        # Parse v1 overrides
        overrides = enforcement.get("overrides", {})
        for key, value in overrides.items():
            if hasattr(config.enforcement, key):
                try:
                    setattr(config.enforcement, key, EnforcementLevel(value))
                except ValueError:
                    pass

        # Testing frameworks
        testing = data.get("testing", {})
        frameworks = testing.get("frameworks", {})
        config.testing.unit_framework = frameworks.get("unit")
        config.testing.integration_framework = frameworks.get("integration")
        config.testing.property_framework = frameworks.get("property")
        config.testing.e2e_framework = frameworks.get("e2e")

        # Test directories - v1 used "tests" section
        tests = data.get("tests", {})
        config.testing.unit_dir = tests.get("unit_dir", "tests/unit")
        config.testing.integration_dir = tests.get("integration_dir", "tests/integration")
        config.testing.property_dir = tests.get("property_dir", "tests/property")
        config.testing.e2e_dir = tests.get("e2e_dir", "tests/e2e")

        # Specs
        spec = data.get("specification", {})
        config.specs.directory = spec.get("directory", "docs/spec")
        config.specs.id_format = spec.get("id_format", "SPEC-{section}.{paragraph}")

        # ADRs
        adr = data.get("adr", {})
        config.adrs.directory = adr.get("directory", "docs/adr")
        config.adrs.id_format = adr.get("id_format", "ADR-{number}")

        # Hooks
        hooks = data.get("hooks", {})
        config.hooks = {k: v for k, v in hooks.items() if isinstance(v, list)}

        return config

    @classmethod
    def _from_v2(cls, data: dict[str, Any]) -> DPConfig:
        """Parse v2.0 configuration."""
        config = cls(version=ConfigVersion.V2)

        # Project info
        project = data.get("project", {})
        config.project_name = project.get("name", "")
        config.project_language = project.get("language", "")

        # Task tracker
        tracker = data.get("task_tracker", "chainlink")
        try:
            config.task_tracker = TaskTracker(tracker)
        except ValueError:
            config.task_tracker = TaskTracker.CHAINLINK

        # Chainlink config
        chainlink = data.get("chainlink", {})
        features = chainlink.get("features", {})
        config.chainlink = ChainlinkConfig(
            sessions=features.get("sessions", True),
            milestones=features.get("milestones", True),
            time_tracking=features.get("time_tracking", False),
            rules_path=chainlink.get("rules_path", ".claude/rules/"),
        )

        # Beads config
        beads = data.get("beads", {})
        config.beads = BeadsConfig(
            auto_sync=beads.get("auto_sync", True),
            daemon=beads.get("daemon", True),
            prefix=beads.get("prefix"),
        )

        # Builtin config
        builtin = data.get("builtin", {})
        config.builtin = BuiltinConfig(
            task_list_id=builtin.get("task_list_id"),
            auto_set_env=builtin.get("auto_set_env", True),
        )

        # Enforcement
        enforcement = data.get("enforcement", {})
        if isinstance(enforcement, str):
            # Simple format: enforcement: "guided"
            try:
                config.enforcement.level = EnforcementLevel(enforcement)
            except ValueError:
                pass
        else:
            # Full format with overrides
            level = enforcement.get("level", "guided")
            try:
                config.enforcement.level = EnforcementLevel(level)
            except ValueError:
                pass

            overrides = enforcement.get("overrides", {})
            for key, value in overrides.items():
                if value and hasattr(config.enforcement, key):
                    try:
                        setattr(config.enforcement, key, EnforcementLevel(value))
                    except ValueError:
                        pass

        # Adversarial review
        adversarial = data.get("adversarial_review", {})
        config.adversarial = AdversarialConfig(
            enabled=adversarial.get("enabled", False),
            model=adversarial.get("model", "gemini-2.0-flash"),
            max_iterations=adversarial.get("max_iterations", 3),
            trigger=adversarial.get("trigger", "on_review"),
            fresh_context=adversarial.get("fresh_context", True),
        )

        # Specs
        specs = data.get("specs", {})
        config.specs = SpecConfig(
            directory=specs.get("directory", "docs/spec"),
            id_format=specs.get("id_format", "SPEC-{section:02d}.{item:02d}"),
            require_issue_link=specs.get("require_issue_link", False),
        )

        # ADRs
        adrs = data.get("adrs", {})
        config.adrs = ADRConfig(
            directory=adrs.get("directory", "docs/adr"),
            id_format=adrs.get("id_format", "ADR-{number:04d}"),
            template=adrs.get("template"),
        )

        # Testing
        testing = data.get("testing", {})
        frameworks = testing.get("frameworks", {})
        directories = testing.get("directories", {})
        config.testing = TestingConfig(
            unit_framework=frameworks.get("unit"),
            integration_framework=frameworks.get("integration"),
            property_framework=frameworks.get("property"),
            e2e_framework=frameworks.get("e2e"),
            unit_dir=directories.get("unit", "tests/unit"),
            integration_dir=directories.get("integration", "tests/integration"),
            property_dir=directories.get("property", "tests/property"),
            e2e_dir=directories.get("e2e", "tests/e2e"),
        )

        # Degradation
        degradation = data.get("degradation", {})
        config.degradation = DegradationConfig(
            on_tracker_unavailable=DegradationAction(
                degradation.get("on_tracker_unavailable", "warn")
            ),
            on_rlm_unavailable=DegradationAction(
                degradation.get("on_rlm_unavailable", "skip")
            ),
            on_adversary_unavailable=DegradationAction(
                degradation.get("on_adversary_unavailable", "skip")
            ),
        )

        # Hooks
        hooks = data.get("hooks", {})
        config.hooks = {k: v for k, v in hooks.items() if isinstance(v, list)}

        return config

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "version": self.version.value,
            "project": {
                "name": self.project_name,
                "language": self.project_language,
            },
            "task_tracker": self.task_tracker.value,
            "chainlink": {
                "features": {
                    "sessions": self.chainlink.sessions,
                    "milestones": self.chainlink.milestones,
                    "time_tracking": self.chainlink.time_tracking,
                },
                "rules_path": self.chainlink.rules_path,
            },
            "beads": {
                "auto_sync": self.beads.auto_sync,
                "daemon": self.beads.daemon,
                "prefix": self.beads.prefix,
            },
            "builtin": {
                "task_list_id": self.builtin.task_list_id,
                "auto_set_env": self.builtin.auto_set_env,
            },
            "enforcement": {
                "level": self.enforcement.level.value,
                "overrides": {
                    k: getattr(self.enforcement, k).value
                    for k in [
                        "pre_commit_tests",
                        "trace_markers",
                        "spec_issue_links",
                        "task_id_commits",
                    ]
                    if getattr(self.enforcement, k) is not None
                },
            },
            "adversarial_review": {
                "enabled": self.adversarial.enabled,
                "model": self.adversarial.model,
                "max_iterations": self.adversarial.max_iterations,
                "trigger": self.adversarial.trigger,
                "fresh_context": self.adversarial.fresh_context,
            },
            "specs": {
                "directory": self.specs.directory,
                "id_format": self.specs.id_format,
                "require_issue_link": self.specs.require_issue_link,
            },
            "adrs": {
                "directory": self.adrs.directory,
                "id_format": self.adrs.id_format,
                "template": self.adrs.template,
            },
            "testing": {
                "frameworks": {
                    "unit": self.testing.unit_framework,
                    "integration": self.testing.integration_framework,
                    "property": self.testing.property_framework,
                    "e2e": self.testing.e2e_framework,
                },
                "directories": {
                    "unit": self.testing.unit_dir,
                    "integration": self.testing.integration_dir,
                    "property": self.testing.property_dir,
                    "e2e": self.testing.e2e_dir,
                },
            },
            "degradation": {
                "on_tracker_unavailable": self.degradation.on_tracker_unavailable.value,
                "on_rlm_unavailable": self.degradation.on_rlm_unavailable.value,
                "on_adversary_unavailable": self.degradation.on_adversary_unavailable.value,
            },
            "hooks": self.hooks,
        }

    def save(self, path: Path | str) -> None:
        """Save configuration to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Always save as v2
        data = self.to_dict()
        data["version"] = "2.0"

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def migrate_v1_to_v2(v1_path: Path, v2_path: Path | None = None) -> DPConfig:
    """
    Migrate a v1.0 config file to v2.0 format.

    Args:
        v1_path: Path to the v1.0 config file
        v2_path: Path to save the v2.0 config (defaults to same location)

    Returns:
        The migrated DPConfig
    """
    config = DPConfig.load(v1_path)
    config.version = ConfigVersion.V2

    if v2_path is None:
        v2_path = v1_path

    config.save(v2_path)
    return config


# Global config instance (lazy-loaded)
_config: DPConfig | None = None


def get_config() -> DPConfig:
    """Get the global configuration, loading if necessary."""
    global _config
    if _config is None:
        _config = DPConfig.load()
    return _config


def reload_config() -> DPConfig:
    """Force reload of the global configuration."""
    global _config
    _config = DPConfig.load()
    return _config
