---
name: tdd-methodology
description: Test-driven development methodology with four test types - unit, integration, property, and e2e. Use when writing tests, planning test strategy, implementing features test-first, or verifying test coverage. Triggers when tests are mentioned, test files are being created, or test-first approach is needed.
---

# Test-Driven Development Methodology

Tests verify specifications are met. Write tests BEFORE implementation. Tests reference spec paragraph IDs for traceability.

## The TDD Cycle

```
┌──────────────────┐
│  1. RED          │  Write a failing test for spec requirement
├──────────────────┤
│  2. GREEN        │  Write minimal code to pass
├──────────────────┤
│  3. REFACTOR     │  Improve code, keep tests green
└──────────────────┘
```

## Four Test Types

### 1. Unit Tests

**Purpose**: Test individual functions/methods in isolation  
**Location**: `tests/unit/`  
**Characteristics**:
- Fast (ms per test)
- No I/O, no network, no filesystem
- Mock external dependencies
- One assertion focus per test

**Pattern**:
```
test_<function>_<scenario>_<expected>
```

**Example** (Rust):
```rust
#[test]
// @trace SPEC-03.07
fn test_validate_length_exceeds_max_returns_error() {
    let input = "x".repeat(1025);
    assert!(validate_length(&input).is_err());
}
```

**Example** (TypeScript):
```typescript
describe('validateLength', () => {
    // @trace SPEC-03.07
    it('returns error when input exceeds max length', () => {
        const input = 'x'.repeat(1025);
        expect(() => validateLength(input)).toThrow();
    });
});
```

**Example** (Python):
```python
def test_validate_length_exceeds_max_returns_error():
    """@trace SPEC-03.07"""
    input_str = 'x' * 1025
    with pytest.raises(ValidationError):
        validate_length(input_str)
```

### 2. Integration Tests

**Purpose**: Test component interactions, real dependencies  
**Location**: `tests/integration/`  
**Characteristics**:
- Slower (seconds per test)
- Real database, real filesystem, test containers
- Test boundaries between modules
- Setup/teardown for external state

**Pattern**:
```
test_<component>_<integration>_<scenario>
```

**Example** (Rust):
```rust
#[tokio::test]
// @trace SPEC-05.12
async fn test_auth_service_validates_against_database() {
    let db = TestDb::new().await;
    let auth = AuthService::new(db.pool());
    
    let result = auth.authenticate(valid_credentials()).await;
    
    assert!(result.is_ok());
}
```

### 3. Property Tests

**Purpose**: Test invariants hold across generated inputs  
**Location**: `tests/property/`  
**Characteristics**:
- Generates random inputs
- Finds edge cases automatically
- Tests properties, not specific values
- Shrinks failing cases to minimal examples

**Properties to test**:
- Roundtrip: `decode(encode(x)) == x`
- Idempotence: `f(f(x)) == f(x)`
- Invariants: `len(result) <= MAX_SIZE`
- Commutativity: `f(a, b) == f(b, a)`

**Example** (Rust with proptest):
```rust
proptest! {
    #[test]
    // @trace SPEC-02.01 - Encoding roundtrip
    fn test_encode_decode_roundtrip(input: String) {
        let encoded = encode(&input);
        let decoded = decode(&encoded)?;
        prop_assert_eq!(decoded, input);
    }
}
```

**Example** (Python with Hypothesis):
```python
from hypothesis import given, strategies as st

@given(st.text())
def test_encode_decode_roundtrip(input_str):
    """@trace SPEC-02.01"""
    encoded = encode(input_str)
    decoded = decode(encoded)
    assert decoded == input_str
```

**Example** (TypeScript with fast-check):
```typescript
import fc from 'fast-check';

// @trace SPEC-02.01
test('encode/decode roundtrip', () => {
    fc.assert(fc.property(fc.string(), (input) => {
        const encoded = encode(input);
        const decoded = decode(encoded);
        return decoded === input;
    }));
});
```

### 4. End-to-End Tests

**Purpose**: Test complete user workflows  
**Location**: `tests/e2e/`  
**Characteristics**:
- Slowest (minutes per suite)
- Real environment, real data flows
- Test from user's perspective
- Critical paths only (expensive to maintain)

**Pattern**:
```
test_<user_journey>_<expected_outcome>
```

**Example**:
```typescript
// @trace SPEC-01.01 - Complete user registration flow
test('user can register and receive confirmation email', async () => {
    await page.goto('/register');
    await page.fill('#email', 'test@example.com');
    await page.fill('#password', 'SecurePass123!');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/welcome');
    await expect(emailServer).toHaveReceivedEmail({
        to: 'test@example.com',
        subject: /Welcome/
    });
});
```

## Test Pyramid

```
        ╱╲
       ╱  ╲         E2E (few)
      ╱────╲        Critical user journeys
     ╱      ╲
    ╱────────╲      Property (some)
   ╱          ╲     Invariants, edge cases
  ╱────────────╲    Integration (more)
 ╱              ╲   Component boundaries
╱────────────────╲  Unit (many)
                    Individual functions
```

## Test Organization

```
tests/
├── unit/
│   ├── test_<module>.{ext}
│   └── ...
├── integration/
│   ├── test_<component>_<integration>.{ext}
│   └── ...
├── property/
│   ├── test_<invariant>.{ext}
│   └── ...
├── e2e/
│   ├── test_<journey>.{ext}
│   └── ...
├── fixtures/                 # Shared test data
│   ├── valid_inputs.json
│   └── ...
└── conftest.{ext}           # Shared setup (pytest) or similar
```

## Framework Selection by Language

| Language | Unit | Property | Integration | E2E |
|----------|------|----------|-------------|-----|
| Rust | `#[test]`, cargo test | proptest, quickcheck | tokio::test | - |
| TypeScript | Jest, Vitest | fast-check | Supertest | Playwright |
| Python | pytest | Hypothesis | pytest + fixtures | Playwright |
| Go | testing | gopter | testcontainers | - |
| Zig | std.testing | - | - | - |

## Coverage Requirements

| Level | Minimum Coverage | Measured By |
|-------|------------------|-------------|
| Spec | 100% normative paragraphs | Trace marker presence |
| Unit | 80% line coverage | Coverage tools |
| Integration | Critical paths | Manual review |
| E2E | Happy paths | Journey checklist |

## Quick Reference

1. **Before coding**: Write failing test with `@trace SPEC-XX.YY`
2. **Test naming**: `test_<what>_<scenario>_<expected>`
3. **One focus**: Each test verifies one thing
4. **Fast feedback**: Unit tests run in <1s total
5. **Isolation**: Unit tests mock externals
6. **Coverage**: Every spec paragraph has a test
