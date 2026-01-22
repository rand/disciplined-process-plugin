# Adversarial Review Workflow

Using VDD-style adversarial review for thorough code validation.

## What is Adversarial Review?

Adversarial review uses a fresh-context model (Gemini) to critically examine your code. The "Sarcasmotron" reviewer:
- Has no knowledge of your implementation journey
- Only sees the final diff and context
- Actively tries to find problems
- Detects hallucinations (references to non-existent code)

## Basic Usage

```bash
# After implementing a feature, run adversarial review
/dp:review --adversarial

# Output:
# =================================================
# Adversarial Review (Iteration 1/5)
# =================================================
#
# Gathering context...
#   - Diff: 127 lines changed
#   - Specs: SPEC-03.01, SPEC-03.02
#   - Tests: 8 test files
#
# Sarcasmotron says:
#
# BLOCKING ISSUES:
#
# 1. [HIGH] SQL Injection vulnerability
#    File: src/db/queries.ts:45
#    Code: `WHERE id = ${userId}`
#    Fix: Use parameterized query
#
# 2. [HIGH] Missing null check
#    File: src/handlers/user.ts:23
#    Code: `user.profile.name` - profile may be null
#    Fix: Add optional chaining or null check
#
# NON-BLOCKING ISSUES:
#
# 1. [MEDIUM] Magic number
#    File: src/config.ts:12
#    Code: `timeout: 30000`
#    Suggestion: Extract to named constant
#
# 2. [LOW] Inconsistent naming
#    File: src/utils.ts:8
#    Code: `getUserData` vs `fetchUserInfo`
#    Suggestion: Standardize naming convention
#
# Options:
#   [F] Fix blocking issues and re-review
#   [A] Accept non-blocking, file as tasks
#   [D] Done - all issues addressed
```

## Iterative Review Process

### Fix and Re-review

```bash
# After fixing the SQL injection and null check...

/dp:review --adversarial

# Output:
# =================================================
# Adversarial Review (Iteration 2/5)
# =================================================
#
# Sarcasmotron says:
#
# BLOCKING ISSUES: None
#
# NON-BLOCKING ISSUES:
#
# 1. [MEDIUM] Magic number (previously reported)
#    File: src/config.ts:12
#
# 2. [LOW] Inconsistent naming (previously reported)
#    File: src/utils.ts:8
#
# 3. [LOW] Missing JSDoc on public function
#    File: src/handlers/user.ts:20
#
# No blocking issues! Ready to merge.
#
# Options:
#   [A] Accept - file non-blocking as tasks
#   [D] Done - proceed without filing tasks
```

### Accept and File Tasks

```bash
# Choose [A] to accept and file tasks

# Output:
# Filed tasks for non-blocking issues:
#   chainlink-142: Extract timeout to named constant (src/config.ts:12)
#   chainlink-143: Standardize function naming (getUserData vs fetchUserInfo)
#   chainlink-144: Add JSDoc to user handler functions
#
# Review complete. Ready to merge.
```

## Hallucination Detection

The adversarial reviewer validates its own findings:

```bash
/dp:review --adversarial

# Output:
# Sarcasmotron says:
#
# BLOCKING ISSUES:
#
# 1. [HIGH] Unclosed database connection
#    File: src/db/pool.ts:67
#    Code: Missing `connection.release()` in error path
#
# Validating findings...
#
# WARNING: Potential hallucination detected:
#   - Line 67 of src/db/pool.ts does not exist (file has 45 lines)
#   - Re-analyzing...
#
# Corrected finding:
# 1. [HIGH] Unclosed database connection
#    File: src/db/pool.ts:34
#    Code: Missing `connection.release()` in catch block
#
# Hallucination detection saved you from a wild goose chase!
```

## Configuration

### Adjusting Max Iterations

```bash
# Allow more iterations for complex reviews
/dp:review --adversarial --max-iterations 10

# Or set in dp-config.yaml:
# adversarial_review:
#   max_iterations: 10
```

### Changing the Model

```yaml
# In .claude/dp-config.yaml
adversarial_review:
  enabled: true
  model: gemini-2.5-pro  # Use pro for more thorough review
  max_iterations: 5
```

### Disabling for Quick Changes

```bash
# Skip adversarial for trivial changes
/dp:review  # Standard review only

# Or disable globally
# adversarial_review:
#   enabled: false
```

## When to Use Adversarial Review

**Always use for:**
- Security-sensitive code (auth, crypto, input handling)
- Public API changes
- Database migrations
- Complex business logic

**Consider skipping for:**
- Documentation updates
- Simple config changes
- Trivial refactoring
- Prototype/experimental code

## Example: Security-Critical Review

```bash
# Implementing password reset - use adversarial review

/dp:review --adversarial

# Output:
# Sarcasmotron says:
#
# BLOCKING ISSUES:
#
# 1. [CRITICAL] Token not cryptographically secure
#    File: src/auth/reset.ts:12
#    Code: `Math.random().toString(36)`
#    Fix: Use crypto.randomBytes(32).toString('hex')
#
# 2. [HIGH] Token never expires
#    File: src/auth/reset.ts:25
#    Code: No expiration check before use
#    Fix: Add createdAt + 1 hour expiration
#
# 3. [HIGH] Token reusable after password change
#    File: src/auth/reset.ts:45
#    Code: Token not invalidated after use
#    Fix: Delete token after successful reset
#
# 4. [MEDIUM] No rate limiting on reset requests
#    File: src/routes/auth.ts:78
#    Fix: Add rate limiting (e.g., 3 requests per hour per email)
#
# Security review found 4 issues. Address before merging.
```
