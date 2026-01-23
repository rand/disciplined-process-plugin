# Architecture Decision Records
[SPEC-03]

## Overview

[SPEC-03.01] The plugin SHALL support Architecture Decision Records (ADRs) for documenting design choices.

[SPEC-03.02] ADRs capture the context, decision, and consequences of significant architectural choices.

## ADR Format

[SPEC-03.10] ADRs SHALL be stored in the configured directory (default: `docs/adr/`).

[SPEC-03.11] ADR files SHALL follow naming convention: `NNNN-<slug>.md` (e.g., `0001-use-sqlite-for-storage.md`).

[SPEC-03.12] ADR template structure:
```markdown
# ADR-NNNN: <Title>

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
**Date**: YYYY-MM-DD
**Deciders**: <names>
**Relates to**: SPEC-XX.YY, ADR-XXXX, bd-XXXX

## Context

<Describe the issue and forces at play>

## Decision

**We will <specific decision>.**

## Alternatives Considered

### Alternative 1: <Name>
<Description>
- Pros: ...
- Cons: ...

### Alternative 2: <Name>
...

## Consequences

### Positive
- <benefit>

### Negative
- <tradeoff>

### Risks
- <risk>

## References
- <links to specs, discussions, research>
```

## ADR Lifecycle

[SPEC-03.20] ADR status transitions:
```
Proposed → Accepted → [Deprecated | Superseded]
```

[SPEC-03.21] Status meanings:
- **Proposed**: Under discussion, not yet decided
- **Accepted**: Decision made and in effect
- **Deprecated**: No longer relevant (context changed)
- **Superseded**: Replaced by a newer ADR

[SPEC-03.22] When superseding an ADR:
1. Update old ADR status to "Superseded by ADR-XXXX"
2. New ADR references the superseded one
3. Both remain in history for context

## Command Interface

### /dp:adr list

[SPEC-03.30] List all ADRs:
```
/dp:adr list [--status <status>] [--relates <ref>]
```

[SPEC-03.31] Output format:
```
Architecture Decision Records
=============================

ADR-0001  Accepted    Use SQLite for storage
ADR-0002  Accepted    Adopt spec-first workflow
ADR-0003  Proposed    Add GraphQL API
ADR-0004  Superseded  Use REST API (→ ADR-0003)
```

### /dp:adr create

[SPEC-03.40] Create a new ADR:
```
/dp:adr create "<title>" [--relates <refs>]
```

[SPEC-03.41] The command SHALL:
1. Determine next ADR number
2. Generate slug from title
3. Create file from template
4. Open for editing (if interactive)

### /dp:adr show

[SPEC-03.50] Show ADR details:
```
/dp:adr show <id>
```

### /dp:adr update

[SPEC-03.60] Update ADR status:
```
/dp:adr update <id> --status <status> [--superseded-by <id>]
```

## Integration

[SPEC-03.70] ADRs SHALL integrate with specs:
- ADRs MAY reference specs they implement
- Specs MAY reference ADRs that inform their design

[SPEC-03.71] ADRs SHALL integrate with tasks:
- Creating an ADR MAY create a corresponding task
- Implementing an ADR MAY require task completion

[SPEC-03.72] ADRs SHALL be considered in code review:
- Architectural changes without ADRs MAY trigger warnings
- `/dp:review` MAY check for ADR compliance

## When to Create an ADR

[SPEC-03.80] An ADR SHOULD be created when:
- Choosing between technologies or libraries
- Defining API contracts or data schemas
- Establishing patterns or conventions
- Making tradeoffs with long-term implications
- Changing existing architectural decisions

[SPEC-03.81] An ADR is NOT needed for:
- Implementation details without alternatives
- Bug fixes
- Routine refactoring
- Configuration changes

## Configuration

[SPEC-03.90] ADR behavior configurable in `dp-config.yaml`:
```yaml
adrs:
  directory: docs/adr
  id_format: "ADR-{number:04d}"
  template: .claude/templates/adr.md  # Custom template
```
