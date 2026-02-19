# @trace SPEC-07
"""Tests for diff-based re-decomposition."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from tools.spec_decompose.diff import (
    ChangeCategory,
    DiffItem,
    DiffResult,
    WorkItemSnapshot,
    _extract_produces_from_text,
    _extract_traces_from_text,
    _has_scope_changed,
    _hole_match_score,
    _match_score,
    compute_diff,
    generate_diff_markdown,
    generate_diff_script,
    snapshot_from_beads_json,
    snapshot_from_state_yaml,
    write_diff_output,
)


# --- Fixtures ---


def _make_snapshot(
    id: str = "bd-abc",
    title: str = "Configure OAuth",
    status: str = "open",
    spec_traces: list[str] | None = None,
    depends_on: list[str] | None = None,
    produces: list[str] | None = None,
    description: str = "",
    is_hole: bool = False,
    hole_type: str = "",
) -> WorkItemSnapshot:
    return WorkItemSnapshot(
        id=id,
        title=title,
        status=status,
        spec_traces=spec_traces or [],
        depends_on=depends_on or [],
        produces=produces or [],
        description=description,
        is_hole=is_hole,
        hole_type=hole_type,
    )


def _make_target_task(
    number: int = 1,
    title: str = "Configure OAuth",
    spec_traces: list[str] | None = None,
    depends_on_tasks: list[int] | None = None,
    depends_on_holes: list[str] | None = None,
    description: str = "Task description",
    acceptance_criteria: list[str] | None = None,
    produces: list[str] | None = None,
    priority: int = 2,
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "spec_traces": spec_traces or [],
        "depends_on_tasks": depends_on_tasks or [],
        "depends_on_holes": depends_on_holes or [],
        "description": description,
        "acceptance_criteria": acceptance_criteria or [],
        "produces": produces or [],
        "estimated_tokens": {"total": 15000},
        "priority": priority,
    }


def _make_target_hole(
    number: str = "H001",
    title: str = "Session behavior on revocation",
    hole_type: str = "clarification",
    blocks_tasks: list[int] | None = None,
    priority: int = 1,
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "hole_type": hole_type,
        "blocks_tasks": blocks_tasks or [],
        "priority": priority,
    }


# --- Snapshot Tests ---


class TestSnapshotFromBeadsJson:
    def test_basic_task(self):
        issues = [
            {
                "id": "bd-abc",
                "title": "Configure OAuth",
                "status": "open",
                "description": "Implements SPEC-03.01",
                "labels": [],
            }
        ]
        snapshots = snapshot_from_beads_json(issues)
        assert len(snapshots) == 1
        assert snapshots[0].id == "bd-abc"
        assert snapshots[0].title == "Configure OAuth"
        assert snapshots[0].status == "open"
        assert snapshots[0].spec_traces == ["SPEC-03.01"]
        assert snapshots[0].is_hole is False

    def test_hole_detection(self):
        issues = [
            {
                "id": "bd-xyz",
                "title": "HOLE: Rate limit algorithm",
                "status": "open",
                "description": "",
                "labels": ["hole", "hole:research"],
            }
        ]
        snapshots = snapshot_from_beads_json(issues)
        assert len(snapshots) == 1
        assert snapshots[0].is_hole is True
        assert snapshots[0].hole_type == "research"

    def test_produces_extraction(self):
        issues = [
            {
                "id": "bd-abc",
                "title": "Auth endpoint",
                "status": "open",
                "description": '<!-- ORCHESTRATION METADATA\nproduces: ["src/auth.py", "tests/test_auth.py"]\n-->',
                "labels": [],
            }
        ]
        snapshots = snapshot_from_beads_json(issues)
        assert snapshots[0].produces == ["src/auth.py", "tests/test_auth.py"]

    def test_depends_on(self):
        issues = [
            {
                "id": "bd-abc",
                "title": "Token exchange",
                "status": "in_progress",
                "description": "",
                "labels": [],
                "depends_on": [{"id": "bd-dep1"}, {"id": "bd-dep2"}],
            }
        ]
        snapshots = snapshot_from_beads_json(issues)
        assert snapshots[0].depends_on == ["bd-dep1", "bd-dep2"]

    def test_empty_list(self):
        assert snapshot_from_beads_json([]) == []


class TestSnapshotFromStateYaml:
    def test_basic_state(self, tmp_path: Path):
        state = {
            "version": 1,
            "tasks": [
                {
                    "number": 1,
                    "title": "Configure OAuth",
                    "status": "open",
                    "traces": ["SPEC-03.01"],
                    "depends_on": [],
                }
            ],
            "holes": [
                {
                    "number": "H001",
                    "title": "Session behavior",
                    "status": "open",
                    "type": "clarification",
                    "traces": ["SPEC-03.04"],
                }
            ],
        }
        state_path = tmp_path / "state.yaml"
        state_path.write_text(yaml.dump(state))

        snapshots = snapshot_from_state_yaml(state_path)
        assert len(snapshots) == 2

        task = snapshots[0]
        assert task.id == "1"
        assert task.title == "Configure OAuth"
        assert task.is_hole is False
        assert task.spec_traces == ["SPEC-03.01"]

        hole = snapshots[1]
        assert hole.id == "H001"
        assert hole.is_hole is True
        assert hole.hole_type == "clarification"

    def test_empty_state(self, tmp_path: Path):
        state_path = tmp_path / "state.yaml"
        state_path.write_text("")
        assert snapshot_from_state_yaml(state_path) == []


# --- Trace/Produces Extraction ---


class TestExtractTraces:
    def test_extracts_spec_ids(self):
        text = "This implements SPEC-03.01 and SPEC-03.02"
        assert _extract_traces_from_text(text) == ["SPEC-03.01", "SPEC-03.02"]

    def test_no_traces(self):
        assert _extract_traces_from_text("No specs here") == []

    def test_deduplication(self):
        text = "SPEC-01.01 and again SPEC-01.01"
        assert _extract_traces_from_text(text) == ["SPEC-01.01"]


class TestExtractProduces:
    def test_extracts_file_paths(self):
        text = 'produces: ["src/auth.py", "tests/test_auth.py"]'
        assert _extract_produces_from_text(text) == [
            "src/auth.py",
            "tests/test_auth.py",
        ]

    def test_no_produces(self):
        assert _extract_produces_from_text("no metadata") == []


# --- Match Score ---


class TestMatchScore:
    def test_perfect_trace_match(self):
        ex = _make_snapshot(spec_traces=["SPEC-03.01"])
        tgt = _make_target_task(spec_traces=["SPEC-03.01"])
        score = _match_score(ex, tgt)
        assert score >= 0.6  # Full trace match worth 60%

    def test_title_only_match(self):
        ex = _make_snapshot(title="Configure OAuth provider")
        tgt = _make_target_task(title="Configure OAuth provider")
        score = _match_score(ex, tgt)
        assert score >= 0.2  # Title match worth 30%

    def test_no_match(self):
        ex = _make_snapshot(
            title="Completely different",
            spec_traces=["SPEC-99.99"],
        )
        tgt = _make_target_task(
            title="Something else entirely",
            spec_traces=["SPEC-01.01"],
        )
        score = _match_score(ex, tgt)
        assert score < 0.3

    def test_file_overlap_bonus(self):
        ex = _make_snapshot(produces=["src/auth.py"])
        tgt = _make_target_task(produces=["src/auth.py"])
        score_with = _match_score(ex, tgt)

        ex_no = _make_snapshot(produces=[])
        score_without = _match_score(ex_no, tgt)
        assert score_with >= score_without

    def test_partial_trace_match(self):
        ex = _make_snapshot(spec_traces=["SPEC-03.01", "SPEC-03.02"])
        tgt = _make_target_task(spec_traces=["SPEC-03.01", "SPEC-03.03"])
        score = _match_score(ex, tgt)
        # 1/3 overlap = ~0.2 from traces
        assert 0.1 < score < 0.6


class TestHoleMatchScore:
    def test_same_title_and_type(self):
        ex = _make_snapshot(
            title="Session behavior on revocation",
            is_hole=True,
            hole_type="clarification",
        )
        tgt = _make_target_hole(
            title="Session behavior on revocation",
            hole_type="clarification",
        )
        score = _hole_match_score(ex, tgt)
        assert score >= 0.9

    def test_different_type(self):
        ex = _make_snapshot(
            title="Rate limit algorithm",
            is_hole=True,
            hole_type="research",
        )
        tgt = _make_target_hole(
            title="Rate limit algorithm",
            hole_type="clarification",
        )
        score = _hole_match_score(ex, tgt)
        assert 0.3 < score < 0.8  # Title matches but type doesn't


# --- Scope Change Detection ---


class TestHasScopeChanged:
    def test_no_change(self):
        ex = _make_snapshot(description="Same", spec_traces=["SPEC-01.01"])
        tgt = _make_target_task(description="Same", spec_traces=["SPEC-01.01"])
        changed, summary = _has_scope_changed(ex, tgt)
        assert changed is False

    def test_description_changed(self):
        ex = _make_snapshot(description="Old description")
        tgt = _make_target_task(description="New description")
        changed, summary = _has_scope_changed(ex, tgt)
        assert changed is True
        assert "description updated" in summary

    def test_traces_added(self):
        ex = _make_snapshot(spec_traces=["SPEC-01.01"])
        tgt = _make_target_task(spec_traces=["SPEC-01.01", "SPEC-01.02"])
        changed, summary = _has_scope_changed(ex, tgt)
        assert changed is True
        assert "new spec refs" in summary

    def test_traces_removed(self):
        ex = _make_snapshot(spec_traces=["SPEC-01.01", "SPEC-01.02"])
        tgt = _make_target_task(spec_traces=["SPEC-01.01"])
        changed, summary = _has_scope_changed(ex, tgt)
        assert changed is True
        assert "removed spec refs" in summary


# --- Compute Diff ---


class TestComputeDiff:
    def test_all_unchanged(self):
        existing = [
            _make_snapshot(
                id="1", title="Task A", spec_traces=["SPEC-01.01"]
            ),
        ]
        target = {
            "tasks": [
                _make_target_task(
                    number=1,
                    title="Task A",
                    spec_traces=["SPEC-01.01"],
                    description="",
                )
            ],
            "holes": [],
        }
        diff = compute_diff(existing, target)
        assert len(diff.unchanged) == 1
        assert len(diff.modified) == 0
        assert len(diff.new) == 0
        assert len(diff.removed) == 0

    def test_new_task(self):
        existing: list[WorkItemSnapshot] = []
        target = {
            "tasks": [_make_target_task(number=1, title="Brand new task")],
            "holes": [],
        }
        diff = compute_diff(existing, target)
        assert len(diff.new) == 1
        assert diff.new[0].target is not None
        assert diff.new[0].target["title"] == "Brand new task"

    def test_removed_task(self):
        existing = [
            _make_snapshot(id="1", title="Old task", spec_traces=["SPEC-99.01"]),
        ]
        target = {"tasks": [], "holes": []}
        diff = compute_diff(existing, target)
        assert len(diff.removed) == 1

    def test_modified_open_task(self):
        existing = [
            _make_snapshot(
                id="1",
                title="Task A",
                status="open",
                spec_traces=["SPEC-01.01"],
                description="Old description",
            ),
        ]
        target = {
            "tasks": [
                _make_target_task(
                    number=1,
                    title="Task A",
                    spec_traces=["SPEC-01.01"],
                    description="New description with changes",
                )
            ],
            "holes": [],
        }
        diff = compute_diff(existing, target)
        assert len(diff.modified) == 1
        assert diff.modified[0].needs_human_review is False

    def test_modified_closed_task_creates_rework(self):
        existing = [
            _make_snapshot(
                id="1",
                title="Rate limiting",
                status="closed",
                spec_traces=["SPEC-04.02"],
                description="100 req/min",
            ),
        ]
        target = {
            "tasks": [
                _make_target_task(
                    number=1,
                    title="Rate limiting",
                    spec_traces=["SPEC-04.02"],
                    description="50 req/min",
                )
            ],
            "holes": [],
        }
        diff = compute_diff(existing, target)
        assert len(diff.modified) == 1
        assert diff.modified[0].needs_human_review is True
        assert diff.modified[0].rework_description != ""
        assert diff.has_rework is True

    def test_modified_in_progress_needs_review(self):
        existing = [
            _make_snapshot(
                id="1",
                title="Task A",
                status="in_progress",
                spec_traces=["SPEC-01.01"],
                description="Working on it",
            ),
        ]
        target = {
            "tasks": [
                _make_target_task(
                    number=1,
                    title="Task A",
                    spec_traces=["SPEC-01.01"],
                    description="Changed while in progress",
                )
            ],
            "holes": [],
        }
        diff = compute_diff(existing, target)
        assert len(diff.modified) == 1
        assert diff.modified[0].needs_human_review is True

    def test_dependency_changed(self):
        existing = [
            _make_snapshot(
                id="1",
                title="Task A",
                spec_traces=["SPEC-01.01"],
                depends_on=["2"],
                description="",
            ),
        ]
        target = {
            "tasks": [
                _make_target_task(
                    number=1,
                    title="Task A",
                    spec_traces=["SPEC-01.01"],
                    depends_on_tasks=[3],
                    description="",
                )
            ],
            "holes": [],
        }
        diff = compute_diff(existing, target)
        assert len(diff.dependency_changed) == 1

    def test_removed_in_progress_needs_review(self):
        existing = [
            _make_snapshot(
                id="1",
                title="WIP task",
                status="in_progress",
                spec_traces=["SPEC-99.01"],
            ),
        ]
        target = {"tasks": [], "holes": []}
        diff = compute_diff(existing, target)
        assert len(diff.removed) == 1
        assert diff.removed[0].needs_human_review is True


class TestDiffHoles:
    def test_new_hole(self):
        existing: list[WorkItemSnapshot] = []
        target = {
            "tasks": [],
            "holes": [_make_target_hole(number="H001", title="New ambiguity")],
        }
        diff = compute_diff(existing, target)
        new_holes = [
            h for h in diff.hole_changes if h.category == ChangeCategory.NEW
        ]
        assert len(new_holes) == 1

    def test_hole_auto_resolved(self):
        existing = [
            _make_snapshot(
                id="H001",
                title="Session behavior",
                status="open",
                is_hole=True,
                hole_type="clarification",
            ),
        ]
        target = {"tasks": [], "holes": []}
        diff = compute_diff(existing, target)
        resolved = [
            h
            for h in diff.hole_changes
            if h.category == ChangeCategory.REMOVED
        ]
        assert len(resolved) == 1
        assert "auto-resolve" in resolved[0].change_summary

    def test_resolved_hole_contradicted(self):
        existing = [
            _make_snapshot(
                id="H001",
                title="Session behavior on revocation",
                status="closed",
                is_hole=True,
                hole_type="clarification",
            ),
        ]
        target = {
            "tasks": [],
            "holes": [
                _make_target_hole(
                    number="H001",
                    title="Session behavior on revocation",
                    hole_type="clarification",
                )
            ],
        }
        diff = compute_diff(existing, target)
        modified = [
            h
            for h in diff.hole_changes
            if h.category == ChangeCategory.MODIFIED
        ]
        assert len(modified) == 1
        assert modified[0].needs_human_review is True

    def test_hole_still_open(self):
        existing = [
            _make_snapshot(
                id="H001",
                title="Rate limit algorithm",
                status="open",
                is_hole=True,
                hole_type="research",
            ),
        ]
        target = {
            "tasks": [],
            "holes": [
                _make_target_hole(
                    number="H001",
                    title="Rate limit algorithm",
                    hole_type="research",
                )
            ],
        }
        diff = compute_diff(existing, target)
        unchanged = [
            h
            for h in diff.hole_changes
            if h.category == ChangeCategory.UNCHANGED
        ]
        assert len(unchanged) == 1


# --- Output Generation ---


class TestDiffMarkdown:
    def test_generates_markdown(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.UNCHANGED,
                    existing=_make_snapshot(id="1", title="Task A", status="closed"),
                ),
                DiffItem(
                    category=ChangeCategory.NEW,
                    target=_make_target_task(number=2, title="New task"),
                ),
                DiffItem(
                    category=ChangeCategory.REMOVED,
                    existing=_make_snapshot(id="3", title="Old task", status="open"),
                    change_summary="requirement removed",
                ),
            ]
        )
        md = generate_diff_markdown(diff, spec_source="docs/spec/auth.md")
        assert "# Decomposition Diff" in md
        assert "docs/spec/auth.md" in md
        assert "Unchanged (1 tasks)" in md
        assert "New (1 tasks)" in md
        assert "Removed (1 tasks)" in md

    def test_rework_section(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.MODIFIED,
                    existing=_make_snapshot(
                        id="1", title="Rate limit", status="closed"
                    ),
                    target=_make_target_task(number=1, title="Rate limit"),
                    change_summary="rate changed",
                    needs_human_review=True,
                    rework_description="Update rate from 100 to 50",
                ),
            ]
        )
        md = generate_diff_markdown(diff)
        assert "REWORK" in md
        assert "Update rate from 100 to 50" in md
        assert "discovered-from" in md

    def test_hole_changes_section(self):
        diff = DiffResult(
            hole_changes=[
                DiffItem(
                    category=ChangeCategory.NEW,
                    target=_make_target_hole(
                        number="H002",
                        title="New ambiguity",
                        hole_type="clarification",
                    ),
                    change_summary="new ambiguity",
                ),
                DiffItem(
                    category=ChangeCategory.REMOVED,
                    existing=_make_snapshot(
                        id="H001",
                        title="Old question",
                        status="open",
                        is_hole=True,
                    ),
                    change_summary="auto-resolve",
                ),
            ]
        )
        md = generate_diff_markdown(diff)
        assert "Hole Changes" in md
        assert "Auto-Resolved" in md
        assert "New Holes" in md

    def test_human_review_section(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.MODIFIED,
                    existing=_make_snapshot(
                        id="1", title="In progress task", status="in_progress"
                    ),
                    target=_make_target_task(number=1),
                    change_summary="scope changed while in progress",
                    needs_human_review=True,
                ),
            ]
        )
        md = generate_diff_markdown(diff)
        assert "Requires Human Review" in md

    def test_empty_diff(self):
        diff = DiffResult()
        md = generate_diff_markdown(diff)
        assert "# Decomposition Diff" in md
        assert "0 new" in md


class TestDiffScript:
    def test_modified_open_updates(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.MODIFIED,
                    existing=_make_snapshot(id="bd-abc", title="Task A", status="open"),
                    target=_make_target_task(number=1, title="Task A"),
                    change_summary="description changed",
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "bd update" in script
        assert "bd-abc" in script

    def test_modified_closed_creates_rework(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.MODIFIED,
                    existing=_make_snapshot(
                        id="bd-abc", title="Rate limit", status="closed"
                    ),
                    target=_make_target_task(number=1, title="Rate limit"),
                    change_summary="rate changed",
                    rework_description="Update rate",
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "bd create" in script
        assert "Rework" in script
        assert "discovered-from" in script

    def test_new_task_created(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.NEW,
                    target=_make_target_task(number=5, title="New feature"),
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "bd create" in script
        assert "New feature" in script

    def test_removed_open_closed(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.REMOVED,
                    existing=_make_snapshot(
                        id="bd-xyz", title="Obsolete", status="open"
                    ),
                    change_summary="removed",
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "bd close" in script
        assert "Obsolete" in script

    def test_removed_in_progress_commented(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.REMOVED,
                    existing=_make_snapshot(
                        id="bd-xyz", title="WIP", status="in_progress"
                    ),
                    change_summary="removed",
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "review" in script.lower()
        assert "bd close" not in script.split("review")[0]

    def test_hole_auto_resolved(self):
        diff = DiffResult(
            hole_changes=[
                DiffItem(
                    category=ChangeCategory.REMOVED,
                    existing=_make_snapshot(
                        id="bd-h1", title="Old question", status="open", is_hole=True
                    ),
                    change_summary="auto-resolve",
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "bd close" in script
        assert "Auto-resolved" in script

    def test_new_hole_created(self):
        diff = DiffResult(
            hole_changes=[
                DiffItem(
                    category=ChangeCategory.NEW,
                    target=_make_target_hole(
                        number="H003",
                        title="New ambiguity",
                        hole_type="clarification",
                    ),
                    change_summary="new",
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "bd create" in script
        assert "HOLE:" in script
        assert "hole:clarification" in script

    def test_no_actions_message(self):
        diff = DiffResult()
        script = generate_diff_script(diff)
        assert "No changes needed" in script

    def test_in_progress_modified_is_comment(self):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.MODIFIED,
                    existing=_make_snapshot(
                        id="bd-wip", title="WIP task", status="in_progress"
                    ),
                    target=_make_target_task(number=1, title="WIP task"),
                    change_summary="scope changed",
                ),
            ]
        )
        script = generate_diff_script(diff)
        assert "# ⚠️" in script
        assert "review manually" in script


class TestWriteDiffOutput:
    def test_writes_files(self, tmp_path: Path):
        diff = DiffResult(
            items=[
                DiffItem(
                    category=ChangeCategory.NEW,
                    target=_make_target_task(number=1, title="New task"),
                ),
            ]
        )
        md_path, sh_path = write_diff_output(
            diff,
            spec_source="test.md",
            output_dir=tmp_path,
        )
        assert md_path.exists()
        assert sh_path.exists()
        assert "Decomposition Diff" in md_path.read_text()
        assert "#!/usr/bin/env bash" in sh_path.read_text()

    def test_default_output_dir(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        diff = DiffResult()
        md_path, sh_path = write_diff_output(diff)
        assert md_path == Path("decompose-diff.md")
        assert sh_path == Path("decompose-diff.sh")


# --- Integration-style Tests ---


class TestDiffIntegration:
    def test_mixed_changes(self):
        """Test a realistic scenario with multiple change types."""
        existing = [
            _make_snapshot(
                id="1",
                title="Configure OAuth",
                status="closed",
                spec_traces=["SPEC-03.01"],
                description="",
            ),
            _make_snapshot(
                id="2",
                title="Token exchange",
                status="in_progress",
                spec_traces=["SPEC-03.02"],
                description="",
            ),
            _make_snapshot(
                id="3",
                title="Legacy migration",
                status="open",
                spec_traces=["SPEC-99.01"],
                description="",
            ),
            _make_snapshot(
                id="H1",
                title="Session behavior",
                status="open",
                is_hole=True,
                hole_type="clarification",
            ),
        ]
        target = {
            "tasks": [
                _make_target_task(
                    number=1,
                    title="Configure OAuth",
                    spec_traces=["SPEC-03.01"],
                    description="",
                ),
                _make_target_task(
                    number=2,
                    title="Token exchange",
                    spec_traces=["SPEC-03.02"],
                    description="Now uses PKCE",
                ),
                _make_target_task(
                    number=4,
                    title="SAML SSO integration",
                    spec_traces=["SPEC-05.01"],
                ),
            ],
            "holes": [
                _make_target_hole(
                    number="H2",
                    title="SAML attribute mapping",
                    hole_type="research",
                ),
            ],
        }

        diff = compute_diff(existing, target)

        # T1: unchanged (closed, same spec)
        assert len(diff.unchanged) == 1

        # T2: modified (in_progress, description changed)
        assert len(diff.modified) == 1
        assert diff.modified[0].needs_human_review is True

        # T3: removed (spec trace doesn't match)
        assert len(diff.removed) == 1

        # T4: new
        assert len(diff.new) == 1

        # H1: removed (auto-resolve since no matching target hole)
        resolved_holes = [
            h
            for h in diff.hole_changes
            if h.category == ChangeCategory.REMOVED
        ]
        assert len(resolved_holes) == 1

        # H2: new
        new_holes = [
            h for h in diff.hole_changes if h.category == ChangeCategory.NEW
        ]
        assert len(new_holes) == 1

        # Generate both outputs
        md = generate_diff_markdown(diff, spec_source="auth.md")
        script = generate_diff_script(diff, existing)

        assert "Unchanged (1 tasks)" in md
        assert "Modified (1 tasks)" in md
        assert "New (1 tasks)" in md
        assert "Removed (1 tasks)" in md
        assert "Hole Changes" in md

        assert "#!/usr/bin/env bash" in script

    def test_complete_roundtrip_with_state_yaml(self, tmp_path: Path):
        """Test snapshot from state.yaml → compute_diff → output."""
        state = {
            "version": 1,
            "tasks": [
                {
                    "number": 1,
                    "title": "Setup auth",
                    "status": "closed",
                    "traces": ["SPEC-01.01"],
                    "depends_on": [],
                },
                {
                    "number": 2,
                    "title": "Token handling",
                    "status": "open",
                    "traces": ["SPEC-01.02"],
                    "depends_on": [1],
                },
            ],
            "holes": [],
        }
        state_path = tmp_path / "state.yaml"
        state_path.write_text(yaml.dump(state))

        snapshots = snapshot_from_state_yaml(state_path)
        assert len(snapshots) == 2

        target = {
            "tasks": [
                _make_target_task(
                    number=1,
                    title="Setup auth",
                    spec_traces=["SPEC-01.01"],
                    description="",
                ),
                _make_target_task(
                    number=2,
                    title="Token handling v2",
                    spec_traces=["SPEC-01.02"],
                    description="Updated approach",
                ),
            ],
            "holes": [],
        }

        diff = compute_diff(snapshots, target)
        assert len(diff.unchanged) == 1  # T1 closed and unchanged
        assert len(diff.modified) == 1  # T2 has changed description

        md_path, sh_path = write_diff_output(
            diff, spec_source="test", output_dir=tmp_path
        )
        assert md_path.exists()
        assert sh_path.exists()
