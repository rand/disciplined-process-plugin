# @trace SPEC-07
"""DAG validation, cycle detection, and coverage checking for decomposition graphs.

The decomposition produces a directed acyclic graph (DAG) of tasks and holes.
This module validates that graph for structural correctness before output
generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CoverageResult:
    """Result of checking requirement-to-task coverage."""

    requirements_total: int
    requirements_covered: int
    requirements_with_holes: int
    uncovered: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return len(self.uncovered) == 0

    @property
    def coverage_ratio(self) -> float:
        if self.requirements_total == 0:
            return 1.0
        return self.requirements_covered / self.requirements_total


def validate_dag(
    tasks: list[dict[str, Any]], holes: list[dict[str, Any]]
) -> list[str]:
    """Validate that tasks and holes form a valid DAG.

    Checks:
    - No circular dependencies
    - All dependency references exist
    - No self-references
    - Holes are properly wired into the graph

    Args:
        tasks: List of task dicts with 'number' and 'depends_on_tasks' keys.
        holes: List of hole dicts with 'number' and 'blocks_tasks' keys.

    Returns:
        List of error strings. Empty list means valid DAG.
    """
    errors: list[str] = []

    # Build the set of all node IDs (tasks use int numbers, holes use string like "H001")
    task_ids: set[int | str] = set()
    for task in tasks:
        task_ids.add(task["number"])
    hole_ids: set[str] = set()
    for hole in holes:
        hole_ids.add(hole["number"])
    all_ids = task_ids | hole_ids

    # Build adjacency list: node -> set of nodes it depends on
    graph: dict[int | str, set[int | str]] = {}

    for task in tasks:
        num = task["number"]
        deps: set[int | str] = set()

        # Task-to-task dependencies
        for dep in task.get("depends_on_tasks", []):
            if dep == num:
                errors.append(f"Task {num} depends on itself")
            elif dep not in task_ids:
                errors.append(f"Task {num} depends on non-existent task {dep}")
            else:
                deps.add(dep)

        # Task-to-hole dependencies
        for dep in task.get("depends_on_holes", []):
            if dep not in hole_ids:
                errors.append(f"Task {num} depends on non-existent hole {dep}")
            else:
                deps.add(dep)

        graph[num] = deps

    # Holes can also block tasks (reverse direction represented differently)
    # Validate that hole's blocks_tasks references exist
    for hole in holes:
        hnum = hole["number"]
        graph.setdefault(hnum, set())
        for blocked_task in hole.get("blocks_tasks", []):
            if blocked_task not in task_ids:
                errors.append(
                    f"Hole {hnum} claims to block non-existent task {blocked_task}"
                )

    # Cycle detection using DFS with coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[int | str, int] = {node: WHITE for node in graph}

    def dfs(node: int | str) -> bool:
        """Returns True if a cycle is found."""
        color[node] = GRAY
        for neighbor in graph.get(node, set()):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                errors.append(f"Cycle detected involving {node} -> {neighbor}")
                return True
            if color[neighbor] == WHITE:
                if dfs(neighbor):
                    return True
        color[node] = BLACK
        return False

    for node in list(graph.keys()):
        if color.get(node) == WHITE:
            if dfs(node):
                break  # One cycle report is sufficient

    return errors


def check_coverage(
    requirements: list[dict[str, Any]], tasks: list[dict[str, Any]]
) -> CoverageResult:
    """Check that every requirement maps to at least one task.

    Args:
        requirements: List of requirement dicts with 'id' key.
        tasks: List of task dicts with 'spec_traces' key (list of requirement IDs).

    Returns:
        CoverageResult with coverage statistics.
    """
    req_ids = {r["id"] for r in requirements}

    # Build set of all covered requirement IDs
    covered: set[str] = set()
    for task in tasks:
        for trace in task.get("spec_traces", []):
            covered.add(trace)

    # Also check holes for traces (holes may cover requirements too)
    uncovered = sorted(req_ids - covered)

    # Count requirements with holes (covered but with uncertainty)
    with_holes = 0
    for task in tasks:
        if task.get("depends_on_holes"):
            for trace in task.get("spec_traces", []):
                if trace in req_ids:
                    with_holes += 1

    return CoverageResult(
        requirements_total=len(req_ids),
        requirements_covered=len(req_ids) - len(uncovered),
        requirements_with_holes=with_holes,
        uncovered=uncovered,
    )


def check_reachability(tasks: list[dict[str, Any]]) -> list[int | str]:
    """Find orphaned tasks — tasks with no path from any root task.

    A root task is one with no dependencies. All other tasks should be
    reachable from at least one root.

    Args:
        tasks: List of task dicts with 'number' and 'depends_on_tasks' keys.

    Returns:
        List of orphaned task IDs (unreachable from any root).
    """
    if not tasks:
        return []

    # Build reverse adjacency: task -> tasks that depend on it
    all_ids = {t["number"] for t in tasks}
    dependents: dict[int | str, set[int | str]] = {tid: set() for tid in all_ids}

    roots: set[int | str] = set(all_ids)

    for task in tasks:
        num = task["number"]
        deps = task.get("depends_on_tasks", [])
        for dep in deps:
            if dep in all_ids:
                dependents[dep].add(num)
                roots.discard(num)

    # Also exclude tasks that depend on holes from being considered orphaned
    # (they're connected through the hole graph)
    for task in tasks:
        if task.get("depends_on_holes"):
            roots.discard(task["number"])

    if not roots:
        # All tasks have dependencies — could be valid if connected
        # Fall back to checking if all are in one connected component
        roots = {tasks[0]["number"]}

    # BFS from roots
    reachable: set[int | str] = set()
    queue = list(roots)
    while queue:
        node = queue.pop(0)
        if node in reachable:
            continue
        reachable.add(node)
        for dep in dependents.get(node, set()):
            if dep not in reachable:
                queue.append(dep)

    orphaned = sorted(all_ids - reachable, key=lambda x: (isinstance(x, str), x))
    return orphaned


@dataclass
class CriticalPathEntry:
    """One node on the critical path."""

    task_id: int | str
    cumulative_tokens: int


def compute_critical_path(
    tasks: list[dict[str, Any]],
    holes: list[dict[str, Any]] | None = None,
) -> list[CriticalPathEntry]:
    """Compute the critical (longest) path through the task DAG.

    Uses topological sort + longest-path DP with estimated_tokens as weight.

    Args:
        tasks: Task dicts with 'number', 'depends_on_tasks', 'estimated_tokens'.
        holes: Optional hole dicts (treated as zero-weight nodes).

    Returns:
        Ordered list of CriticalPathEntry from root to leaf on the longest path.
        Empty list if no tasks.
    """
    if not tasks:
        return []

    # Build node weights
    weights: dict[int | str, int] = {}
    for t in tasks:
        weights[t["number"]] = t.get("estimated_tokens", {}).get("total", 0)
    for h in (holes or []):
        weights[h["number"]] = 0

    # Build forward adjacency (dependency → dependent)
    adj: dict[int | str, list[int | str]] = {nid: [] for nid in weights}
    for t in tasks:
        for dep in t.get("depends_on_tasks", []):
            if dep in weights:
                adj.setdefault(dep, []).append(t["number"])
        for dep in t.get("depends_on_holes", []):
            if dep in weights:
                adj.setdefault(dep, []).append(t["number"])

    # Topological order
    try:
        topo = topological_sort(tasks)
    except ValueError:
        return []

    # Include holes at the front of topo if not already present
    topo_set = set(topo)
    for h in (holes or []):
        if h["number"] not in topo_set:
            topo.insert(0, h["number"])

    # DP: dist[node] = max cumulative weight to reach this node
    dist: dict[int | str, int] = {nid: weights.get(nid, 0) for nid in weights}
    pred: dict[int | str, int | str | None] = {nid: None for nid in weights}

    for node in topo:
        for neighbor in adj.get(node, []):
            candidate = dist[node] + weights.get(neighbor, 0)
            if candidate > dist.get(neighbor, 0):
                dist[neighbor] = candidate
                pred[neighbor] = node

    # Find the endpoint with maximum distance
    if not dist:
        return []
    end_node = max(dist, key=lambda n: dist[n])

    # Trace back from end to start
    path: list[int | str] = []
    current: int | str | None = end_node
    while current is not None:
        path.append(current)
        current = pred.get(current)
    path.reverse()

    return [
        CriticalPathEntry(task_id=nid, cumulative_tokens=dist[nid])
        for nid in path
    ]


def topological_sort(tasks: list[dict[str, Any]]) -> list[int | str]:
    """Return task numbers in dependency-respecting order (Kahn's algorithm).

    Args:
        tasks: List of task dicts with 'number' and 'depends_on_tasks' keys.

    Returns:
        List of task numbers in topological order.

    Raises:
        ValueError: If the graph has cycles.
    """
    # Build in-degree map and adjacency
    in_degree: dict[int | str, int] = {}
    adj: dict[int | str, list[int | str]] = {}
    all_ids: set[int | str] = set()

    for task in tasks:
        num = task["number"]
        all_ids.add(num)
        in_degree.setdefault(num, 0)
        adj.setdefault(num, [])

    for task in tasks:
        num = task["number"]
        for dep in task.get("depends_on_tasks", []):
            if dep in all_ids:
                adj.setdefault(dep, []).append(num)
                in_degree[num] = in_degree.get(num, 0) + 1

    # Kahn's algorithm
    queue = [n for n in all_ids if in_degree.get(n, 0) == 0]
    queue.sort()  # Deterministic order
    result: list[int | str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in adj.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
        queue.sort()

    if len(result) != len(all_ids):
        raise ValueError("Graph has cycles — cannot topologically sort")

    return result
