# Code Review
[SPEC-04]

## Overview

[SPEC-04.01] The plugin SHALL provide structured code review with checklist-based and adversarial modes.

[SPEC-04.02] Review modes:
- **Standard**: Checklist-based review by Claude
- **Adversarial**: VDD-style review using fresh-context adversary
- **Plan**: Pre-execution validation of specs and tasks

## Standard Review

[SPEC-04.10] Standard review SHALL analyze changes against a checklist.

[SPEC-04.11] Review categories:
- **Correctness** (Blocking): Logic errors, bugs, unhandled edge cases
- **Specification Compliance**: @trace markers, spec implementation
- **Performance**: Inefficient algorithms, unnecessary allocations
- **Security**: Injection risks, hardcoded secrets, access control
- **Code Quality**: Readability, naming, organization
- **Testing**: Coverage, meaningful tests, trace markers
- **Documentation**: API docs, complex logic explanation

[SPEC-04.12] Issues SHALL be categorized as:
- **Blocking**: Must fix before commit
- **Non-blocking**: Should fix but can be filed as tasks

## Review Checklist

[SPEC-04.20] Correctness checks (Blocking):
- [ ] Code does what it's supposed to do
- [ ] No obvious bugs or logic errors
- [ ] Edge cases handled
- [ ] Error cases handled appropriately
- [ ] Tests pass

[SPEC-04.21] Specification compliance:
- [ ] Implementation has @trace markers
- [ ] All referenced specs have corresponding tests
- [ ] Behavior matches spec requirements

[SPEC-04.22] Security checks:
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] No SQL/command injection risks
- [ ] Appropriate access controls

[SPEC-04.23] Code quality:
- [ ] Code is readable and well-organized
- [ ] Names are clear and descriptive
- [ ] Functions are appropriately sized
- [ ] No obvious code duplication

## Command Interface

### /dp:review

[SPEC-04.30] Run standard review:
```
/dp:review [--staged] [--full] [--json]
```

[SPEC-04.31] Arguments:
- `--staged`: Only review staged changes (default: all uncommitted)
- `--full`: Include all files, not just changed
- `--json`: Output in JSON format
- `--file-issues`: Create tasks for non-blocking issues
- `--strict`: Treat spec compliance as blocking
- `--verify`: Include goal-backward verification

### Output Format

[SPEC-04.40] Review output SHALL include:

```
Code Review: N files changed

## Blocking Issues (must fix before commit)

### file:line
[CATEGORY] Description
Fix: Suggested fix

## Non-blocking Issues (file as tasks for later)

### file:line
[CATEGORY] Description
Suggested task: /dp:task create "..."

## Summary

Blocking:     N
Non-blocking: N

Fix blocking issues before committing.
```

## Adversarial Review

[SPEC-04.50] Adversarial review SHALL use VDD (Verification-Driven Development) workflow.

[SPEC-04.51] VDD principles:
- Builder AI implements, Adversary AI critiques
- Fresh context per adversary turn (prevents relationship drift)
- Human arbitrates legitimate vs. hallucinated critiques
- Loop continues until convergence

### /dp:review adversarial

[SPEC-04.60] Run adversarial review:
```
/dp:review adversarial [--max-iterations N]
```

[SPEC-04.61] Workflow:
1. Gather context (diff, specs, tests)
2. Invoke adversary with fresh context
3. Present critique with options: [A]ccept, [P]artial, [R]eject, [D]one
4. Iterate until convergence

[SPEC-04.62] Convergence criteria:
- Adversary returns "No issues found"
- Human selects "Done"
- Max iterations reached (default: 5)
- All critiques rejected as hallucinated

### Critique Format

[SPEC-04.70] Adversary critique format:
```
[CATEGORY] file:line
Description of issue

Why it's wrong:
<explanation>

Suggested fix:
<fix>
```

[SPEC-04.71] Critique categories:
- LOGIC: Logical errors or incorrect behavior
- SECURITY: Security vulnerabilities
- PLACEHOLDER: Stub or incomplete code
- ERROR: Error handling issues
- CONVENTION: Style or convention violations
- TEST: Testing gaps

### Hallucination Detection

[SPEC-04.80] The system SHALL detect potential hallucinations:
- Line numbers that don't exist
- Referenced functions/variables not in file
- File paths not in modified files
- Critiques contradicting visible code

[SPEC-04.81] Hallucination flags SHALL be shown:
```
[!] POTENTIAL HALLUCINATION DETECTED
    Critique references `function_name` on line 78,
    but line 78 contains: `return result`

    Consider rejecting this critique.
```

## Plan Validation Mode

[SPEC-04.90] Plan validation checks pre-execution:
```
/dp:review --plan [--spec SPEC-XX]
```

[SPEC-04.91] Validation dimensions:
- **Requirement Coverage**: Every spec has implementing task(s)
- **Task Completeness**: Every task has verification criteria
- **Dependency Correctness**: No cycles, valid references

[SPEC-04.92] Validation output:
```
Plan Validation
===============

Requirement Coverage:
  [ok] SPEC-03.01 → task-001
  [WARN] SPEC-03.02 → NO TASK (orphan)

Task Completeness:
  [ok] task-001 - has acceptance criteria
  [WARN] task-002 - missing verification criteria

Dependencies:
  [ok] No circular dependencies

Status: WARN (0 blocking, 2 warnings)
```

## Configuration

[SPEC-04.95] Review behavior configurable in `dp-config.yaml`:
```yaml
adversarial_review:
  enabled: true
  model: gemini-2.5-flash
  max_iterations: 5
  trigger: on_review  # or: on_commit, manual
  fresh_context: true

enforcement:
  level: guided  # strict | guided | minimal
```

## Integration with Hooks

[SPEC-04.98] In strict mode, review MAY run as pre-commit hook:
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
