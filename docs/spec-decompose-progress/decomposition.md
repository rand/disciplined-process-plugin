# Decomposition Algorithm

**Parent:** [README.md](./README.md)  
**Related:** [holes.md](./holes.md) · [context-sizing.md](./context-sizing.md) · [schemas.md](./schemas.md)

---

## Overview

The decomposition transforms specification documents into a directed acyclic graph of work items (tasks and [holes](./holes.md)) sized for agent context windows. The algorithm runs in five steps: Analyze, Identify Holes, Partition, Size, and Annotate.

---

## Input: The Spec

The tool reads one or more files that collectively form the spec. It does not impose a format.

```bash
spec-decompose ./docs/spec.md                              # Single file
spec-decompose ./docs/spec/*.md                            # Multiple files
spec-decompose --constitution ./docs/constitution.md ./docs/spec/*.md  # With principles
```

---

## Step 1: Analyze — Build the Requirement Graph `[ALGO-1]`

The subagent parses the spec and produces a structured requirement graph.

**Extract requirements.** Find everything that reads as a requirement: explicit `[SPEC-XX.YY]` IDs, RFC 2119 language (MUST/SHOULD/MAY), user stories, acceptance criteria, behavioral descriptions. Tag each with a stable internal ID if it doesn't already have one.

**Extract constraints.** Technology choices, performance bounds, compatibility requirements, non-functional requirements. These become context attached to relevant tasks, not tasks themselves.

**Infer dependencies** using four heuristics:

| Heuristic | Signal | Example |
|-----------|--------|---------|
| Entity dependency | A defines entity, B references it | B depends on A |
| API dependency | A defines endpoint, B calls it | B depends on A |
| Temporal language | "after," "once," "when X is complete" | Explicit ordering |
| Shared state | Requirements read/write same state | Ordering relationship |

