---
description: Run code review checklist against current changes. Provides structured feedback categorized as blocking or non-blocking.
argument-hint: [--staged] [--full] [--json]
---

# Code Review Command

Run a structured code review against current changes.

## Behavior

1. Identify changed files (staged or all uncommitted)
2. Analyze against review checklist
3. Categorize issues as blocking or non-blocking
4. Provide actionable feedback with file:line references
5. Optionally file non-blocking issues to task tracker

## Review Checklist

### Correctness (Blocking)
- [ ] Code does what it's supposed to do
- [ ] No obvious bugs or logic errors
- [ ] Edge cases handled
- [ ] Error cases handled appropriately
- [ ] Tests pass

### Specification Compliance (Blocking if strict mode)
- [ ] Implementation has `@trace SPEC-XX.YY` markers
- [ ] All referenced specs have corresponding tests
- [ ] Behavior matches spec requirements

### Performance
- [ ] No obvious performance issues
- [ ] Appropriate data structures used
- [ ] No unnecessary allocations in hot paths
- [ ] Async operations used appropriately

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] No SQL/command injection risks
- [ ] Appropriate access controls

### Code Quality
- [ ] Code is readable and well-organized
- [ ] Names are clear and descriptive
- [ ] Functions are appropriately sized
- [ ] No obvious code duplication
- [ ] Comments explain "why", not "what"

### Testing
- [ ] New code has tests
- [ ] Tests are meaningful, not just coverage padding
- [ ] Test names describe behavior
- [ ] Tests have `@trace` markers

### Documentation
- [ ] Public APIs documented
- [ ] Complex logic explained
- [ ] ADR created if architectural decision made

## Output Format

```
📋 Code Review: 3 files changed

## Blocking Issues (must fix before commit)

### src/auth.ts:45
❌ CORRECTNESS: Null check missing after optional chain
   const user = await getUser(id)?.name  // getUser returns Promise
   
   Fix: Await before optional chain or handle undefined

### tests/auth.test.ts:23
❌ SPEC COMPLIANCE: Test missing @trace marker
   it('should authenticate valid user', () => {
   
   Fix: Add // @trace SPEC-05.12

## Non-Blocking Issues (file as tasks for later)

### src/auth.ts:67
⚠️ PERFORMANCE: Consider caching user lookup
   This is called multiple times per request
   
   Suggested task: bd create "Cache user lookups in auth flow" -p 2

### src/auth.ts:89
⚠️ CODE QUALITY: Function exceeds 50 lines
   Consider extracting validation logic
   
   Suggested task: bd create "Refactor validateCredentials" -p 3

## Summary

Blocking:     2
Non-blocking: 2

Fix blocking issues before committing.
Run `/dp:review --file-issues` to create tasks for non-blocking issues.
```

## Arguments

- `--staged`: Only review staged changes (default: all uncommitted)
- `--full`: Include all files, not just changed
- `--json`: Output in JSON format
- `--file-issues`: Create tasks for non-blocking issues
- `--strict`: Treat spec compliance as blocking (default in strict mode)

## Integration with Hooks

In strict enforcement mode, this review runs automatically as a pre-commit hook:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash(git commit*)",
      "hooks": [{
        "type": "command",
        "command": "/dp:review --staged --blocking-only"
      }]
    }]
  }
}
```

## JSON Output

```json
{
  "files_reviewed": 3,
  "blocking": [
    {
      "file": "src/auth.ts",
      "line": 45,
      "category": "CORRECTNESS",
      "message": "Null check missing after optional chain",
      "fix": "Await before optional chain or handle undefined"
    }
  ],
  "non_blocking": [
    {
      "file": "src/auth.ts", 
      "line": 67,
      "category": "PERFORMANCE",
      "message": "Consider caching user lookup",
      "suggested_task": {
        "title": "Cache user lookups in auth flow",
        "priority": 2
      }
    }
  ],
  "summary": {
    "blocking_count": 2,
    "non_blocking_count": 2,
    "can_commit": false
  }
}
```
