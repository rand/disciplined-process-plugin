# ADR-0001: Adversarial Validation Architecture

**Status:** Proposed
**Date:** 2026-01-21
**Deciders:** rand
**Relates to:** [SPEC] disciplined-process-plugin-v2-specification.md

## Context

The disciplined-process-plugin v2.0 specification calls for adversarial validation via rlm-claude-code integration, where a different model (Gemini) critiques code changes with fresh context to catch issues the primary model might miss.

**Current State:**
- rlm-core has multi-provider routing (Anthropic, OpenAI) but NO Gemini support
- rlm-core has epistemic verification (claim extraction, KL divergence) but NO adversarial validation
- No "fresh context" mechanism exists for isolated model invocations
- disciplined-process-plugin currently has no adversarial review capability

**The Problem:**
The spec assumes infrastructure that doesn't exist. We need to decide:
1. Where to build the adversarial validation module
2. How to integrate across the rlm ecosystem
3. How to handle graceful degradation when components are unavailable

## Decision

**Build adversarial validation in rlm-core/loop, then integrate with disciplined-process.**

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          rlm-core (Rust)                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │ LLM Client  │  │ Epistemic   │  │ Adversarial (NEW)      │  │
│  │             │  │ Verification│  │                        │  │
│  │ - Anthropic │  │ - Claims    │  │ - AdversarialValidator │  │
│  │ - OpenAI    │  │ - Evidence  │  │ - FreshContextInvoker  │  │
│  │ - Google*   │  │ - KL Budget │  │ - CrossCheckStrategy   │  │
│  └─────────────┘  └─────────────┘  └────────────────────────┘  │
│         │                │                     │                │
│         └────────────────┴─────────────────────┘                │
│                          │                                      │
│                   ┌──────▼──────┐                               │
│                   │ Trajectory  │  (Observable events)          │
│                   └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
┌─────────────────────┐    ┌─────────────────────────────────────┐
│   rlm-claude-code   │    │       disciplined-process           │
│                     │    │                                     │
│ - Python bindings   │───►│ - RLMCapabilities.discover()        │
│ - get_validator()   │    │ - /dp:review adversarial            │
│ - Fallback impl     │    │ - Graceful degradation              │
└─────────────────────┘    └─────────────────────────────────────┘
```

### Key Design Decisions

1. **Adversarial module lives in rlm-core** (not in disciplined-process)
   - Reuses existing LLM client infrastructure
   - Integrates with epistemic claim extraction
   - Benefits all consumers (rlm-claude-code, recurse, etc.)
   - Single implementation, multiple consumers

2. **Feature-gated with Cargo features**
   - `adversarial` feature gates the module
   - `gemini` feature gates Provider::Google
   - Allows gradual rollout and emergency disable
   - Consumers can opt-in via `features = ["adversarial"]`

3. **Fresh context via FreshContextInvoker**
   - New struct that invokes LLM WITHOUT conversation history
   - Only passes: system prompt + query + optional evidence subset
   - Prevents "relationship drift" where adversary becomes too agreeable

4. **Capability negotiation in disciplined-process**
   - `RLMCapabilities.discover()` detects available features at runtime
   - Graceful degradation to manual review if adversarial unavailable
   - /dp:health shows RLM ecosystem status

5. **Pure-Python fallback in rlm-claude-code**
   - `get_validator()` returns Rust validator if available
   - Falls back to `PythonAdversarialValidator` if rlm-core missing
   - Ensures adversarial review works without full Rust stack

## Alternatives Considered

### Alternative A: Build adversarial in disciplined-process directly
**Rejected because:**
- Would duplicate LLM client infrastructure
- Wouldn't benefit other rlm ecosystem consumers
- Would require separate Gemini API integration
- Higher maintenance burden

### Alternative B: Build adversarial in rlm-claude-code (Python only)
**Rejected because:**
- Performance concerns for production use
- Wouldn't benefit recurse (Go consumer)
- Misses opportunity to leverage Rust type safety
- Would need to reimplement claim extraction

### Alternative C: Defer adversarial to v2.1
**Rejected because:**
- Core value proposition of v2.0 spec
- VDD methodology is differentiated feature
- Building infrastructure now enables future enhancements

## Consequences

### Positive
- Single adversarial implementation serves entire ecosystem
- Feature flags allow gradual rollout with low risk
- Graceful degradation ensures users aren't blocked
- Clear upgrade path for all consumers
- Rust performance for production workloads

### Negative
- More complex dependency chain (dp → rlm-cc → rlm-core)
- Phase 0 work required before Phase 3 can start
- Breaking changes in rlm-core require coordinated releases
- Users need rlm-core built with features for full functionality

### Risks
- Gemini API integration may have unforeseen issues
- Cross-version compatibility requires careful testing
- Fresh context isolation may not be sufficient for true "adversarial" behavior

## Implementation

See `.claude/plans/dp-v2-implementation.md` for detailed task breakdown.

**Phase 0 (rlm-core):**
1. Add Provider::Google and GeminiClient
2. Create adversarial module with feature flag
3. Implement FreshContextInvoker
4. Add trajectory events for observability
5. Expose via Python bindings

**Phase 3 (disciplined-process):**
1. Implement RLMCapabilities discovery
2. Wire /dp:review adversarial to rlm-core
3. Add code-specific hallucination detection
4. Implement graceful degradation

## References

- [disciplined-process-plugin-v2-specification.md](../../disciplined-process-plugin-v2-specification.md)
- [VDD Methodology](https://gist.github.com/dollspace-gay/45c95ebfb5a3a3bae84d8bebd662cc25)
- [RLM Paper](https://arxiv.org/abs/2512.24601)
- [rlm-core](file:///Users/rand/src/loop/rlm-core)
- [rlm-claude-code](file:///Users/rand/src/rlm-claude-code)
