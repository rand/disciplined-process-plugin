---
name: spec-tracing
description: Specification authoring with traceable paragraph IDs. Use when writing specifications, updating specs, adding new features to specs, or when implementing code that needs to reference spec paragraphs. Triggers on spec creation, implementation traceability, or coverage verification.
---

# Specification Tracing

Specifications define WHAT the system does, not HOW. Every normative statement gets a unique ID that implementation and tests reference.

## Paragraph ID Format

```
[SPEC-{section}.{paragraph}]
```

Examples:
- `[SPEC-01.03]` - Section 1, paragraph 3
- `[SPEC-05.12]` - Section 5, paragraph 12
- `[SPEC-03.07a]` - Section 3, paragraph 7, sub-item a

## Specification Document Structure

```markdown
# {Section Title}

## Overview

[SPEC-{NN}.01] This section defines {what this section covers}.

## {Subsection}

[SPEC-{NN}.02] {Normative statement using RFC 2119 language}.

[SPEC-{NN}.03] {Another normative statement}.

### {Sub-subsection}

[SPEC-{NN}.04] {Detailed requirement}.

> **Informative**: {Non-normative explanation or rationale}
```

## RFC 2119 Keywords

Use precise requirement language:

| Keyword | Meaning |
|---------|---------|
| MUST / SHALL | Absolute requirement |
| MUST NOT / SHALL NOT | Absolute prohibition |
| SHOULD / RECOMMENDED | Strong preference, exceptions allowed with justification |
| SHOULD NOT | Discouraged, exceptions allowed with justification |
| MAY / OPTIONAL | Truly optional |

## Implementation Traceability

### In Source Code

Add trace comments linking implementation to spec:

```rust
// @trace SPEC-03.07 - Validates input length constraint
fn validate_length(input: &str) -> Result<(), Error> {
    // Implementation per SPEC-03.07
}
```

```typescript
/**
 * @trace SPEC-05.12 - Handles authentication flow
 */
function authenticate(credentials: Credentials): Promise<Token> {
    // Implementation per SPEC-05.12
}
```

```python
def process_request(req: Request) -> Response:
    """
    @trace SPEC-02.04 - Request processing pipeline
    """
    # Implementation per SPEC-02.04
```

### In Tests

Reference spec paragraphs in test names and comments:

```rust
#[test]
// @trace SPEC-03.07
fn test_input_length_validation() {
    // Tests requirement from SPEC-03.07
}
```

```typescript
describe('SPEC-05.12: Authentication', () => {
    it('should return token on valid credentials', () => {
        // @trace SPEC-05.12
    });
});
```

```python
def test_request_processing_spec_02_04():
    """@trace SPEC-02.04"""
    # Tests requirement from SPEC-02.04
```

## Coverage Verification

To verify spec coverage, check that every normative paragraph has:

1. **At least one test** with `@trace SPEC-XX.YY` marker
2. **Implementation** with corresponding `@trace` comment

### Coverage Check Script Pattern

```bash
# Extract all spec paragraph IDs
grep -rhoE '\[SPEC-[0-9]+\.[0-9]+[a-z]?\]' docs/spec/ | sort -u > spec-ids.txt

# Extract all traced tests
grep -rhoE '@trace SPEC-[0-9]+\.[0-9]+[a-z]?' tests/ | \
    sed 's/@trace /[/' | sed 's/$/]/' | sort -u > test-traces.txt

# Find untested specs
comm -23 spec-ids.txt test-traces.txt > untested-specs.txt
```

## Spec Modification Rules

1. **New features**: Add new paragraph IDs, never reuse deleted ones
2. **Modifications**: Update paragraph text, add version note
3. **Deprecation**: Mark as deprecated, don't delete (for traceability)
4. **Breaking changes**: Create new section, deprecate old

### Version Notes

```markdown
[SPEC-03.07] Input length MUST NOT exceed 1024 bytes.

> **History**: Changed from 512 bytes in v2.0. See ADR-0015.
```

## Informative vs Normative Content

| Type | Marker | Purpose | Tested? |
|------|--------|---------|---------|
| Normative | `[SPEC-XX.YY]` | Requirements | Yes |
| Informative | Blockquote or "Note:" | Rationale, examples | No |
| Example | Code block | Illustration | Optional |

## Quick Reference

- Every MUST/SHALL/SHOULD gets a `[SPEC-XX.YY]` ID
- Implementation uses `@trace SPEC-XX.YY` comments
- Tests use `@trace SPEC-XX.YY` in name or docstring
- Coverage tooling verifies all specs have tests
- Never reuse deleted paragraph IDs
