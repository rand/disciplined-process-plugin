# Goal-Backward Verification
[SPEC-05]

## Overview

[SPEC-05.01] The verification system SHALL confirm that work achieves its intended goal, not merely that tasks were completed.

[SPEC-05.02] Verification follows a goal-backward approach:
1. Start from what SHOULD be achieved (the goal)
2. Derive what must be TRUE for that goal
3. Derive what must EXIST to support those truths
4. Derive what must be WIRED between those artifacts
5. Verify each level against the actual codebase

## Core Principle

[SPEC-05.03] Task completion does NOT equal goal achievement. A task "create component" can be marked complete when the component is a placeholder. The task was done, but the goal was not achieved.

## Verification Levels

### Level 1: Truths

[SPEC-05.10] A **truth** is an observable behavior that must be true for the goal to be achieved.

[SPEC-05.11] Truths SHALL be stated from the user's perspective (e.g., "User can log in with valid credentials").

[SPEC-05.12] Each truth SHALL be testable by a human using the system.

### Level 2: Artifacts

[SPEC-05.20] An **artifact** is a file or component that must exist to support a truth.

[SPEC-05.21] Artifact verification SHALL check three properties:
- **Existence**: The file exists at the specified path
- **Substance**: The file contains meaningful implementation (not a stub/placeholder)
- **Completeness**: Required exports/interfaces are present

[SPEC-05.22] Stub detection SHALL identify:
- Files with only `TODO`, `FIXME`, or `pass` statements
- Functions that only throw "not implemented" errors
- Components that render only placeholder text
- Files under a configurable line threshold (default: 10 lines)

### Level 3: Key Links

[SPEC-05.30] A **key link** is a connection between artifacts that must be wired correctly.

[SPEC-05.31] Key link verification SHALL check:
- Import statements exist
- Functions/components are actually called
- API routes are registered
- Database queries connect to schema

[SPEC-05.32] Common unwired patterns to detect:
- Component defined but never imported
- API endpoint defined but not registered in router
- Function exported but never called
- Schema defined but no migrations

## Command Interface

### /dp:verify

[SPEC-05.40] The `/dp:verify` command SHALL accept the following subcommands:

```
/dp:verify <task-id>           # Verify task achieved its goal
/dp:verify --staged            # Verify staged changes
/dp:verify --spec <SPEC-XX>    # Verify spec section implementation
/dp:verify --last-commit       # Verify most recent commit
```

[SPEC-05.41] The command SHALL extract verification criteria from:
1. Task description and acceptance criteria
2. Linked specs (`[SPEC-XX.YY]`)
3. Must-have annotations (if present)

### Output Format

[SPEC-05.50] Verification output SHALL include:

```
Verifying: <task-id or description>

Truths:
  [status] <truth description>
  ...

Artifacts:
  [status] <path> (<details>)
  ...

Links:
  [status] <from> -> <to> (<via>)
  ...

Status: <VERIFIED | INCOMPLETE | FAILED>
[Details of failures if any]
```

[SPEC-05.51] Status indicators SHALL be:
- `[ok]` - Verified successfully
- `[FAIL]` - Verification failed
- `[?]` - Cannot verify programmatically (needs human)
- `[STUB]` - File exists but appears to be placeholder

### Verification Outcomes

[SPEC-05.60] A verification SHALL result in one of:
- **VERIFIED**: All truths achievable, all artifacts substantive, all links connected
- **INCOMPLETE**: Some truths or links not yet implemented
- **FAILED**: Artifacts missing or verification errors occurred

[SPEC-05.61] The command SHALL return non-zero exit code for INCOMPLETE or FAILED status.

## Integration

### With Task Tracking

[SPEC-05.70] When verifying a task, the system SHALL:
1. Fetch task details from configured tracker
2. Parse description for success criteria
3. Check for linked specs
4. Run verification against those criteria

### With Specs

[SPEC-05.71] When verifying a spec section, the system SHALL:
1. Load all specs in the section
2. Find `@trace` markers for each spec
3. Verify traced code implements spec intent
4. Report coverage and gaps

### With /dp:review

[SPEC-05.72] The `/dp:review` command MAY invoke verification as part of its checklist when `--verify` flag is passed.

## Configuration

[SPEC-05.80] Verification behavior SHALL be configurable in `dp-config.yaml`:

```yaml
verification:
  stub_threshold_lines: 10
  require_truths: false  # If true, tasks must have explicit truths
  auto_verify_on_close: false  # Run verification when closing tasks
  artifact_patterns:
    - "src/**/*.{ts,tsx,py,go,rs}"
    - "lib/**/*"
  exclude_patterns:
    - "**/*.test.*"
    - "**/__mocks__/**"
```

## Error Handling

[SPEC-05.90] The verification system SHALL handle:
- Missing task IDs gracefully with clear error message
- Invalid spec references with suggestions
- File system errors during artifact checks
- Timeout for long-running link verification

[SPEC-05.91] Verification SHALL NOT modify any files; it is read-only analysis.
