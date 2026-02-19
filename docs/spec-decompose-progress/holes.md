# Holes: First-Class Unknowns

**Parent:** [README.md](./README.md)  
**Related:** [decomposition.md](./decomposition.md) · [diff.md](./diff.md) · [agent-skills.md](./agent-skills.md) · [schemas.md](./schemas.md)

---

## Overview

A hole is a work item representing something the system doesn't yet know but needs to know before certain work can proceed. Unlike warnings (which are inert text that agents ignore), holes are **first-class nodes in the work graph** — they block downstream tasks, carry partial information about their shape, and get resolved through explicit actions.

This design draws from typed holes in the Hazel research program and RFLX: a hole isn't an opaque `[?]` — it carries partial characterization that constrains valid fillings and enables progressive refinement.

---

## Hole Properties

Every hole has:

| Property | Description |
|----------|-------------|
| **ID** | A Beads issue ID or Markdown file, like any other work item |
| **Type** | What kind of resolution is needed (see [taxonomy](#hole-taxonomy)) |
| **Known bounds** | What IS known — partial types, constraints, scope |
| **Unknown** | What specifically is missing |
| **Blocks** | Which tasks cannot proceed until this hole is filled |
| **Resolution method** | How this hole gets filled |
| **Provenance** | Where the hole was discovered (decomposition, implementation, or review) |

---

## Hole Taxonomy

### `clarification` — Human must answer a question `[HOLE-clarification]`

The spec is ambiguous or underspecified. Only a human or domain expert can resolve it.

```
Hole: What should happen when a user's OAuth token is revoked
      while they have an active session?

Known:
  - Input: User with active session + revoked OAuth token
  - Output: [? some error/redirect/logout behavior]
  - Constraint: Must not leave orphaned sessions

Unknown:
  - Eager invalidation (push) or lazy on next request (pull)?
  - User experience: error page, silent re-auth, or redirect to login?

Blocks: T005 (session revocation), T006 (session expiry)
Resolution: human_input
```

### `validation` — Something must be verified `[HOLE-validation]`

An assumption was made during decomposition that needs confirmation. The information might exist in external docs, an API, or the codebase. Binary yes/no answer.

```
Hole: Does the S3-compatible storage API support conditional PUTs?

Known:
  - We need S3-compatible storage (SPEC-IMG-04)
  - Pipeline uses optimistic concurrency
  - If not supported, we need a different strategy

Unknown:
  - Whether the specific provider supports If-None-Match headers

Blocks: T003 (S3 storage integration)
Resolution: agent_research (check provider docs) → validate → fill
```

### `research` — Deeper investigation needed `[HOLE-research]`

Unlike validation, research requires exploring options and synthesizing a recommendation.

```
Hole: What rate limiting algorithm best fits our constraints?

Known:
  - Input: HTTP requests to auth endpoints
  - Output: allow/deny decision with appropriate headers
  - Constraint: ≤100 requests/minute/user, works across instances

Unknown:
  - Sliding window vs token bucket vs leaky bucket
  - Redis vs in-memory vs distributed approach
  - Per-endpoint or global limits

Blocks: T009 (rate limiter implementation)
Resolution: agent_research → synthesis → human_approval
```

### `synthesis` — Multiple inputs must be combined `[HOLE-synthesis]`

Several resolved holes or spec sections need to be woven into a coherent design that doesn't exist yet.

```
Hole: Session–Rate Limiting interaction design

Known:
  - Sessions expire and can be revoked (SPEC-03.04-06)
  - Rate limiting applies to auth endpoints (SPEC-04.01-02)
  - Security logging captures both (SPEC-04.03)

Unknown:
  - How session operations count against rate limits
  - Whether session refresh bypasses rate limiting
  - How rate limit state interacts with session state

Blocks: T010 (rate limiting on auth endpoints), T012 (security logging)
Resolution: synthesis → human_review
```

### `escalation` — Agent hit something it can't handle `[HOLE-escalation]`

During implementation, an agent encounters a genuine decision point — not a bug, not a missing test, but a situation requiring human judgment.

```
Hole: The existing User model has a `status` field with values
      [active, inactive, suspended] but the spec describes a
      `deactivated` state that doesn't exist and behaves differently
      from `inactive`.

Known:
  - Existing code uses `inactive` for soft-delete
  - Spec describes `deactivated` as "user chose to leave, data retained 30 days"
  - These have different semantics and reactivation flows

Unknown:
  - Add a new status value or repurpose `inactive`?
  - If new value, what migration strategy?

Blocks: Current task (T005) paused pending resolution
Resolution: human_decision
Provenance: discovered-from:T005 during implementation
```

### Convenience Groupings

| Group | Includes | Who resolves |
|-------|----------|-------------|
| `agent-resolvable` | validation, research | Agents (no human needed) |
| `human-required` | clarification, escalation | Human decision-maker |
| `mixed` | synthesis | Agent prepares, human approves |

---

## Hole Lifecycle

```
IDENTIFIED ──→ OPEN ──→ IN_PROGRESS ──→ RESOLVED ──→ APPLIED
    │              │          │              │            │
    │              │          │              │            └─ Blocked tasks updated
    │              │          │              │               with resolution context
    │              │          │              │
    │              │          │              └─ Answer/decision recorded
    │              │          │                 as close reason
    │              │          │
    │              │          └─ Someone (human or agent) is
    │              │             actively working on resolution
    │              │
    │              └─ Hole exists in graph, blocking tasks,
    │                 awaiting resolution
    │
    └─ Detected during decomposition, implementation, or review
```

### Resolution Mechanics

When a hole is resolved:

1. **Record the resolution.** The answer, decision, or synthesis result is captured in the Beads close reason or Markdown resolution section.
2. **Update blocked tasks.** Review whether blocked tasks need their descriptions updated based on the resolution (e.g., if the answer is "sliding window with Redis," task T009's description should reflect that).
3. **Unblock the graph.** Close the hole; downstream tasks immediately become eligible for `bd ready`.
4. **Propagate constraints.** If the resolution adds constraints affecting other parts of the graph (e.g., choosing Redis creates a new infrastructure dependency), new tasks or holes may be created.

This is the RFLX refinement model: filling a hole may narrow constraints on other holes, may create new holes, and progressively moves the spec from incomplete to complete.

### Progressive Refinement

A hole may narrow through multiple resolution steps:

```
H003: Rate limit algorithm
  Type: research
  Unknown: Which algorithm? Which storage? Per-endpoint or global?

  ──→ Agent researches, narrows to two options:
      Sliding window + Redis  vs  Token bucket + in-memory

  ──→ H003 updated, type changed to: clarification
      Unknown (narrowed): Sliding window + Redis or Token bucket + in-memory?

  ──→ Human decides: Sliding window + Redis

  ──→ H003 resolved, T009 updated with specific implementation guidance
```

This mirrors RFLX's progressive refinement: `[?] → [? algorithm] → [? sliding_window | token_bucket] → sliding_window`. Each step narrows the hole's type until it's fully determined.

---

## Holes in the Work Graph

Holes participate in the dependency graph exactly like tasks. They block. They get resolved. They have status. No special hole-handling logic is needed in executors — `bd ready` naturally skips tasks blocked by open holes.

### As Beads Issues

```bash
bd create "HOLE: Session behavior on OAuth token revocation" \
  -t task -p 1 \
  -l "hole,clarification" \
  -d "<description with known/unknown/resolution>" \
  --json > /tmp/bd-hole.json

HOLE_ID=$(jq -r '.id' /tmp/bd-hole.json)

# Wire into graph — tasks that need this answer
bd dep add "$T005" "$HOLE_ID"  # T005 blocks on this hole
bd dep add "$T006" "$HOLE_ID"  # T006 blocks on this hole
```

### As Markdown Files

Hole files live in `docs/tasks/holes/` with structured metadata. See [schemas.md § Hole Markdown Format](./schemas.md#hole-markdown-format).

### Beads Label Conventions

```
hole                    # All holes get this label
hole:clarification      # Needs human answer
hole:validation         # Needs verification (agent-resolvable)
hole:research           # Needs investigation (agent-resolvable)
hole:synthesis          # Needs design combination
hole:escalation         # Agent hit a wall (needs human)
hole:agent-resolvable   # Convenience: validation + research
hole:human-required     # Convenience: clarification + escalation
```

Useful queries:

```bash
bd list --label hole:agent-resolvable --status open --json  # What can agents resolve?
bd list --label hole:human-required --status open --json    # What needs human attention?
bd blocked --json | jq 'group_by(.blocked_by) | sort_by(-length)'  # Highest-impact holes
```

---

## Holes in Diffs

When re-decomposing after a spec change, holes participate in the diff. See [diff.md § Hole Participation](./diff.md#hole-participation-in-diffs).

| Scenario | Action |
|----------|--------|
| Hole was open, spec now answers it | Auto-resolve the hole, unblock tasks |
| Hole was open, spec still ambiguous | Keep hole open |
| Hole was resolved, spec contradicts resolution | Create new hole, flag completed tasks for rework |
| New ambiguity in updated spec | Create new hole |
| Spec change invalidates an existing assumption | Create `validation` hole to check impacted tasks |

---

## Holes in Progress Reports

The [progress reporter](./progress-report.md) includes a dedicated Holes section and adds hole-specific trigger conditions:

```yaml
triggers:
  hole_created: true           # Report when a new hole is discovered
  hole_resolved: true          # Report when a hole is resolved
  all_work_hole_blocked: true  # ALL remaining work blocked by holes
                               # (critical — human attention needed)
```

The `all_work_hole_blocked` trigger signals that agents have exhausted all available work and the project is waiting on human decisions. This should broadcast with high urgency.
