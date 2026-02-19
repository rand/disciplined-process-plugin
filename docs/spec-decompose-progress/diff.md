# Diff-Based Re-Decomposition

**Parent:** [README.md](./README.md)  
**Related:** [decomposition.md](./decomposition.md) · [holes.md](./holes.md) · [schemas.md](./schemas.md)

---

## Overview

When a spec changes after initial decomposition, the tool performs a principled diff against existing work items rather than wiping and recreating. This preserves completed work, minimizes rework, and maintains graph integrity.

```bash
spec-decompose --diff ./docs/spec.md
```

---

## The Diff Algorithm

### Step 1: Snapshot Existing State `[DIFF-1]`

Capture the current state of all work items.

**Beads:** `bd list --json` + `bd dep list --json`  
**Markdown:** Parse `state.yaml`

For each existing work item (task or hole), capture: ID, title, status (open/in_progress/closed), spec traces, dependencies, and acceptance criteria.

### Step 2: Re-Decompose the Updated Spec `[DIFF-2]`

Run the full decomposition subagent on the new spec, producing a "target" task graph. The subagent receives BOTH the new spec AND the existing state snapshot, with instructions to preserve existing task IDs where possible.

### Step 3: Diff Existing vs. Target `[DIFF-3]`

Classify each requirement into one of five categories:

| Category | Condition | Action by Status |
|----------|-----------|-----------------|
| **UNCHANGED** | Same requirement, same scope | Keep task as-is. If complete, stays complete. |
| **MODIFIED** | Same requirement ID, changed scope | Not started → update description. In progress → flag for review. Complete → create REWORK task linked via `discovered-from`. |
| **NEW** | Requirement not in existing decomposition | Create new task(s). Wire dependencies to existing graph. |
| **REMOVED** | Requirement no longer in spec | Not started → close as "obsolete". In progress → flag for review. Complete → leave it (code exists). |
| **DEPENDENCY CHANGED** | Same tasks, different ordering | Update dependency links. Flag if completed task now has new dependency. |

### Step 4: Generate Incremental Update `[DIFF-4]`

Produce a diff plan (`decompose-diff.md`) and an incremental script (`decompose-diff.sh`). The script uses `bd update` and `bd close` for existing issues, `bd create` only for new ones.

---

## The Diff Plan Format

```markdown
# Decomposition Diff

**Spec:** docs/spec/auth-system.md (updated 2026-02-20)
**Previous decomposition:** 2026-02-19 (12 tasks)
**After update:** 14 tasks (+3 new, -1 removed, 2 modified)

## Unchanged (9 tasks)
| Task | Status | Notes |
|------|--------|-------|
| bd-a1b2: Configure OAuth provider | ✅ complete | No changes needed |
| bd-e5f6: Token exchange endpoint | 🔄 in_progress | No changes needed |

## Modified (2 tasks)
| Task | Status | Change | Action |
|------|--------|--------|--------|
| bd-g7h8: Session expiry | open | Expiry 24h → 8h | Update description |
| bd-i9j0: Rate limiting | ✅ complete | Rate limit 100/min → 50/min | ⚠️ REWORK |

### Rework: bd-i9j0 (Rate limiting)
Original task complete, but SPEC-04.02 changed rate limit.
- New task: "Update rate limit from 100/min to 50/min"
- Links to: discovered-from:bd-i9j0

## New (3 tasks)
| Task | Depends On | Est. Tokens | Priority |
|------|-----------|-------------|----------|
| SAML SSO integration | bd-e5f6 | ~30K | P2 |
| SSO session mapping | SAML SSO | ~18K | P2 |
| SSO error handling | SAML SSO | ~15K | P2 |

## Removed (1 task)
| Task | Status | Action |
|------|--------|--------|
| bd-k1l2: Legacy token migration | open | Close as obsolete |

## ⚠️ Requires Human Review
- bd-i9j0: Complete task needs rework. Review scope.
- New SAML SSO tasks: large scope (~63K total). Confirm priority.
```

---

## Matching Heuristic

The diff must match existing tasks to requirements in the updated spec. Matching uses three signals in priority order:

1. **Spec trace IDs** (strongest): Existing task traces `SPEC-03.01` and updated spec still has `SPEC-03.01` → match.
2. **Title/description similarity** (for specs without formal IDs): Semantic similarity between existing task descriptions and new requirement text.
3. **File overlap**: Existing task produces `src/auth/session.py` and new decomposition also targets that file → likely same task.

When matching is ambiguous, the tool **flags it for human review** rather than guessing.

---

## Hole Participation in Diffs

Holes are full participants in the diff process. See [holes.md § Holes in Diffs](./holes.md#holes-in-diffs).

| Scenario | Action |
|----------|--------|
| Hole was open, spec now answers it | Auto-resolve the hole, unblock tasks |
| Hole was open, spec still ambiguous | Keep hole open |
| Hole was resolved, spec contradicts resolution | Create new hole, flag completed tasks for rework |
| New ambiguity in updated spec | Create new hole |
| Spec change invalidates an assumption | Create `validation` hole |

This means a spec update can *close* holes (the spec was clarified) as well as *open* them (the update introduced new ambiguity). The diff plan reports both.

---

## Rework Tasks

When a completed task's requirements change, the diff creates a **rework task** rather than reopening the original:

- The original task stays closed (it was correctly completed against the original spec).
- The rework task is linked via `discovered-from` to the original.
- The rework task's description includes only the delta — what changed and what needs updating.
- The rework task inherits the original's context files and adds any new ones.

This preserves the project's history and makes the rework scope explicit rather than hidden inside a reopened task.
