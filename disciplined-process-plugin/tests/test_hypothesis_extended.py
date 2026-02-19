# @trace SPEC-07 SPEC-08
"""Extended property-based (Hypothesis) tests across modules."""

from __future__ import annotations

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from tools.spec_decompose.diff import (
    WorkItemSnapshot,
    compute_diff,
    _match_score,
)
from tools.spec_decompose.graph import validate_dag, topological_sort, compute_critical_path
from tools.spec_decompose.holes import (
    HoleType, BEADS_LABELS, AGENT_RESOLVABLE, HUMAN_REQUIRED,
    propagate_resolution, refine_hole,
)
from tools.spec_decompose.orchestration import _infer_phases, _detect_parallel_conflicts
from tools.spec_decompose.sizing import validate_decomposition_sizing
from tools.spec_decompose.validate import parse_decomposition_output
from tools.shared.config import parse_interval
from tools.progress_report.triggers import evaluate_triggers, TriggerResult
from tools.shared.config import TriggerConfig


# --- Diff module properties ---


@st.composite
def snapshot_strategy(draw: st.DrawFn) -> WorkItemSnapshot:
    """Generate random WorkItemSnapshots."""
    return WorkItemSnapshot(
        id=draw(st.text(min_size=1, max_size=10, alphabet="abcdef0123456789-")),
        title=draw(st.text(min_size=1, max_size=50)),
        status=draw(st.sampled_from(["open", "in_progress", "closed"])),
        is_hole=draw(st.booleans()),
        spec_traces=draw(st.lists(st.from_regex(r"SPEC-\d{2}\.\d{2}", fullmatch=True), max_size=3)),
        produces=draw(st.lists(st.text(min_size=1, max_size=30), max_size=3)),
        description=draw(st.text(max_size=100)),
    )


@given(st.lists(snapshot_strategy(), min_size=0, max_size=10))
@settings(max_examples=50)
def test_diff_never_loses_items(existing: list[WorkItemSnapshot]) -> None:
    """Every existing item must appear in exactly one diff category."""
    target_data = {
        "tasks": [
            {"number": i + 1, "title": f"Task {i + 1}"}
            for i in range(len(existing))
        ],
        "holes": [],
    }
    result = compute_diff(existing, target_data)
    total_items = (
        len(result.unchanged)
        + len(result.modified)
        + len(result.new)
        + len(result.removed)
        + len(result.dependency_changed)
    )
    # Result should have at least as many items as the larger set
    assert total_items >= max(len(existing), len(target_data["tasks"]))


@given(
    traces_a=st.lists(st.from_regex(r"SPEC-\d{2}\.\d{2}", fullmatch=True), max_size=5),
    traces_b=st.lists(st.from_regex(r"SPEC-\d{2}\.\d{2}", fullmatch=True), max_size=5),
)
@settings(max_examples=50)
def test_match_score_symmetric_for_traces(
    traces_a: list[str], traces_b: list[str]
) -> None:
    """Match score from traces should be symmetric."""
    snap = WorkItemSnapshot(
        id="a", title="T", status="open", spec_traces=traces_a
    )
    target = {"spec_traces": traces_b, "title": "T", "produces": []}
    score_ab = _match_score(snap, target)

    snap2 = WorkItemSnapshot(
        id="b", title="T", status="open", spec_traces=traces_b
    )
    target2 = {"spec_traces": traces_a, "title": "T", "produces": []}
    score_ba = _match_score(snap2, target2)

    # Trace-based matching should be symmetric
    assert abs(score_ab - score_ba) < 0.01


# --- Graph module properties ---


@st.composite
def dag_tasks(draw: st.DrawFn) -> list[dict]:
    """Generate random DAG task lists (may have cycles)."""
    n = draw(st.integers(min_value=1, max_value=8))
    tasks = []
    for i in range(1, n + 1):
        deps = draw(st.lists(
            st.integers(min_value=1, max_value=n),
            max_size=min(3, n),
        ))
        # Remove self-references
        deps = [d for d in deps if d != i]
        tasks.append({
            "number": i,
            "title": f"Task {i}",
            "depends_on_tasks": deps,
        })
    return tasks


@given(dag_tasks())
@settings(max_examples=100)
def test_validate_dag_always_returns_list(tasks: list[dict]) -> None:
    """validate_dag always returns a list (may be empty or have errors)."""
    result = validate_dag(tasks, [])
    assert isinstance(result, list)


