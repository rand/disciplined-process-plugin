---
name: adr-authoring
description: Architecture Decision Record format and process. Use when making architectural decisions, documenting technical choices, evaluating alternatives, or when asked about past decisions. Triggers on ADR creation, architecture discussions, or "why did we choose" questions.
---

# Architecture Decision Records (ADRs)

ADRs document significant technical decisions with context, alternatives considered, and rationale. They answer "WHY did we choose this approach?"

## When to Write an ADR

Create an ADR when:
- Choosing between multiple valid approaches
- Adopting a new technology, framework, or pattern
- Making decisions that are hard to reverse
- Deviating from established patterns
- Trade-offs need documentation for future reference

Do NOT create an ADR for:
- Obvious best practices
- Decisions with only one viable option
- Implementation details that don't affect architecture

## ADR Format

```markdown
# ADR-{NNNN}: {Title}

**Status**: {Proposed | Accepted | Deprecated | Superseded by ADR-XXXX}  
**Date**: {YYYY-MM-DD}  
**Deciders**: {Names or roles}  
**Relates to**: {SPEC-XX.YY, ADR-XXXX, bd-XXXX}

## Context

{What is the issue we're facing? What forces are at play?}

## Decision

{What is the change we're proposing/decided?}

**We will {specific decision}.**

## Alternatives Considered

### Alternative 1: {Name}

{Description}

**Pros**:
- {advantage}

**Cons**:
- {disadvantage}

### Alternative 2: {Name}

{Description}

**Pros**:
- {advantage}

**Cons**:
- {disadvantage}

## Consequences

### Positive
- {benefit}

### Negative
- {cost/tradeoff}

### Neutral
- {side effect}

## References

- {Link to spec, discussion, research}
```

## ADR Lifecycle

```
Proposed → Accepted → [Active]
                   ↘ Deprecated
                   ↘ Superseded by ADR-XXXX
```

### Status Definitions

| Status | Meaning |
|--------|---------|
| Proposed | Under discussion, not yet decided |
| Accepted | Decision made, in effect |
| Deprecated | No longer relevant, kept for history |
| Superseded | Replaced by newer ADR (link to it) |

## Numbering

ADRs are numbered sequentially: `ADR-0001`, `ADR-0002`, etc.

- Never reuse numbers
- Superseded ADRs keep their number
- Numbers indicate chronological order, not importance

## File Organization

```
docs/adr/
├── 0001-use-postgresql-for-persistence.md
├── 0002-adopt-event-sourcing.md
├── 0003-switch-to-grpc.md
├── template.md
└── index.md                    # Optional: ADR index/summary
```

## Writing Guidelines

### Context Section
- State facts, not opinions
- Describe the problem space
- List constraints and forces
- Be specific about what prompted this decision

### Decision Section
- Start with "We will..."
- Be specific and actionable
- State what, not how (implementation comes later)

### Alternatives Section
- Include at least 2 alternatives
- Be fair to rejected options
- Explain why they were rejected
- "Do nothing" is often a valid alternative

### Consequences Section
- Be honest about negatives
- Think about operational impact
- Consider learning curve, tooling, hiring

## Examples

### Good ADR Title
- ✅ "Use PostgreSQL for User Data Persistence"
- ✅ "Adopt Circuit Breaker Pattern for External APIs"
- ✅ "Switch from REST to gRPC for Internal Services"

### Bad ADR Title
- ❌ "Database Decision" (too vague)
- ❌ "Use the best database" (not specific)
- ❌ "Technical stuff" (meaningless)

## Linking to Specs and Tasks

Reference related artifacts:

```markdown
**Relates to**: SPEC-03.07, SPEC-03.08, bd-a1b2

## Context

Per SPEC-03.07, the system MUST validate input length. 
This ADR decides HOW we implement that validation.
```

## ADR Review Checklist

- [ ] Clear, specific title
- [ ] Correct status and date
- [ ] Context explains the problem
- [ ] Decision is specific and actionable
- [ ] At least 2 alternatives considered
- [ ] Pros/cons listed for each alternative
- [ ] Consequences include positives AND negatives
- [ ] Links to related specs/tasks if applicable

## Quick Reference

1. **Trigger**: Architectural choice between alternatives
2. **Format**: Context → Decision → Alternatives → Consequences
3. **Status**: Proposed → Accepted (or Deprecated/Superseded)
4. **Numbering**: Sequential, never reused
5. **Location**: `docs/adr/NNNN-<slug>.md`
