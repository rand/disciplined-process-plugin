# Enforcement Configuration

The disciplined process supports three enforcement levels that control how strictly the workflow is applied.

## Levels

### Strict (Default)

Full enforcement with blocking hooks.

**Behavior**:
- Pre-commit hook blocks without passing tests
- Pre-commit hook blocks without `@trace` markers in implementation
- Code review issues must be fixed before commit
- Task IDs required in commit messages

**Configuration**:
```yaml
enforcement:
  level: "strict"
```

**When to use**:
- Production codebases
- Team projects
- When spec compliance is critical

### Guided

Advisory mode with warnings but no blocking.

**Behavior**:
- Hooks warn about missing tests/traces
- Code review issues are suggestions
- Task tracking is recommended but not required
- Skills provide guidance on request

**Configuration**:
```yaml
enforcement:
  level: "guided"
```

**When to use**:
- Learning the workflow
- Solo prototyping
- Legacy code without existing specs

### Minimal

Skills available but no enforcement.

**Behavior**:
- No hooks run automatically
- Skills available when explicitly invoked
- No commit restrictions
- Full flexibility

**Configuration**:
```yaml
enforcement:
  level: "minimal"
```

**When to use**:
- Exploratory work
- Hackathons
- Existing projects with different workflows

## Per-Hook Configuration

Individual hooks can be configured independently:

```yaml
enforcement:
  level: "strict"
  overrides:
    pre_commit_tests: "guided"      # Warn on test failures, don't block
    trace_markers: "minimal"         # Disable trace marker checks
    task_id_commits: "strict"        # Keep strict for commit messages
```

## Switching Levels

Change enforcement level anytime:

```bash
# In .claude/dp-config.yaml
enforcement:
  level: "guided"  # Change this line
```

Or use the command:
```
/dp:config set enforcement.level guided
```

## Hook Bypass

In strict mode, bypass hooks for emergencies:

```bash
git commit --no-verify -m "hotfix: critical production issue"
```

This should be rare and documented. Consider filing a task to address any skipped checks.

## Team Recommendations

| Scenario | Recommended Level |
|----------|-------------------|
| New project, greenfield | Strict |
| Existing project, adopting process | Guided → Strict |
| Learning/onboarding | Guided |
| Hackathon/prototype | Minimal |
| Production hotfix | Bypass (document) |
