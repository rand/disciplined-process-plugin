---
description: Run code review checklist
argument-hint: [adversarial] [--staged] [--full] [--json]
---

# Code Review Command

Run a structured code review against current changes.

## Modes

- **Standard** (default): Checklist-based review by Claude
- **Adversarial**: VDD-style review using Gemini with fresh context

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
   
   Suggested task: /dp:task create "Cache user lookups in auth flow" -p 2

### src/auth.ts:89
⚠️ CODE QUALITY: Function exceeds 50 lines
   Consider extracting validation logic
   
   Suggested task: /dp:task create "Refactor validateCredentials" -p 3

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

---

## Adversarial Review Mode

VDD-style (Verification-Driven Development) review using a fresh-context adversary.

```
/dp:review adversarial [--max-iterations N]
```

### How It Works

1. **Gather Context**: Collects diff, linked specs, test coverage
2. **Invoke Adversary**: Calls Gemini via rlm-claude-code with fresh context
3. **Present Critique**: Shows issues with Accept/Reject/Done options
4. **Iterate**: Loop continues until convergence

### Workflow

```
================================================================
Adversary Critique (Iteration 1)
================================================================

1. [LOGIC] auth.py:45
   Function validate_user returns early on line 45 without
   checking the is_active flag, allowing deactivated users
   through authentication.

2. [EDGE CASE] auth.py:52
   No handling for empty email string - will cause IndexError
   in email.split('@') on line 52.

3. [SECURITY] auth.py:78
   Password comparison uses == instead of constant-time
   comparison, vulnerable to timing attacks.

----------------------------------------------------------------
Options:
[A]ccept all and address
[P]artially accept (select which)
[R]eject as hallucinated
[D]one (code is complete)
----------------------------------------------------------------
```

### Response Options

| Option | Action |
|--------|--------|
| **Accept (A)** | Builder addresses all issues, then loop repeats |
| **Partial (P)** | Select specific issues to address, reject others |
| **Reject (R)** | Log critique as hallucinated, continue to next iteration |
| **Done (D)** | Exit loop, code is considered complete |

### Hallucination Detection

The system automatically flags suspicious critiques:

```
[!] POTENTIAL HALLUCINATION DETECTED
    Critique #3 references `password_hash` on line 78,
    but line 78 contains: `return user.is_authenticated`

    The function `compare_password` doesn't exist in auth.py.

    Consider rejecting this critique.
```

Detection triggers:
- Line numbers don't exist in file
- Referenced functions/variables not found
- File paths don't match modified files
- Critique contradicts visible code structure

### Convergence Criteria

The loop terminates when:

1. **Adversary returns "No issues found"** - Code is complete
2. **Human selects "Done"** - Manual termination
3. **Max iterations reached** - Default: 5 (configurable)
4. **All critiques rejected** - Adversary has lost grounding

### Configuration

In `dp-config.yaml`:

```yaml
adversarial_review:
  enabled: true
  model: gemini-2.5-flash
  max_iterations: 5
  prompt_path: .claude/adversary-prompt.md  # Optional custom prompt
```

### Requirements

- rlm-claude-code installed and configured
- `GOOGLE_API_KEY` set for Gemini access
- `adversarial_review.enabled: true` in dp-config.yaml
