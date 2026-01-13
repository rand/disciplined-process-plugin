---
description: Manage Architecture Decision Records
argument-hint: <create|list|status|link> [options]
---

# ADR Command

Manage Architecture Decision Records for documenting technical decisions.

## Subcommands

### create
Create a new ADR from template.

```
/dp:adr create <title>
```

**Behavior**:
1. Determine next ADR number from existing files
2. Generate slug from title
3. Create file from template at `docs/adr/NNNN-<slug>.md`
4. Open for editing with placeholders

**Example**:
```
/dp:adr create "Use PostgreSQL for persistence"
→ Created docs/adr/0003-use-postgresql-for-persistence.md
```

### list
List all ADRs with status.

```
/dp:adr list [--status <status>]
```

**Output format**:
```
ADR-0001  Accepted    Adopt disciplined process
ADR-0002  Accepted    Use PostgreSQL for persistence
ADR-0003  Proposed    Switch to event sourcing
ADR-0004  Superseded  Use MongoDB (→ ADR-0002)
```

### status
Update ADR status.

```
/dp:adr status <number> <proposed|accepted|deprecated|superseded>
```

**If superseded**, prompt for superseding ADR number:
```
/dp:adr status 0004 superseded
→ Superseded by ADR number: 0002
→ Updated ADR-0004 status to "Superseded by ADR-0002"
```

### link
Add reference links to an ADR.

```
/dp:adr link <number> <reference>
```

**Examples**:
```
/dp:adr link 0003 SPEC-05.12
/dp:adr link 0003 bd-a1b2
/dp:adr link 0003 ADR-0002
```

Adds to the "Relates to" field in the ADR frontmatter.

## Template

When creating, use this template:

```markdown
# ADR-{NNNN}: {Title}

**Status**: Proposed  
**Date**: {YYYY-MM-DD}  
**Deciders**: {TODO: Add names}  
**Relates to**: {TODO: Add refs}

## Context

{TODO: Describe the issue and forces at play}

## Decision

**We will {TODO: specific decision}.**

## Alternatives Considered

### Alternative 1: {TODO: Name}

{TODO: Description}

**Pros**:
- {TODO}

**Cons**:
- {TODO}

### Alternative 2: {TODO: Name}

{TODO: Description}

**Pros**:
- {TODO}

**Cons**:
- {TODO}

## Consequences

### Positive
- {TODO}

### Negative
- {TODO}

### Neutral
- {TODO}

## References

- {TODO: Links to specs, discussions, research}
```

## File Location

ADRs are stored in `docs/adr/` with naming convention:
```
docs/adr/NNNN-<slug>.md
```

Where:
- NNNN = zero-padded sequential number
- slug = lowercase title with hyphens
