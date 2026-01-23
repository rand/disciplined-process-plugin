---
description: Goal-backward verification of task completion
argument-hint: <task-id|--staged|--spec SPEC-XX> [options]
---

# Verify Command

Verify that work achieves its intended goal, not just that tasks were completed.

## Core Principle

**Task completion ≠ Goal achievement**

A task "create component" can be marked complete when the component is a placeholder. The task was done — a file was created — but the goal "working component" was not achieved.

## Verification Levels

Goal-backward verification works backwards from desired outcomes:

1. **Truths**: What must be TRUE for the goal to be achieved?
   - Observable behaviors from user perspective
   - e.g., "User can log in with valid credentials"

2. **Artifacts**: What must EXIST for those truths to hold?
   - Concrete files with substantive implementations (not stubs)
   - e.g., `src/auth/login.ts` with real logic

3. **Key Links**: What must be WIRED for artifacts to function?
   - Import chains, API registrations, route connections
   - e.g., login.ts imported in App.tsx, connected to /api/auth

## Usage

```bash
/dp:verify <task-id>           # Verify task achieved its goal
/dp:verify --staged            # Verify staged changes
/dp:verify --spec SPEC-05      # Verify spec section implementation
/dp:verify --last-commit       # Verify most recent commit
```

## Behavior

1. **Extract verification criteria** from task/spec:
   - Acceptance criteria → Truths
   - `@must_have` annotations → Truths, Artifacts, Links
   - Linked specs → Additional requirements

2. **Verify truths** (observable behaviors):
   - Mark as `[ok]`, `[FAIL]`, or `[?]` (needs human)

3. **Verify artifacts** (files exist with substance):
   - Check file exists
   - Check for stub patterns (TODO, NotImplementedError, placeholders)
   - Report line count and substance status

4. **Verify links** (wiring between artifacts):
   - Check import statements
   - Check function calls
   - Check route registrations

5. **Report status**: VERIFIED, INCOMPLETE, or FAILED

## Output Format

```
Verifying: bd-001f (Implement user authentication)

Truths:
  [ok] User can log in with valid credentials
  [ok] User can log out
  [FAIL] Invalid credentials show error message

Artifacts:
  [ok] src/auth/login.ts (142 lines)
  [ok] src/auth/logout.ts (28 lines)
  [STUB] src/auth/errors.ts (12 lines, stub detected)

Links:
  [ok] login.ts -> App.tsx (import)
  [ok] login.ts -> api/auth (fetch)
  [FAIL] errors.ts -> login.ts (not imported)

Status: INCOMPLETE
- 1 truth not achieved
- 1 stub detected
- 1 link missing
```

## Status Indicators

| Status | Meaning |
|--------|---------|
| `[ok]` | Verified successfully |
| `[FAIL]` | Verification failed |
| `[?]` | Cannot verify programmatically (needs human) |
| `[STUB]` | File exists but appears to be placeholder |

## Verification Outcomes

| Outcome | Condition |
|---------|-----------|
| **VERIFIED** | All truths achievable, artifacts substantive, links connected |
| **INCOMPLETE** | Some truths or links not yet implemented, stubs detected |
| **FAILED** | Artifacts missing, verification errors |

## Stub Detection

Files are flagged as stubs if they contain:
- Only `TODO`, `FIXME`, or `pass` statements
- `raise NotImplementedError` or `throw new Error("Not implemented")`
- Placeholder JSX content (`<div>TODO</div>`)
- Fewer than 10 lines with no meaningful content

## @must_have Annotations

Add explicit verification criteria to task descriptions or specs:

```markdown
[SPEC-03.01] Users SHALL be able to send messages

@must_have:
  truth: User can send a message and see it appear
  truth: Message is persisted to database
  artifact: src/components/MessageInput.tsx
  artifact: src/api/messages.ts
  link: MessageInput -> api/messages
  link: api/messages -> database.messages
```

**Fields:**
- `truth:` - Observable behavior that must be true
- `artifact:` - File path that must exist with substantive implementation
- `link:` - Connection between components (format: `from -> to`)

Works in both task descriptions and spec definitions.

## Integration

### With Task Tracking

When verifying a task, the command:
1. Fetches task details from configured tracker
2. Parses description for acceptance criteria
3. Checks for linked specs (`@trace SPEC-XX.YY`)
4. Runs verification against those criteria

### With /dp:review

Add `--verify` to include verification in review:

```bash
/dp:review --verify
```

### With /dp:task close

Enable auto-verification on task close in `dp-config.yaml`:

```yaml
verification:
  auto_verify_on_close: true
```

## Configuration

```yaml
verification:
  stub_threshold_lines: 10
  require_truths: false  # Require explicit truths in tasks
  auto_verify_on_close: false
  artifact_patterns:
    - "src/**/*.{ts,tsx,py,go,rs}"
  exclude_patterns:
    - "**/*.test.*"
    - "**/__mocks__/**"
```

## Arguments

- `<task-id>`: Task ID to verify
- `--staged`: Verify staged git changes
- `--spec <SPEC-XX>`: Verify implementation of spec section
- `--last-commit`: Verify most recent commit
- `--json`: Output in JSON format
- `--strict`: Fail on any `[?]` (uncertain) results

## See Also

- [SPEC-05: Goal-Backward Verification](../docs/spec/05-verification.md)
- [ADR-0001: Adopt Goal-Backward Verification](../docs/adr/0001-goal-backward-verification.md)
- `/dp:trace` - Spec traceability (what's linked, not whether it works)
- `/dp:review` - Code review checklist