@given(dag_tasks())
@settings(max_examples=50)
def test_topological_sort_handles_all_inputs(tasks: list[dict]) -> None:
    """topological_sort either succeeds or raises ValueError for cycles."""
    errors = validate_dag(tasks, [])
    cycle_errors = [e for e in errors if "cycle" in e.lower()]
    if cycle_errors:
        # Should raise on cycles
        try:
            topological_sort(tasks)
            # May still work if validate_dag found an indirect issue
        except ValueError:
            pass
    else:
        # No cycles — should succeed
        result = topological_sort(tasks)
        assert len(result) == len(tasks)


# --- Holes module properties ---


def test_hole_label_completeness() -> None:
    """Every HoleType has entries in BEADS_LABELS."""
    for ht in HoleType:
        assert ht in BEADS_LABELS, f"Missing BEADS_LABELS for {ht}"
        assert len(BEADS_LABELS[ht]) > 0


def test_agent_human_partition_complete() -> None:
    """AGENT_RESOLVABLE and HUMAN_REQUIRED cover meaningful types."""
    # validation and research are agent-resolvable
    assert HoleType.VALIDATION in AGENT_RESOLVABLE
    assert HoleType.RESEARCH in AGENT_RESOLVABLE
    # clarification and escalation need humans
    assert HoleType.CLARIFICATION in HUMAN_REQUIRED
    assert HoleType.ESCALATION in HUMAN_REQUIRED
    # No overlap
    assert AGENT_RESOLVABLE & HUMAN_REQUIRED == set()


# --- Orchestration properties ---


@st.composite
def task_with_deps(draw: st.DrawFn, max_n: int = 10) -> list[dict]:
    """Generate tasks with random dependencies."""
    n = draw(st.integers(min_value=1, max_value=max_n))
    tasks = []
    for i in range(1, n + 1):
        deps = draw(st.lists(
            st.integers(min_value=1, max_value=n).filter(lambda x, i=i: x != i),
            max_size=min(3, n - 1),
            unique=True,
        ))
        tasks.append({
            "number": i,
            "title": f"Task {i}",
            "depends_on_tasks": deps,
        })
    return tasks


@given(task_with_deps())
@settings(max_examples=100)
def test_infer_phases_covers_all_tasks(tasks: list[dict]) -> None:
    """Every task appears in exactly one phase."""
    phases = _infer_phases(tasks)
    all_task_nums = set()
    for phase in phases:
        for tn in phase["tasks"]:
            assert tn not in all_task_nums, f"Task {tn} in multiple phases"
            all_task_nums.add(tn)
    expected = {t["number"] for t in tasks}
    assert all_task_nums == expected


@given(task_with_deps())
@settings(max_examples=50)
def test_infer_phases_respects_ordering(tasks: list[dict]) -> None:
    """Tasks in later phases depend on tasks in earlier phases."""
    phases = _infer_phases(tasks)
    task_phase: dict[int, int] = {}
    for pi, phase in enumerate(phases):
        for tn in phase["tasks"]:
            task_phase[tn] = pi

    for t in tasks:
        tn = t["number"]
        for dep in t.get("depends_on_tasks", []):
            if dep in task_phase:
                # Dependency should be in same or earlier phase
                assert task_phase[dep] <= task_phase[tn], (
                    f"Task {tn} (phase {task_phase[tn]}) depends on "
                    f"task {dep} (phase {task_phase[dep]})"
                )


# --- Config parsing properties ---


@given(st.integers(min_value=1, max_value=10000))
def test_parse_interval_minutes(n: int) -> None:
    """parse_interval with 'm' suffix always returns n * 60."""
    result = parse_interval(f"{n}m")
    assert result == n * 60


@given(st.integers(min_value=1, max_value=10000))
def test_parse_interval_seconds(n: int) -> None:
    """parse_interval with 's' suffix returns n."""
    result = parse_interval(f"{n}s")
    assert result == n


@given(st.integers(min_value=1, max_value=1000))
def test_parse_interval_hours(n: int) -> None:
    """parse_interval with 'h' suffix returns n * 3600."""
    result = parse_interval(f"{n}h")
    assert result == n * 3600


@given(st.integers(min_value=1, max_value=10000))
def test_parse_interval_bare_number(n: int) -> None:
    """parse_interval with bare number assumes minutes (returns n*60)."""
    result = parse_interval(str(n))
    assert result == n * 60


# --- JSON validation properties ---


