---
description: Manage specifications with [SPEC-XX.YY] IDs
argument-hint: <create|add|link|unlink|coverage|list> [options]
---

# Specification Command

Manage specifications with traceable paragraph IDs.

## Subcommands

### create
Create a new specification section.

```
/dp:spec create <section-number> <title>
```

**Behavior**:
1. Validate section number format (NN)
2. Create file at `docs/spec/NN-<slug>.md`
3. Initialize with section template
4. Add first paragraph ID `[SPEC-NN.01]`

**Example**:
```
/dp:spec create 03 "Type System"
→ Created docs/spec/03-type-system.md
→ Initialized with [SPEC-03.01] placeholder
```

### add
Add a new paragraph to existing spec section.

```
/dp:spec add <section> "<statement>"
```

**Behavior**:
1. Find next available paragraph ID for section
2. Append paragraph with proper ID
3. Format with RFC 2119 keywords highlighted

**Example**:
```
/dp:spec add 03 "Types MUST be resolved before codegen"
→ Added [SPEC-03.07]: Types MUST be resolved before codegen
```

### link
Link a specification to an issue for traceability.

```
/dp:spec link <spec-id> <issue-id>
```

**Behavior**:
1. Find the spec paragraph in `docs/spec/`
2. Add HTML comment with issue reference: `<!-- chainlink:N -->` or `<!-- beads:id -->`
3. Optionally update issue description with spec reference

**Example**:
```
/dp:spec link SPEC-01.03 CL-15
-> Linked [SPEC-01.03] to CL-15 (Session expiry)
-> Updated spec file: docs/spec/01-authentication.md
```

**Spec format after linking**:
```markdown
[SPEC-01.03] Session expires after 30 minutes of inactivity <!-- chainlink:15 -->
```

### unlink
Remove link between a specification and an issue.

```
/dp:spec unlink <spec-id>
```

**Example**:
```
/dp:spec unlink SPEC-01.03
-> Removed link from [SPEC-01.03]
```

### coverage
Check test coverage for specifications.

```
/dp:spec coverage [--section <NN>] [--json]
```

**Behavior**:
1. Extract all `[SPEC-XX.YY]` IDs from `docs/spec/`
2. Extract all `@trace SPEC-XX.YY` markers from `tests/`
3. Calculate coverage and report

**Output format**:
```
Specification Coverage Report
=============================

Section 01 (Overview):        8/8   (100%)
Section 02 (Lexical):        12/14  (86%)
  Missing: SPEC-02.09, SPEC-02.13
Section 03 (Types):           5/10  (50%)
  Missing: SPEC-03.04, SPEC-03.05, SPEC-03.07, SPEC-03.08, SPEC-03.10

Total: 25/32 (78%)

Run with --json for machine-readable output.
```

**JSON output**:
```json
{
  "total_specs": 32,
  "covered_specs": 25,
  "coverage_percent": 78,
  "sections": {
    "01": {"total": 8, "covered": 8, "missing": []},
    "02": {"total": 14, "covered": 12, "missing": ["SPEC-02.09", "SPEC-02.13"]},
    "03": {"total": 10, "covered": 5, "missing": ["SPEC-03.04", "..."]}
  }
}
```

### list
List all specification paragraphs.

```
/dp:spec list [--section <NN>] [--uncovered]
```

**Example output**:
```
SPEC-01.01  ✓  This specification defines the Rue language
SPEC-01.02  ✓  A conforming implementation MUST...
SPEC-02.01  ✓  Source files MUST be UTF-8 encoded
SPEC-02.02  ✗  Line terminators are CR, LF, or CRLF
...

✓ = has test coverage
✗ = missing test coverage
```

## Spec File Format

Each spec section follows this format:

```markdown
# {Section Title}
[SPEC-{NN}] <!-- chainlink:12 -->

## Overview

[SPEC-{NN}.01] {Overview statement}. <!-- chainlink:13 -->

## {Subsection}

[SPEC-{NN}.02] {Normative requirement using RFC 2119 keywords}. <!-- chainlink:14 -->

> **Informative**: {Rationale or explanation, not tested}

[SPEC-{NN}.03] {Another requirement}. <!-- beads:bd-a1b2 -->

### {Sub-subsection}

[SPEC-{NN}.04] {Detailed requirement}.
```

**Note**: The HTML comment `<!-- provider:id -->` links the spec to an issue:
- `<!-- chainlink:N -->` - Links to Chainlink issue #N
- `<!-- beads:bd-xxxx -->` - Links to Beads issue bd-xxxx

Unlinked specs (no HTML comment) appear in the coverage report as "not started".

## RFC 2119 Detection

When adding paragraphs, detect and format RFC 2119 keywords:
- MUST, SHALL → requirement
- MUST NOT, SHALL NOT → prohibition  
- SHOULD, RECOMMENDED → strong preference
- MAY, OPTIONAL → optional

## Integration with Task Tracking

When adding specs, optionally create related task:

```
/dp:spec add 03 "Types MUST be resolved before codegen" --task
→ Added [SPEC-03.07]
→ Created bd-a1b2: Implement SPEC-03.07 (type resolution)
```

## File Location

Specifications are stored in `docs/spec/` with naming convention:
```
docs/spec/NN-<slug>.md
```

Where:
- NN = zero-padded section number
- slug = lowercase title with hyphens
