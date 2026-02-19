# @trace SPEC-07 SPEC-08
"""End-to-end integration test: spec → decompose → output → diff → progress report.

Uses a small fixture spec and pre-computed JSON (no subagent call).
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path

import pytest

from tools.spec_decompose.analyzer import read_spec_files
from tools.spec_decompose.validate import parse_decomposition_output
from tools.spec_decompose.graph import validate_dag, check_coverage, topological_sort
from tools.spec_decompose.output_beads import (
    generate_plan_markdown,
    generate_plan_script,
    write_beads_output,
)
from tools.spec_decompose.output_markdown import (
    write_markdown_output,
    generate_state_yaml,
)
from tools.spec_decompose.diff import (
    compute_diff,
    snapshot_from_state_yaml,
    write_diff_output,
)
from tools.spec_decompose.orchestration import (
    generate_orchestration_script,
    generate_pull_loop_script,
    write_orchestration_output,
)
from tools.progress_report.extractor import ProjectState, TaskState, GitState
from tools.progress_report.report import (
    generate_report_markdown,
    generate_report_json,
    write_report,
)
from tools.progress_report.triggers import evaluate_triggers
from tools.shared.config import ProgressReportConfig


# --- Fixture data ---

FIXTURE_SPEC = """\
# Authentication System