**Output:** Structured JSON (see [schemas.md § Requirement Graph](./schemas.md#requirement-graph)).

```json
{
  "requirements": [
    {
      "id": "SPEC-03.01",
      "text": "The system MUST authenticate users via OAuth 2.0 PKCE flow.",
      "type": "functional",
      "complexity": "complex",
      "depends_on": ["SPEC-05.01"],
      "complexity_signals": {
        "conditions": 3,
        "error_cases": 4,
        "integrations": 2,
        "entities_referenced": ["User", "OAuthProvider", "Session"]
      }
    }
  ],
  "constraints": [...],
  "ambiguities": [...]
}
```

---

## Step 1b: Identify Holes `[ALGO-1b]`

For every ambiguity, underspecification, or decision point, the subagent creates a **hole** — a first-class node in the work graph. See [holes.md](./holes.md) for the full taxonomy and lifecycle.

**Decision criteria for hole creation vs. assumption:**

| Condition | Action |
|-----------|--------|
| Affects architecture or public API | Create hole (don't assume) |
| Affects only internal implementation detail | Assume, note assumption in task description |
| Ambiguous language with two very different interpretations | Create hole |
| Omitted error case | Assume standard handling; create hole only if critical |
| External dependency behavior unknown | Create `validation` hole |
| Multiple valid design approaches | Create `research` hole |

The `--holes-strategy` flag controls this behavior:

| Strategy | Behavior |
|----------|----------|
| `graph` (default) | Create holes as blocking work items |
| `warn` | Log as warnings only (legacy behavior) |
| `strict` | Fail on any ambiguity |
| `assume` | Always assume, never create holes |

---

## Step 2: Partition — Group into Implementation Clusters `[ALGO-2]`

Group requirements into candidate tasks based on implementation locality:

- Same module or file → same cluster
- CRUD operations on same resource → same cluster
- A requirement + its error handling → same cluster
- A requirement + its validation → same cluster

Then organize clusters into a hierarchy: **tasks** → **issues** (logical components) → **epics** (the full spec).

---

## Step 3: Size — Fit to Context Window `[ALGO-3]`

For each candidate task, estimate total token consumption against the target context window. See [context-sizing.md](./context-sizing.md) for the full budget model and rules.

**Estimation components:**

| Component | Method |
|-----------|--------|
| Task description | Count tokens in generated text |
| Context files | If files exist, count tokens. If not yet created, estimate from spec. |
| Implementation | Heuristic: simple ~10K, moderate ~20K, complex ~35K |
| Tests | ~40% of implementation estimate |
| Tool overhead | ~300 tokens × estimated tool calls |

Split if over budget `[SIZE-3]`. Merge if trivially small `[SIZE-4]`.

---

## Step 4: Graph — Establish Dependencies `[ALGO-4]`

Translate requirement dependencies to task dependencies. Use ONLY these relationship types:

| Relationship | Beads command | Semantics |
|-------------|---------------|-----------|
| **blocks** | `bd dep add` | Real implementation dependency — cannot start B until A is done |
| **parent-child** | `--parent` | Hierarchy (epic → issue → task) |
| **related** | `--type related` | Touches similar code, no ordering constraint |
| **discovered-from** | `--deps discovered-from:<id>` | Rework tasks and mid-flight discoveries |

Holes participate as blocking nodes: tasks that depend on a hole's answer are wired with `bd dep add` just like task-to-task dependencies. See [holes.md § Graph Participation](./holes.md#holes-in-the-work-graph).

**Validation:** The completed graph must be a DAG (no cycles), have full coverage (every requirement maps to ≥1 task), and be fully reachable.

---

## Step 5: Annotate — Generate Agent Context `[ALGO-5]`

For each task, generate:

- **Self-contained description** — an agent can work from this alone without reading the full spec
- **Spec traces** — `[SPEC-XX.YY]` references for traceability
- **Context file list** — files to read before starting, with reasons and token estimates
- **Acceptance criteria** — observable, testable conditions for completion
- **Orchestration metadata** — embedded as HTML comment for machine parsing

```html
<!-- ORCHESTRATION METADATA
parallel_group: foundation
estimated_tokens: 14800
estimated_wall_minutes: 5-10
produces: ["src/auth/validation.py", "tests/unit/test_validation.py"]
consumes: []
can_run_with: [2, 9]
blocks: [3, 4]
-->
```

This metadata is invisible to humans reading task descriptions but parseable by orchestrators. It appears in both Beads descriptions and Markdown task files.

---

## Output Generation

The decomposition produces output in one of two formats. See [cli-reference.md](./cli-reference.md) for all options.

### Beads Output (default)

Generates a **reviewable shell script** (`decompose-plan.sh`) and a **human-readable plan** (`decompose-plan.md`). The human reviews the plan, then runs the script.

This pattern exists because the Discussion #506 failure mode is agents creating a mess of improperly linked issues. The decomposition is inspectable and correctable *before* it hits the tracker.

```bash
spec-decompose ./docs/spec.md --output beads
# Produces:
#   decompose-plan.md   (human-readable plan with graph, holes, coverage, warnings)
#   decompose-plan.sh   (bd commands to execute)
#
# Review, then:
bash decompose-plan.sh
```

The generated script uses `bd create` with `--parent` for hierarchy, `bd dep add` for blocking relationships (including holes), and captures issue IDs at each step to wire dependencies correctly.

### Markdown Output

```bash
spec-decompose ./docs/spec.md --output markdown --dir ./docs/tasks/
```

Produces:

```
docs/tasks/
├── README.md                # Plan overview + dependency graph
├── epic-<n>.md              # Epic description
├── tasks/
│   ├── 001-<title>.md       # Individual task files
│   └── ...
├── holes/
│   ├── H001-<title>.md      # Individual hole files
│   └── ...
└── state.yaml               # Machine-readable state for diffing
```

Each task file contains: ID, dependencies (including holes), spec traces, description, acceptance criteria, context file list, token estimate, and status.

`state.yaml` captures the full graph in a diffable format — this is what enables principled [re-decomposition](./diff.md) in Markdown mode.

---

## Decomposition Plan Format

The human-readable plan includes both tasks and holes:

```
# Decomposition Plan

Spec: docs/spec/auth-system.md
Work items: 12 tasks + 3 holes across 3 issues under 1 epic
Estimated agent effort: ~180K tokens across all tasks
Critical path: 5 tasks + 1 hole, ~75K tokens + human decision

## Holes (resolve before or during implementation)

| # | Hole | Type | Blocks | Resolution |
|---|------|------|--------|------------|
| H1 | Session behavior on token revocation | clarification | T5, T6 | Human decision |
| H2 | S3 conditional PUT support | validation | T3 | Agent can verify |
| H3 | Rate limit algorithm choice | research | T9 | Agent → human |

## Tasks

| # | Task | Depends On | Est. Tokens | Priority |
|---|------|-----------|-------------|----------|
| 1 | Configure OAuth provider | — | ~15K | P1 |
| 2 | PKCE challenge generation | — | ~12K | P1 |
| 3 | Token exchange endpoint | 1, 2, H2 | ~25K | P1 |
| ... | | | | |

## Critical Path Analysis

Recommended resolution order:
1. H2 first (agent can do it, unblocks T3 on the critical path)
2. H1 next (human decision, blocks the most downstream work)
3. H3 can proceed in parallel with early tasks
```
