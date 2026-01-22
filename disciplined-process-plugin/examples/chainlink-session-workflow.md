# Chainlink Session Workflow

Using session management for context preservation across Claude Code restarts.

## Scenario

Working on a complex refactoring task that spans multiple sessions.

## Starting a Session

```bash
# Start a tracked session with description
/dp:session start "Refactoring payment processing module"

# Output:
# Session started: session-2024-01-15-001
# Description: Refactoring payment processing module
# Time: 0:00:00

# Check what's available
/dp:task ready

# Output:
# Ready tasks (no blockers):
#   [P1] chainlink-89: Extract payment gateway abstraction
#   [P2] chainlink-90: Add Stripe integration
#   [P2] chainlink-91: Add PayPal integration

# Claim task AND start timer in one command
/dp:session work chainlink-89

# Output:
# Claimed: chainlink-89 - Extract payment gateway abstraction
# Timer started
# Session: session-2024-01-15-001
```

## Working Within a Session

```bash
# Check session status anytime
/dp:session status

# Output:
# Session: session-2024-01-15-001
# Description: Refactoring payment processing module
# Duration: 1:23:45
# Active task: chainlink-89 (Extract payment gateway abstraction)
# Timer: 0:45:12
#
# Handoff notes from previous session:
#   "Started extracting PaymentGateway interface.
#    Completed: gateway.ts, stripe-adapter.ts
#    Next: paypal-adapter.ts, update existing code to use interface"
```

## Ending a Session with Handoff Notes

When you need to stop (end of day, context switch, etc.):

```bash
# End session with handoff notes for next time
/dp:session end --notes "Completed PaymentGateway interface extraction.
Created adapters for Stripe and PayPal.
Next session: Update checkout.ts to use new interface (line 145-230).
Watch out: The webhook handler still uses old direct Stripe calls.
Test: npm test -- --grep 'payment'"

# Output:
# Session ended: session-2024-01-15-001
# Duration: 2:15:30
# Tasks worked: chainlink-89
# Handoff notes saved
#
# Next session will show these notes automatically.
```

## Resuming Work

When starting a new Claude Code session:

```bash
# Session start hook automatically shows context
# Output on session start:
#
# =================================================
# Disciplined Process - Session Context
# =================================================
#
# Previous session: session-2024-01-15-001 (2:15:30)
# Handoff notes:
#   "Completed PaymentGateway interface extraction.
#    Created adapters for Stripe and PayPal.
#    Next session: Update checkout.ts to use new interface (line 145-230).
#    Watch out: The webhook handler still uses old direct Stripe calls.
#    Test: npm test -- --grep 'payment'"
#
# In-progress tasks:
#   chainlink-89: Extract payment gateway abstraction
#
# Ready tasks:
#   chainlink-90: Add Stripe integration
#   chainlink-91: Add PayPal integration

# Start new session continuing the work
/dp:session start "Continuing payment refactor - checkout integration"

# Resume working on the same task
/dp:session work chainlink-89
```

## Session Best Practices

### Write Good Handoff Notes

Good handoff notes include:
- What was completed
- What's next (specific files/lines if possible)
- Gotchas or things to watch out for
- How to test the current state

```bash
# Good handoff notes
/dp:session end --notes "Implemented rate limiting for /api/auth endpoints.
Completed: auth-middleware.ts, rate-limiter.ts
Config in: config/rate-limits.yaml
Next: Add rate limit headers to responses (X-RateLimit-*)
Gotcha: Redis connection pooling not configured for high load
Test: npm test -- auth && curl -v localhost:3000/api/auth/login"

# Bad handoff notes (too vague)
/dp:session end --notes "worked on auth stuff"
```

### Track Multiple Tasks

```bash
# Start session
/dp:session start "Sprint 42 work"

# Work on first task
/dp:session work chainlink-100
# ... do work ...
/dp:task close chainlink-100

# Switch to another task in same session
/dp:session work chainlink-101
# ... do work ...

# End session - both tasks tracked
/dp:session end --notes "Completed chainlink-100 and chainlink-101.
chainlink-100: Full implementation, merged to main.
chainlink-101: Tests written, implementation 80% done.
Next: Finish error handling in api-client.ts"
```

### View Session History

```bash
# Use Chainlink CLI directly for history
chainlink session list --limit 10

# Output:
# session-2024-01-15-002  2:30:00  Sprint 42 work
# session-2024-01-15-001  2:15:30  Refactoring payment processing module
# session-2024-01-14-001  3:45:00  Bug fixes batch
```
