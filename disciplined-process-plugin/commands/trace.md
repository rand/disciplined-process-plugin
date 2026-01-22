---
description: Code and test traceability validation
argument-hint: <coverage|validate|find> [options]
---

# Trace Command

Validate and report on traceability between specs, issues, tests, and code.

## Subcommands

### coverage
Generate comprehensive traceability report.

```
/dp:trace coverage [--section <NN>] [--format <text|json>]
```

**Behavior**:
1. Extract all `[SPEC-XX.YY]` IDs from `docs/spec/`
2. Extract issue links from spec comments `<!-- chainlink:N -->`
3. Extract `@trace SPEC-XX.YY` markers from tests and code
4. Query issue status from configured tracker
5. Generate coverage matrix

**Output**:
```
Spec Coverage Report
========================================================================

Section: Authentication (SPEC-01)
------------------------------------------------------------------------
SPEC-01.01  [x] chainlink:13 (closed)   tests: 5/5 passing   code: auth.py:42
SPEC-01.02  [!] chainlink:14 (open)     tests: 0 written     code: -
SPEC-01.03  [x] chainlink:15 (closed)   tests: 3/3 passing   code: session.py:18
SPEC-01.10  [ ] No linked issue         tests: -             code: -

Section: User Management (SPEC-02)
------------------------------------------------------------------------
SPEC-02.01  [x] chainlink:20 (closed)   tests: 2/2 passing   code: users.py:15
SPEC-02.02  [!] chainlink:21 (in_progress)  tests: 1/3 passing   code: users.py:45

Summary: 3/6 specs fully covered, 2 in progress, 1 not started
========================================================================
```

**Legend**:
- `[x]` - Issue closed, tests passing
- `[!]` - Issue open or tests failing
- `[ ]` - No linked issue

### validate
Check for traceability issues.

```
/dp:trace validate [--fix]
```

**Checks performed**:
1. Orphan traces - `@trace` markers referencing non-existent specs
2. Missing traces - Specs without any `@trace` markers in code/tests
3. Stale links - Issue links to deleted/renamed issues
4. Format errors - Malformed `[SPEC-XX.YY]` IDs

**Output**:
```
Traceability Validation
=============================

Orphan traces (3):
  tests/test_auth.py:15   @trace SPEC-99.01  (spec does not exist)
  src/users.py:42         @trace SPEC-02.99  (spec does not exist)
  tests/test_api.py:8     @trace SPEC-03     (missing paragraph number)

Missing traces (2):
  SPEC-01.04  "Password reset link expires after 24h"
  SPEC-02.03  "User email must be unique"

Stale links (1):
  SPEC-01.02  <!-- chainlink:999 --> (issue not found)

Run with --fix to attempt automatic repairs.
```

**Auto-fix behavior** (`--fix`):
- Remove orphan traces: Prompts before removal
- Missing traces: Cannot auto-fix (requires implementation)
- Stale links: Removes HTML comment, marks as unlinked

### find
Find all traces for a specific spec.

```
/dp:trace find <spec-id>
```

**Output**:
```
Traces for SPEC-01.03
=============================

Issue: chainlink:15 (Session expiry) - closed

Tests:
  tests/test_session.py:42   test_session_expires_after_inactivity
  tests/test_session.py:67   test_session_extends_on_activity
  tests/test_session.py:89   test_session_expiry_boundary

Code:
  src/session.py:18          SessionManager.check_expiry()
  src/session.py:45          SessionManager.extend_session()
  src/middleware/auth.py:23  validate_session()
```

## @trace Marker Format

Use `@trace` comments in code and tests to link implementations to specs:

**Python**:
```python
# @trace SPEC-01.03
def check_session_expiry(session: Session) -> bool:
    """Check if session has expired."""
    pass

# @trace SPEC-01.03.a - Idle timeout check
if session.last_activity + IDLE_TIMEOUT < now():
    return True
```

**TypeScript/JavaScript**:
```typescript
// @trace SPEC-01.03
function checkSessionExpiry(session: Session): boolean {
    // ...
}
```

**Go**:
```go
// @trace SPEC-01.03
func (s *Session) IsExpired() bool {
    // ...
}
```

**Tests** (any language):
```python
# @trace SPEC-01.03
def test_session_expires_after_inactivity():
    """Verify SPEC-01.03: Session expires after 30 minutes."""
    pass
```

## Integration with Enforcement

Based on `enforcement` level in `dp-config.yaml`:

| Level | New Code Without @trace | Tests Without @trace |
|-------|------------------------|---------------------|
| `strict` | **Block** - Must have trace marker | **Block** |
| `guided` | **Warn** - Suggest adding trace | **Warn** |
| `minimal` | Allow | Allow |

## File Patterns Searched

By default, traces are searched in:
- `src/**/*.py`, `src/**/*.ts`, `src/**/*.go`, `src/**/*.rs`
- `tests/**/*.py`, `tests/**/*.ts`, `tests/**/*.go`, `tests/**/*.rs`
- `lib/**/*`, `pkg/**/*`

Configure additional patterns in `dp-config.yaml`:
```yaml
traceability:
  code_patterns:
    - "src/**/*.py"
    - "lib/**/*.py"
  test_patterns:
    - "tests/**/*.py"
    - "test/**/*.py"
```
