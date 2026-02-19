"""Tests for hole data structures and taxonomy.

@trace SPEC-07
"""

from __future__ import annotations

import pytest

from tools.spec_decompose.holes import (
    AGENT_RESOLVABLE,
    BEADS_LABELS,
    HUMAN_REQUIRED,
    MIXED_RESOLUTION,
    RESOLUTION_METHODS,
    Hole,
    HoleKnown,
    HoleType,
    labels_for_type,
    resolver_for_type,
)


class TestHoleType:
    """Tests for the HoleType enum."""

    def test_all_types_defined(self) -> None:
        types = set(HoleType)
        assert types == {
            HoleType.CLARIFICATION,
            HoleType.VALIDATION,
            HoleType.RESEARCH,
            HoleType.SYNTHESIS,
            HoleType.ESCALATION,
        }

    def test_string_values(self) -> None:
        assert HoleType.CLARIFICATION.value == "clarification"
        assert HoleType.VALIDATION.value == "validation"
        assert HoleType.RESEARCH.value == "research"
        assert HoleType.SYNTHESIS.value == "synthesis"
        assert HoleType.ESCALATION.value == "escalation"

    def test_from_string(self) -> None:
        assert HoleType("clarification") == HoleType.CLARIFICATION


class TestGroupings:
    """Tests for convenience groupings."""

    def test_agent_resolvable_contains_validation_and_research(self) -> None:
        assert HoleType.VALIDATION in AGENT_RESOLVABLE
        assert HoleType.RESEARCH in AGENT_RESOLVABLE

    def test_human_required_contains_clarification_and_escalation(self) -> None:
        assert HoleType.CLARIFICATION in HUMAN_REQUIRED
        assert HoleType.ESCALATION in HUMAN_REQUIRED

    def test_synthesis_is_mixed(self) -> None:
        assert HoleType.SYNTHESIS in MIXED_RESOLUTION

    def test_no_overlap_between_agent_and_human(self) -> None:
        assert len(AGENT_RESOLVABLE & HUMAN_REQUIRED) == 0

    def test_all_types_in_some_group(self) -> None:
        all_grouped = AGENT_RESOLVABLE | HUMAN_REQUIRED | MIXED_RESOLUTION
        assert all_grouped == set(HoleType)


class TestBeadsLabels:
    """Tests for beads label conventions."""

    def test_all_types_have_labels(self) -> None:
        for ht in HoleType:
            assert ht in BEADS_LABELS

    def test_all_labels_include_hole_base(self) -> None:
        for ht in HoleType:
            assert "hole" in BEADS_LABELS[ht]

    def test_agent_resolvable_labels(self) -> None:
        for ht in AGENT_RESOLVABLE:
            assert "hole:agent-resolvable" in BEADS_LABELS[ht]

    def test_human_required_labels(self) -> None:
        for ht in HUMAN_REQUIRED:
            assert "hole:human-required" in BEADS_LABELS[ht]

    def test_type_specific_labels(self) -> None:
        assert "hole:clarification" in BEADS_LABELS[HoleType.CLARIFICATION]
        assert "hole:validation" in BEADS_LABELS[HoleType.VALIDATION]
        assert "hole:research" in BEADS_LABELS[HoleType.RESEARCH]
        assert "hole:synthesis" in BEADS_LABELS[HoleType.SYNTHESIS]
        assert "hole:escalation" in BEADS_LABELS[HoleType.ESCALATION]


class TestResolutionMethods:
    """Tests for resolution methods."""

    def test_all_types_have_methods(self) -> None:
        for ht in HoleType:
            assert ht in RESOLUTION_METHODS

    def test_agent_types_use_agent_research(self) -> None:
        assert RESOLUTION_METHODS[HoleType.VALIDATION] == "agent_research"
        assert RESOLUTION_METHODS[HoleType.RESEARCH] == "agent_research"

    def test_human_types_use_human(self) -> None:
        assert RESOLUTION_METHODS[HoleType.CLARIFICATION] == "human_input"
        assert RESOLUTION_METHODS[HoleType.ESCALATION] == "human_decision"

    def test_synthesis_uses_synthesis(self) -> None:
        assert RESOLUTION_METHODS[HoleType.SYNTHESIS] == "synthesis"


class TestHole:
    """Tests for the Hole dataclass."""

    def test_basic_creation(self) -> None:
        h = Hole(
            number="H001",
            title="Test hole",
            hole_type=HoleType.CLARIFICATION,
        )
        assert h.number == "H001"
        assert h.title == "Test hole"
        assert h.hole_type == HoleType.CLARIFICATION
        assert h.priority == 1

    def test_auto_resolution_method(self) -> None:
        h = Hole(number="H001", title="Test", hole_type=HoleType.VALIDATION)
        assert h.resolution_method == "agent_research"

    def test_explicit_resolution_method(self) -> None:
        h = Hole(
            number="H001",
            title="Test",
            hole_type=HoleType.VALIDATION,
            resolution_method="custom_method",
        )
        assert h.resolution_method == "custom_method"

    def test_is_agent_resolvable(self) -> None:
        assert Hole(number="H1", title="T", hole_type=HoleType.VALIDATION).is_agent_resolvable
        assert Hole(number="H1", title="T", hole_type=HoleType.RESEARCH).is_agent_resolvable
        assert not Hole(number="H1", title="T", hole_type=HoleType.CLARIFICATION).is_agent_resolvable

    def test_is_human_required(self) -> None:
        assert Hole(number="H1", title="T", hole_type=HoleType.CLARIFICATION).is_human_required
        assert Hole(number="H1", title="T", hole_type=HoleType.ESCALATION).is_human_required
        assert not Hole(number="H1", title="T", hole_type=HoleType.RESEARCH).is_human_required

    def test_labels_property(self) -> None:
        h = Hole(number="H001", title="T", hole_type=HoleType.RESEARCH)
        labels = h.labels
        assert "hole" in labels
        assert "hole:research" in labels
        assert "hole:agent-resolvable" in labels

    def test_to_dict(self) -> None:
        h = Hole(
            number="H001",
            title="Session behavior",
            hole_type=HoleType.CLARIFICATION,
            priority=1,
            known=HoleKnown(
                input_desc="User with revoked token",
                output_desc="[? behavior]",
                constraints=["No orphaned sessions"],
            ),
            unknown=["Eager or lazy invalidation?"],
            blocks_tasks=[5, 6],
            traces=["SPEC-03.04"],
        )
        d = h.to_dict()
        assert d["number"] == "H001"
        assert d["hole_type"] == "clarification"
        assert d["known"]["input"] == "User with revoked token"
        assert len(d["unknown"]) == 1
        assert d["blocks_tasks"] == [5, 6]


class TestHelperFunctions:
    """Tests for module-level helpers."""

    def test_labels_for_type(self) -> None:
        labels = labels_for_type(HoleType.ESCALATION)
        assert "hole" in labels
        assert "hole:escalation" in labels

    def test_resolver_for_agent_types(self) -> None:
        assert resolver_for_type(HoleType.VALIDATION) == "agent"
        assert resolver_for_type(HoleType.RESEARCH) == "agent"

    def test_resolver_for_human_types(self) -> None:
        assert resolver_for_type(HoleType.CLARIFICATION) == "human"
        assert resolver_for_type(HoleType.ESCALATION) == "human"

    def test_resolver_for_mixed(self) -> None:
        assert resolver_for_type(HoleType.SYNTHESIS) == "mixed"
