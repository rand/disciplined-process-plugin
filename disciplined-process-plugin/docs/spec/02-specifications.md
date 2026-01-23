# Specifications and Traceability
[SPEC-02]

## Overview

[SPEC-02.01] The plugin SHALL support spec-first development with traceable requirements.

[SPEC-02.02] Specifications are markdown files with structured requirement IDs in the format `[SPEC-XX.YY]`.

## Specification Format

[SPEC-02.10] Specifications SHALL be stored in the configured specs directory (default: `docs/spec/`).

[SPEC-02.11] Specification IDs SHALL follow the format:
- `[SPEC-XX]` - Section ID (e.g., `[SPEC-01]`)
- `[SPEC-XX.YY]` - Paragraph ID (e.g., `[SPEC-01.05]`)
- `[SPEC-XX.YY.ZZ]` - Sub-paragraph (e.g., `[SPEC-01.05.01]`)

[SPEC-02.12] Example specification:
```markdown
# Feature: User Authentication
[SPEC-03]

## Login Flow
[SPEC-03.01] User SHALL be able to log in with email and password.
[SPEC-03.02] Invalid credentials SHALL display an error message.
[SPEC-03.03] Successful login SHALL redirect to the dashboard.
```

## Trace Markers

[SPEC-02.20] Implementation code SHALL link to specs via `@trace` markers.

[SPEC-02.21] Trace marker format:
```python
# @trace SPEC-03.01
def login(email: str, password: str) -> User:
    ...
```

[SPEC-02.22] Trace markers SHALL be recognized in:
- Python: `# @trace SPEC-XX.YY`
- JavaScript/TypeScript: `// @trace SPEC-XX.YY`
- Go: `// @trace SPEC-XX.YY`
- Rust: `// @trace SPEC-XX.YY`
- Shell: `# @trace SPEC-XX.YY`

[SPEC-02.23] Tests SHALL also include trace markers:
```python
def test_login_success():
    """Test successful login. @trace SPEC-03.01"""
    ...
```

## Bidirectional Linking

[SPEC-02.30] Specs MAY be linked to tasks via HTML comments:
```markdown
[SPEC-03.01] User SHALL be able to log in <!-- bd-a1b2 -->
```

[SPEC-02.31] The plugin SHALL support commands to manage links:
- `/dp:spec link <spec-id> <issue-id>` - Create link
- `/dp:spec unlink <spec-id>` - Remove link
- `/dp:spec show <spec-id>` - Show linked issues

## Command Interface

### /dp:spec list

[SPEC-02.40] List all specifications:
```
/dp:spec list [--section XX] [--uncovered]
```

[SPEC-02.41] With `--uncovered`, show only specs without trace markers.

### /dp:spec add

[SPEC-02.50] Add a new specification:
```
/dp:spec add <section> "<requirement>"
```

[SPEC-02.51] The command SHALL:
1. Determine next available paragraph ID
2. Append to section file
3. Optionally create task for implementation

### /dp:spec coverage

[SPEC-02.60] Generate traceability coverage report:
```
/dp:spec coverage [--format text|json|markdown]
```

[SPEC-02.61] Report SHALL include:
- Total specs vs covered specs
- Per-section breakdown
- List of uncovered specs
- Test locations for each covered spec

[SPEC-02.62] Coverage report format:
```
Specification Coverage Report
=============================

Overall: 15/20 specs covered (75%)

Section SPEC-01 (Task Tracking): 8/10 covered
  [ok] SPEC-01.01 → src/task.py:25, tests/test_task.py:10
  [ok] SPEC-01.02 → src/task.py:42
  [!!] SPEC-01.03 → NO COVERAGE
  ...

Section SPEC-02 (Specifications): 7/10 covered
  ...
```

## Validation

[SPEC-02.70] The plugin SHALL validate trace markers:
- Referenced spec ID exists
- Marker format is correct
- Spec is not deprecated

[SPEC-02.71] In strict enforcement mode, commits SHALL be blocked if:
- New code lacks trace markers
- Trace markers reference non-existent specs

## Configuration

[SPEC-02.80] Specification behavior configurable in `dp-config.yaml`:
```yaml
specs:
  directory: docs/spec
  id_format: "SPEC-{section:02d}.{item:02d}"
  require_issue_link: false  # In strict mode, specs must link to tasks
```
