# ADR-0001: Adopt Goal-Backward Verification

## Status
Accepted

## Context

The disciplined-process plugin tracks task completion and spec traceability, but has no mechanism to verify that completed work actually achieves its intended goal.

**Problem observed**: AI agents (and humans) can mark tasks "complete" when implementations are:
- Stubs or placeholders
- Missing key wiring (component exists but isn't imported)
- Partially implemented (happy path works, edge cases don't)

Task completion != Goal achievement.

Example: A task "create chat component" marked complete when:
- `Chat.tsx` exists (task done!)
- But it only renders "TODO: implement chat" (goal not achieved)

## Decision

Adopt **goal-backward verification** methodology, inspired by [get-shit-done](https://github.com/glittercowboy/get-shit-done).

The approach works backwards from desired outcomes:

1. **Truths**: What must be TRUE for the goal to be achieved?
   - Observable behaviors from user perspective
   - e.g., "User can send a message and see it appear"

2. **Artifacts**: What must EXIST for those truths to hold?
   - Concrete files with substantive implementations
   - e.g., `src/components/Chat.tsx` with real rendering logic

3. **Key Links**: What must be WIRED for artifacts to function?
   - Import chains, API registrations, route connections
   - e.g., Chat.tsx imported in App.tsx, connected to /api/messages

Verification checks all three levels against the actual codebase.

## Implementation

New command: `/dp:verify`

```bash
/dp:verify <task-id>        # Verify task achieved its goal
/dp:verify --staged         # Verify staged changes
/dp:verify --spec SPEC-05   # Verify spec section
```

Implementation in `scripts/lib/verification.py`:
- `extract_truths()` - Parse task/spec for success criteria
- `check_artifacts()` - Verify files exist with substance
- `check_links()` - Trace imports/calls between artifacts
- `detect_stubs()` - Identify placeholder implementations

## Consequences

### Positive
- Catches incomplete implementations before they're "done"
- Makes acceptance criteria explicit and verifiable
- Reduces back-and-forth when work doesn't actually work
- Encourages thinking about wiring, not just file creation

### Negative
- Adds verification step to workflow (more time per task)
- Requires learning new concepts (truths, artifacts, links)
- Some verifications need human judgment (marked `[?]`)
- False positives possible for intentionally minimal implementations

### Neutral
- Optional by default; can enable `auto_verify_on_close` for stricter workflows
- Integrates with existing `/dp:review` via `--verify` flag

## Alternatives Considered

### 1. Just use existing `/dp:trace coverage`
- **Rejected**: Traceability shows what's linked, not whether it works
- A stub with `@trace SPEC-01.01` passes coverage but fails verification

### 2. Require explicit acceptance tests for all tasks
- **Rejected**: Too heavyweight for small tasks
- Goal-backward verification is lighter: check existence/substance/wiring

### 3. Manual review only
- **Rejected**: Current state; doesn't scale, easy to miss stubs
- Automated checks catch obvious issues; humans focus on logic

## References

- [get-shit-done gsd-verifier](https://github.com/glittercowboy/get-shit-done/blob/main/agents/gsd-verifier.md)
- [SPEC-05: Goal-Backward Verification](../spec/05-verification.md)
