# @trace SPEC-07
"""Hole data structures and taxonomy for first-class unknowns.

Holes represent things the system doesn't yet know but needs to know
before certain work can proceed. They are first-class nodes in the work
graph — they block downstream tasks and carry partial information about
their shape.

Inspired by typed holes in Hazel and RFLX: a hole carries partial
characterization that constrains valid fillings and enables progressive
refinement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class HoleType(str, Enum):
    """Taxonomy of hole types based on resolution method."""

    CLARIFICATION = "clarification"
    VALIDATION = "validation"
    RESEARCH = "research"
    SYNTHESIS = "synthesis"
    ESCALATION = "escalation"


# Convenience groupings for routing
AGENT_RESOLVABLE: frozenset[HoleType] = frozenset(
    {HoleType.VALIDATION, HoleType.RESEARCH}
)
HUMAN_REQUIRED: frozenset[HoleType] = frozenset(
    {HoleType.CLARIFICATION, HoleType.ESCALATION}
)
MIXED_RESOLUTION: frozenset[HoleType] = frozenset({HoleType.SYNTHESIS})

# Beads label conventions per hole type
BEADS_LABELS: dict[HoleType, list[str]] = {
    HoleType.CLARIFICATION: ["hole", "hole:clarification", "hole:human-required"],
    HoleType.VALIDATION: ["hole", "hole:validation", "hole:agent-resolvable"],
    HoleType.RESEARCH: ["hole", "hole:research", "hole:agent-resolvable"],
    HoleType.SYNTHESIS: ["hole", "hole:synthesis"],
    HoleType.ESCALATION: ["hole", "hole:escalation", "hole:human-required"],
}

# Resolution methods per hole type
RESOLUTION_METHODS: dict[HoleType, str] = {
    HoleType.CLARIFICATION: "human_input",
    HoleType.VALIDATION: "agent_research",
    HoleType.RESEARCH: "agent_research",
    HoleType.SYNTHESIS: "synthesis",
    HoleType.ESCALATION: "human_decision",
}

ResolutionEffort = Literal["low", "medium", "high"]

Provenance = Literal["decomposition", "implementation", "review"]


@dataclass
class HoleKnown:
    """What IS known about the hole — partial types, constraints, scope."""

    input_desc: str = ""
    output_desc: str = ""
    constraints: list[str] = field(default_factory=list)
    related_types: list[str] = field(default_factory=list)


@dataclass
class Hole:
    """A first-class unknown in the work graph."""

    number: str  # e.g., "H001"
    title: str
    hole_type: HoleType
    priority: int = 1
    known: HoleKnown = field(default_factory=HoleKnown)
    unknown: list[str] = field(default_factory=list)
    blocks_tasks: list[int] = field(default_factory=list)
    resolution_method: str = ""
    traces: list[str] = field(default_factory=list)
    estimated_resolution_effort: ResolutionEffort = "medium"
    provenance: Provenance = "decomposition"

    def __post_init__(self) -> None:
        if not self.resolution_method:
            self.resolution_method = RESOLUTION_METHODS.get(
                self.hole_type, "human_input"
            )

    @property
    def is_agent_resolvable(self) -> bool:
        return self.hole_type in AGENT_RESOLVABLE

    @property
    def is_human_required(self) -> bool:
        return self.hole_type in HUMAN_REQUIRED

    @property
    def labels(self) -> list[str]:
        return BEADS_LABELS.get(self.hole_type, ["hole"])

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "title": self.title,
            "hole_type": self.hole_type.value,
            "priority": self.priority,
            "known": {
                "input": self.known.input_desc,
                "output": self.known.output_desc,
                "constraints": self.known.constraints,
                "related_types": self.known.related_types,
            },
            "unknown": self.unknown,
            "blocks_tasks": self.blocks_tasks,
            "resolution_method": self.resolution_method,
            "traces": self.traces,
            "estimated_resolution_effort": self.estimated_resolution_effort,
        }


def labels_for_type(hole_type: HoleType) -> list[str]:
    """Get beads labels for a hole type."""
    return BEADS_LABELS.get(hole_type, ["hole"])


def resolver_for_type(hole_type: HoleType) -> str:
    """Get who resolves this hole type: 'agent', 'human', or 'mixed'."""
    if hole_type in AGENT_RESOLVABLE:
        return "agent"
    if hole_type in HUMAN_REQUIRED:
        return "human"
    return "mixed"
