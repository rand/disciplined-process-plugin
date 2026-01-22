# Basic Feature Workflow

A complete example of implementing a new feature using the disciplined process.

## Scenario

Adding a user authentication feature to a web application.

## Step 1: Orient

```bash
# Check what work is available
/dp:task ready

# Output:
# Ready tasks (no blockers):
#   [P1] chainlink-42: Implement user authentication
#   [P2] chainlink-58: Add password reset flow

# Claim the task
/dp:task update chainlink-42 --status in_progress
```

## Step 2: Specify

```bash
# Create a new spec section for authentication
/dp:spec create 03 "User Authentication"

# Add requirements
/dp:spec add 03 "Users MUST authenticate with email and password"
/dp:spec add 03 "Passwords MUST be hashed with bcrypt (cost factor 12)"
/dp:spec add 03 "Sessions MUST expire after 24 hours of inactivity"
/dp:spec add 03 "Failed login attempts MUST be rate-limited (5 per minute)"

# Link spec to issue
/dp:spec link SPEC-03 chainlink-42
```

## Step 3: Decide

```bash
# Document the architectural decision
/dp:adr create "Use JWT for session management"

# This opens the ADR template. Fill in:
# - Context: Need stateless auth for horizontal scaling
# - Decision: Use JWT with refresh tokens
# - Consequences: Must handle token revocation, larger request headers
# - Alternatives: Server-side sessions (rejected: scaling complexity)
```

## Step 4: Test

Write tests with `@trace` markers:

```typescript
// tests/unit/auth.test.ts

// @trace SPEC-03.01
describe('User Authentication', () => {
  it('authenticates valid email and password', async () => {
    const result = await authenticate('user@example.com', 'valid-password');
    expect(result.success).toBe(true);
    expect(result.token).toBeDefined();
  });

  it('rejects invalid credentials', async () => {
    const result = await authenticate('user@example.com', 'wrong-password');
    expect(result.success).toBe(false);
  });
});

// @trace SPEC-03.02
describe('Password Hashing', () => {
  it('uses bcrypt with cost factor 12', async () => {
    const hash = await hashPassword('test-password');
    expect(hash).toMatch(/^\$2[ab]\$12\$/);
  });
});

// @trace SPEC-03.04
describe('Rate Limiting', () => {
  it('blocks after 5 failed attempts', async () => {
    for (let i = 0; i < 5; i++) {
      await authenticate('user@example.com', 'wrong');
    }
    const result = await authenticate('user@example.com', 'wrong');
    expect(result.error).toBe('rate_limited');
  });
});
```

## Step 5: Implement

Write code with `@trace` markers:

```typescript
// src/auth/authenticate.ts

// @trace SPEC-03.01, SPEC-03.02
export async function authenticate(
  email: string,
  password: string
): Promise<AuthResult> {
  const user = await findUserByEmail(email);
  if (!user) {
    return { success: false, error: 'invalid_credentials' };
  }

  // @trace SPEC-03.04
  if (await isRateLimited(email)) {
    return { success: false, error: 'rate_limited' };
  }

  const valid = await bcrypt.compare(password, user.passwordHash);
  if (!valid) {
    await recordFailedAttempt(email);
    return { success: false, error: 'invalid_credentials' };
  }

  // @trace SPEC-03.03
  const token = await createSession(user.id, { expiresIn: '24h' });
  return { success: true, token };
}
```

## Step 6: Review

```bash
# Run standard review
/dp:review

# Output:
# Review Checklist:
#   [x] All tests passing
#   [x] @trace markers present
#   [x] No hardcoded credentials
#   [!] Consider adding input validation for email format

# Run adversarial review for deep analysis
/dp:review --adversarial

# Sarcasmotron output:
# BLOCKING:
#   - Line 15: No timing-safe comparison for password check
#     (potential timing attack)
#
# NON-BLOCKING:
#   - Consider logging failed auth attempts for security monitoring

# Fix the blocking issue, then re-run
/dp:review --adversarial
# Output: No blocking issues. Ready to merge.

# Verify spec coverage
/dp:trace coverage

# Output:
# SPEC-03.01: 2 traces (auth.test.ts:5, authenticate.ts:4)
# SPEC-03.02: 2 traces (auth.test.ts:18, authenticate.ts:4)
# SPEC-03.03: 1 trace (authenticate.ts:25)
# SPEC-03.04: 2 traces (auth.test.ts:26, authenticate.ts:12)
# Coverage: 100%
```

## Step 7: Close

```bash
# Close the task
/dp:task close chainlink-42 --reason "Authentication implemented per SPEC-03"

# Commit with task reference
git add .
git commit -m "feat: implement user authentication (chainlink-42)

- Email/password auth with bcrypt hashing
- JWT sessions with 24h expiry
- Rate limiting on failed attempts
- Spec: SPEC-03.01-04
- ADR: 0005-jwt-sessions"

# Push
git push
```

## Discovered Work

During implementation, you might discover additional work:

```bash
# While implementing, you realize password reset needs work
/dp:task discover "Password reset needs rate limiting" --from chainlink-42

# This creates a new task linked as "discovered-from" chainlink-42
```