[SPEC-01.01] The system MUST authenticate users via OAuth 2.0.
[SPEC-01.02] The system MUST support Google and GitHub providers.
[SPEC-02.01] Sessions MUST expire after 8 hours.
[SPEC-02.02] Sessions MUST be invalidated on password change.
[SPEC-03.01] Rate limiting MUST enforce 100 requests/minute.
"""

FIXTURE_DECOMPOSITION = {
    "spec_source": ["docs/spec/auth.md"],
    "epic": {
        "title": "Authentication System",
        "description": "Implement OAuth-based authentication with sessions and rate limiting.",
    },
    "issues": [
        {"number": 1, "title": "OAuth Integration", "tasks": [1, 2]},
        {"number": 2, "title": "Session Management", "tasks": [3, 4]},
        {"number": 3, "title": "Rate Limiting", "tasks": [5]},
    ],
    "tasks": [
        {
            "number": 1,
            "title": "Configure OAuth providers",
            "description": "Set up Google and GitHub OAuth providers.",
            "priority": 1,
            "depends_on_tasks": [],
            "depends_on_holes": [],
            "spec_traces": ["SPEC-01.01", "SPEC-01.02"],
            "context_files": [
                {"path": "src/auth/oauth.py", "reason": "OAuth module", "estimated_tokens": 800}
            ],
            "acceptance_criteria": [
                "OAuth config loads from env vars",
                "Unit tests for missing config",
            ],
            "produces": ["src/auth/oauth.py"],
            "estimated_tokens": {"overhead": 2000, "implementation": 10000, "tests": 4000, "total": 16000},
            "orchestration": {
                "parallel_group": "foundation",
                "estimated_wall_minutes": "5-10",
                "can_run_with": [2],
                "blocks": [3, 4],
            },
        },
        {
            "number": 2,
            "title": "Implement PKCE flow",
            "description": "PKCE challenge/verifier generation.",
            "priority": 1,
            "depends_on_tasks": [],
            "depends_on_holes": [],
            "spec_traces": ["SPEC-01.01"],
            "context_files": [],
            "acceptance_criteria": ["PKCE verifier is 64+ chars"],
            "produces": ["src/auth/pkce.py"],
            "estimated_tokens": {"overhead": 1500, "implementation": 8000, "tests": 3000, "total": 12500},
            "orchestration": {
                "parallel_group": "foundation",
                "can_run_with": [1],
                "blocks": [3],
            },
        },
        {
            "number": 3,
            "title": "Token exchange endpoint",
            "description": "Exchange OAuth code for tokens.",
            "priority": 1,
            "depends_on_tasks": [1, 2],
            "depends_on_holes": ["H001"],
            "spec_traces": ["SPEC-01.01"],
            "context_files": [],
            "acceptance_criteria": ["Returns access + refresh tokens"],
            "produces": ["src/auth/token.py"],
            "estimated_tokens": {"overhead": 2500, "implementation": 20000, "tests": 8000, "total": 30500},
            "orchestration": {
                "parallel_group": "core",
                "blocks": [4],
            },
        },
        {
            "number": 4,
            "title": "Session management",
            "description": "Create sessions from tokens, handle expiry.",
            "priority": 2,
            "depends_on_tasks": [3],
            "depends_on_holes": [],
            "spec_traces": ["SPEC-02.01", "SPEC-02.02"],
            "context_files": [],
            "acceptance_criteria": ["Sessions expire after 8h", "Password change invalidates sessions"],
            "produces": ["src/auth/session.py"],
            "estimated_tokens": {"overhead": 2000, "implementation": 15000, "tests": 6000, "total": 23000},
            "orchestration": {"parallel_group": "post-core"},
        },
        {
            "number": 5,
            "title": "Rate limiter",
            "description": "Sliding window rate limiter for auth endpoints.",
            "priority": 1,
            "depends_on_tasks": [],
            "depends_on_holes": [],
            "spec_traces": ["SPEC-03.01"],
            "context_files": [],
            "acceptance_criteria": ["100 req/min enforced"],
            "produces": ["src/auth/ratelimit.py"],
            "estimated_tokens": {"overhead": 1800, "implementation": 18000, "tests": 7000, "total": 26800},
            "orchestration": {
                "parallel_group": "foundation",
                "can_run_with": [1, 2],
            },
        },
    ],
    "holes": [
        {
            "number": "H001",
            "title": "Session behavior on token revocation",
            "hole_type": "clarification",
            "priority": 1,
            "known": {
                "input": "User with active session + revoked token",
                "output": "[? error/redirect/logout]",
                "constraints": ["Must not leave orphaned sessions"],
                "related_types": ["Session", "Token"],
            },
            "unknown": [
                "Eager vs lazy invalidation?",
                "UX: error page, re-auth, or redirect?",
            ],
            "blocks_tasks": [3],
            "resolution_method": "human_input",
            "traces": ["SPEC-02.02"],
            "estimated_resolution_effort": "low",
        },
    ],
    "parallel_groups": [
        {"name": "foundation", "tasks": [1, 2, 5], "rationale": "Independent, no deps"},
        {"name": "core", "tasks": [3], "rationale": "Depends on foundation"},
        {"name": "post-core", "tasks": [4], "rationale": "Depends on core"},
    ],
    "coverage": {
        "requirements_total": 5,
        "requirements_covered": 5,
        "requirements_with_holes": 1,
        "uncovered": [],
    },
}


class TestSpecAnalysis:
    """Step 1: Read and analyze a spec file."""

    def test_read_spec_files(self, tmp_path: Path) -> None:
        spec_file = tmp_path / "auth.md"
        spec_file.write_text(FIXTURE_SPEC)

        bundle = read_spec_files([spec_file])
        assert len(bundle.files) == 1
        assert bundle.total_tokens > 0
        assert "SPEC-01.01" in bundle.all_spec_ids
        assert "SPEC-03.01" in bundle.all_spec_ids
        assert not bundle.needs_sharding


class TestValidation:
    """Step 2: Validate decomposition JSON."""

    def test_validates_fixture(self) -> None:
        raw = json.dumps(FIXTURE_DECOMPOSITION)
        result = parse_decomposition_output(raw)
        assert result.is_valid, f"Errors: {result.errors}"

    def test_dag_valid(self) -> None:
        errors = validate_dag(
            FIXTURE_DECOMPOSITION["tasks"],
            FIXTURE_DECOMPOSITION["holes"],
        )
        assert errors == []

    def test_coverage_complete(self) -> None:
        traces = set()
        for t in FIXTURE_DECOMPOSITION["tasks"]:
            traces.update(t.get("spec_traces", []))
        # All SPEC IDs from fixture spec are covered
        for sid in ["SPEC-01.01", "SPEC-01.02", "SPEC-02.01", "SPEC-02.02", "SPEC-03.01"]:
            assert sid in traces

    def test_topological_sort(self) -> None:
        order = topological_sort(FIXTURE_DECOMPOSITION["tasks"])
        # topological_sort returns list of task numbers (ints)
        assert len(order) == len(FIXTURE_DECOMPOSITION["tasks"])
        # 1, 2, 5 (no deps) come before 3, 4
        assert order.index(1) < order.index(3)
        assert order.index(2) < order.index(3)
        assert order.index(3) < order.index(4)


class TestBeadsOutput:
    """Step 3: Generate Beads output (plan + script)."""

    def test_end_to_end_beads(self, tmp_path: Path) -> None:
        plan_md, plan_sh = write_beads_output(
            FIXTURE_DECOMPOSITION,
            output_dir=tmp_path,
        )
        assert plan_md.exists()
        assert plan_sh.exists()

        md_content = plan_md.read_text()
        assert "Authentication System" in md_content
        assert "Configure OAuth" in md_content
        assert "H001" in md_content

        sh_content = plan_sh.read_text()
        assert "#!/usr/bin/env bash" in sh_content
        assert "set -euo pipefail" in sh_content
        assert "bd create" in sh_content
        assert "bd dep add" in sh_content


class TestMarkdownOutput:
    """Step 4: Generate Markdown output (task files + state.yaml)."""

    def test_end_to_end_markdown(self, tmp_path: Path) -> None:
        out = write_markdown_output(
            FIXTURE_DECOMPOSITION,
            output_dir=tmp_path / "tasks",
            spec_files=["docs/spec/auth.md"],
        )
        assert out.exists()

        # Check task files
        task_files = list((out / "tasks").glob("*.md"))
        assert len(task_files) == 5

        # Check hole files
        hole_files = list((out / "holes").glob("*.md"))
        assert len(hole_files) == 1

        # Check state.yaml
        state_path = out / "state.yaml"
        assert state_path.exists()
        state = yaml.safe_load(state_path.read_text())
        assert state["version"] == 1
        assert len(state["tasks"]) == 5
        assert len(state["holes"]) == 1
        assert state["spec_hash"].startswith("sha256:")


class TestDiff:
    """Step 5: Diff existing state against updated decomposition."""

    def test_diff_from_state_yaml(self, tmp_path: Path) -> None:
        # First: generate original state
        write_markdown_output(
            FIXTURE_DECOMPOSITION,
            output_dir=tmp_path / "tasks",
            spec_files=["docs/spec/auth.md"],
        )

        # Load state and create snapshots
        state_path = tmp_path / "tasks" / "state.yaml"
        existing = snapshot_from_state_yaml(state_path)
        assert len(existing) >= 5  # 5 tasks + 1 hole

        # Simulate spec change: modify task 5 title
        modified_data = json.loads(json.dumps(FIXTURE_DECOMPOSITION))
        modified_data["tasks"][4]["title"] = "Rate limiter (updated to 50/min)"
        modified_data["tasks"][4]["description"] = "Updated: 50 requests/minute."
        # Add a new task
        modified_data["tasks"].append({
            "number": 6,
            "title": "SAML SSO integration",
            "description": "Add SAML SSO support.",
            "priority": 2,
            "depends_on_tasks": [3],
            "depends_on_holes": [],
            "spec_traces": [],
            "context_files": [],
            "acceptance_criteria": ["SAML login works"],
            "produces": ["src/auth/saml.py"],
            "estimated_tokens": {"total": 25000},
        })

        # Compute diff
        diff_result = compute_diff(existing, modified_data)
        assert len(diff_result.new) >= 1  # At least the new SAML task
        # DiffResult has category properties but no summary() method
        assert len(diff_result.items) + len(diff_result.hole_changes) > 0

        # Write diff output
        diff_md, diff_sh = write_diff_output(
            diff_result,
            spec_source="docs/spec/auth.md",
            output_dir=tmp_path,
            existing_tasks=existing,
        )
        assert diff_md.exists()
        assert diff_sh.exists()
        assert "SAML" in diff_md.read_text()


class TestOrchestration:
    """Step 6: Generate orchestration scripts."""

    def test_orchestration_output(self, tmp_path: Path) -> None:
        paths = write_orchestration_output(
            FIXTURE_DECOMPOSITION,
            parallel_slots=4,
            output_dir=tmp_path,
            include_pull_loop=True,
        )
        assert len(paths) == 2
        assert (tmp_path / "orchestrate.sh").exists()
        assert (tmp_path / "pull-loop.sh").exists()

        orch = (tmp_path / "orchestrate.sh").read_text()
        assert "Phase 1: foundation" in orch
        assert "PARALLEL_SLOTS=${PARALLEL_SLOTS:-4}" in orch
        assert "Verifying Phase" in orch

        pull = (tmp_path / "pull-loop.sh").read_text()
        assert "bd ready" in pull
        assert "hole:agent-resolvable" in pull


class TestProgressReport:
    """Step 7: Generate progress reports from project state."""

    def _build_state(self) -> ProjectState:
        """Build a realistic project state from fixture data."""
        tasks = [
            TaskState(
                id="bd-001",
                title="Configure OAuth providers",
                status="closed",
                labels=[],
                blocked_by=[],
                is_hole=False,
            ),
            TaskState(
                id="bd-002",
                title="Implement PKCE flow",
                status="closed",
                labels=[],
                blocked_by=[],
                is_hole=False,
            ),
            TaskState(
                id="bd-003",
                title="Token exchange endpoint",
                status="in_progress",
                labels=[],
                blocked_by=["bd-h001"],
                is_hole=False,
            ),
            TaskState(
                id="bd-004",
                title="Session management",
                status="open",
                labels=[],
                blocked_by=["bd-003"],
                is_hole=False,
            ),
            TaskState(
                id="bd-005",
                title="Rate limiter",
                status="open",
                labels=[],
                blocked_by=[],
                is_hole=False,
            ),
            TaskState(
                id="bd-h001",
                title="Session behavior on token revocation",
                status="open",
                labels=["hole", "hole:clarification"],
                blocked_by=[],
                is_hole=True,
            ),
        ]
        return ProjectState(
            tasks=tasks,
            git=GitState(
                current_branch="feat/auth",
                recent_commits=[
                    {"hash": "abc123", "message": "feat: configure OAuth"},
                ],
                files_changed=["src/auth/oauth.py", "tests/test_oauth.py"],
            ),
        )

    def test_report_generation(self, tmp_path: Path) -> None:
        state = self._build_state()
        md_path, json_path = write_report(
            state,
            trigger_reason="on_demand",
            epic_title="Authentication System",
            output_dir=tmp_path,
        )

        assert md_path.exists()
        assert json_path.exists()

        md = md_path.read_text()
        assert "Authentication System" in md
        assert "2/5 tasks" in md or "40%" in md
        assert "H001" in md or "token revocation" in md.lower()

        json_data = json.loads(json_path.read_text())
        assert json_data["tasks"]["total"] == 5
        assert json_data["tasks"]["completed"] == 2
        assert json_data["epic_progress"] == pytest.approx(0.4)

    def test_trigger_evaluation(self) -> None:
        prev_state = ProjectState(
            tasks=[
                TaskState(id="1", title="T1", status="open", labels=[], blocked_by=[], is_hole=False),
                TaskState(id="2", title="T2", status="open", labels=[], blocked_by=[], is_hole=False),
            ],
        )
        curr_state = ProjectState(
            tasks=[
                TaskState(id="1", title="T1", status="closed", labels=[], blocked_by=[], is_hole=False),
                TaskState(id="2", title="T2", status="open", labels=[], blocked_by=[], is_hole=False),
            ],
        )

        config = ProgressReportConfig.load(None).triggers
        config.tasks_completed = 1

        result = evaluate_triggers(
            config,
            prev_state=prev_state,
            curr_state=curr_state,
        )
        assert result.should_report
        assert "tasks_completed" in result.fired

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """Full pipeline: spec → validate → beads → markdown → diff → report."""
        # 1. Write spec
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(FIXTURE_SPEC)

        # 2. Read spec
        bundle = read_spec_files([spec_file])
        assert bundle.total_tokens > 0

        # 3. Validate decomposition
        raw = json.dumps(FIXTURE_DECOMPOSITION)
        result = parse_decomposition_output(raw)
        assert result.is_valid

        # 4. Generate beads output
        beads_dir = tmp_path / "beads"
        beads_dir.mkdir()
        plan_md, plan_sh = write_beads_output(
            FIXTURE_DECOMPOSITION, output_dir=beads_dir
        )
        assert plan_md.exists()

        # 5. Generate markdown output
        md_dir = tmp_path / "tasks"
        write_markdown_output(
            FIXTURE_DECOMPOSITION,
            output_dir=md_dir,
            spec_files=[str(spec_file)],
        )

        # 6. Compute diff (simulating no changes)
        existing = snapshot_from_state_yaml(md_dir / "state.yaml")
        diff_result = compute_diff(existing, FIXTURE_DECOMPOSITION)
        # state.yaml doesn't store descriptions, so the diff sees "description updated"
        # for all matched tasks. They get classified as MODIFIED, not UNCHANGED.
        # The important thing is that all items are accounted for (matched, not NEW/REMOVED).
        total_matched = len(diff_result.unchanged) + len(diff_result.modified) + len(diff_result.dependency_changed)
        assert total_matched >= len(FIXTURE_DECOMPOSITION["tasks"])

        # 7. Generate progress report
        state = self._build_state()
        report_dir = tmp_path / "progress"
        md_path, json_path = write_report(
            state,
            trigger_reason="pipeline_test",
            epic_title="Auth System",
            output_dir=report_dir,
        )
        assert md_path.exists()
        assert json_path.exists()

        # 8. Verify symlink
        latest = report_dir / "latest.md"
        assert latest.exists()