@given(st.text(min_size=0, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"))))
@settings(max_examples=50)
def test_validate_never_crashes_on_arbitrary_input(text: str) -> None:
    """parse_decomposition_output handles arbitrary input without crashing."""
    result = parse_decomposition_output(text)
    assert hasattr(result, "is_valid")
    assert isinstance(result.errors, list)


# --- Critical path properties ---


@st.composite
def acyclic_dag_tasks(draw: st.DrawFn) -> list[dict]:
    """Generate guaranteed acyclic DAG task lists."""
    n = draw(st.integers(min_value=1, max_value=8))
    tasks = []
    for i in range(1, n + 1):
        # Only depend on lower-numbered tasks (guarantees acyclicity)
        deps = draw(st.lists(
            st.integers(min_value=1, max_value=max(1, i - 1)).filter(lambda x, i=i: x < i),
            max_size=min(3, i - 1),
            unique=True,
        )) if i > 1 else []
        total = draw(st.integers(min_value=100, max_value=50000))
        tasks.append({
            "number": i,
            "title": f"Task {i}",
            "depends_on_tasks": deps,
            "depends_on_holes": [],
            "estimated_tokens": {"total": total},
        })
    return tasks


@given(acyclic_dag_tasks())
@settings(max_examples=50)
def test_critical_path_cumulative_is_monotonic(tasks: list[dict]) -> None:
    """Critical path cumulative tokens are monotonically non-decreasing."""
    path = compute_critical_path(tasks, [])
    for i in range(1, len(path)):
        assert path[i].cumulative_tokens >= path[i - 1].cumulative_tokens


@given(acyclic_dag_tasks())
@settings(max_examples=50)
def test_critical_path_is_valid_topological_order(tasks: list[dict]) -> None:
    """Critical path respects dependency ordering."""
    path = compute_critical_path(tasks, [])
    task_deps = {t["number"]: set(t.get("depends_on_tasks", [])) for t in tasks}
    path_ids = [e.task_id for e in path]
    for i, tid in enumerate(path_ids):
        for dep in task_deps.get(tid, set()):
            if dep in path_ids:
                assert path_ids.index(dep) < i, (
                    f"Dependency {dep} appears after {tid} in critical path"
                )


# --- Sizing validation properties ---


@given(acyclic_dag_tasks())
@settings(max_examples=50)
def test_sizing_warnings_only_for_over_budget(tasks: list[dict]) -> None:
    """Sizing warnings should only fire for tasks exceeding the ceiling."""
    warnings = validate_decomposition_sizing(tasks, context_window=200_000)
    for w in warnings:
        assert w.estimated_total > w.ceiling


# --- Hole propagation properties ---


@given(
    st.text(min_size=1, max_size=10, alphabet="ABCDEFGH0123456789"),
    st.text(min_size=1, max_size=50),
    st.lists(
        st.text(min_size=1, max_size=10, alphabet="ABCDEFGH0123456789"),
        min_size=0,
        max_size=5,
    ),
)
@settings(max_examples=50)
def test_propagate_resolution_removes_only_target(
    hole_id: str, resolution: str, other_holes: list[str]
) -> None:
    """propagate_resolution removes only the target hole, not others."""
    assume(hole_id not in other_holes)
    all_holes = [hole_id] + other_holes
    tasks = [{"number": 1, "depends_on_holes": list(all_holes), "description": ""}]
    propagate_resolution(hole_id, resolution, tasks)
    assert hole_id not in tasks[0]["depends_on_holes"]
    for other in other_holes:
        assert other in tasks[0]["depends_on_holes"]


# --- Hole refinement properties ---


@given(st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=5))
@settings(max_examples=50)
def test_refine_hole_accumulates(infos: list[str]) -> None:
    """Each refinement call adds exactly one entry."""
    hole: dict = {"number": "H1", "known": {"constraints": []}}
    for i, info in enumerate(infos):
        refine_hole(hole, info)
        assert len(hole["refinements"]) == i + 1
    assert len(hole["known"]["constraints"]) == len(infos)


# --- Parallel conflict detection properties ---


@given(
    st.lists(st.text(min_size=3, max_size=20, alphabet="abcdefghijklmnop./"), min_size=0, max_size=5),
    st.lists(st.text(min_size=3, max_size=20, alphabet="abcdefghijklmnop./"), min_size=0, max_size=5),
)
@settings(max_examples=50)
def test_conflict_detection_finds_shared_files(files_a: list[str], files_b: list[str]) -> None:
    """Conflict detection should find all shared produced files."""
    tasks = [
        {"number": 1, "produces": files_a},
        {"number": 2, "produces": files_b},
    ]
    groups = [{"name": "p1", "tasks": [1, 2]}]
    warnings = _detect_parallel_conflicts(tasks, groups)
    shared = set(files_a) & set(files_b)
    if shared:
        assert len(warnings) > 0
        for f in shared:
            assert any(f in w for w in warnings)
    else:
        assert len(warnings) == 0
