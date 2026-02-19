# Context-Window Sizing

**Parent:** [README.md](./README.md)  
**Related:** [decomposition.md](./decomposition.md) · [cli-reference.md](./cli-reference.md)

---

## Overview

Every work item produced by `spec-decompose` must fit within an agent's context window with room to spare for reasoning, code generation, testing, and tool calls. The sizing model treats the context window as a token budget and enforces constraints that prevent agents from running out of working memory mid-task.

---

## The Budget Model `[SIZE-1]`

```
Available context window (e.g., 200K tokens)
  minus  System prompt / CLAUDE.md / agent overhead     (~5-10K)
  minus  Task description loaded into context            (~1-3K)
  minus  Context files the task needs to read            (~2-20K)
  =      Working memory for the agent                    (remaining)

Working memory must cover:
  Reading additional files during implementation          ~10-40K
  Agent reasoning / extended thinking                     ~20-60K
  Code generation                                         ~10-30K
  Test generation                                         ~5-20K
  Tool call overhead (each call ~200-500 tokens)          ~5-15K
  Verification / git operations                           ~2-5K
```

---

## Sizing Rules

### Rule 1: Overhead Ceiling `[SIZE-2]`

Task overhead (description + required context files) ≤ **15% of target window**.

| Window | Max Overhead |
|--------|-------------|
| 200K | ~30K |
| 128K | ~19K |
| 64K | ~10K |

### Rule 2: Total Consumption Ceiling `[SIZE-2b]`

Estimated total consumption (overhead + working memory) ≤ **80% of window**. The remaining 20% is buffer for retries, compaction, exploration, and unexpected file reads.

### Rule 3: Split When Over Budget `[SIZE-3]`

If a task exceeds the budget, split along:

- **Test boundaries** — each sub-task is independently verifiable
- **File boundaries** — each sub-task produces distinct files

Both conditions should hold: a sub-task should produce its own files AND have its own tests. This ensures each piece can be completed and verified in isolation.

### Rule 4: Merge When Trivially Small `[SIZE-4]`

If a task's total estimated consumption is **<5K tokens**, merge it with an adjacent task in the same issue. Tiny tasks create unnecessary context-switching overhead for agents.

---

## Token Estimation Heuristics

| Component | Estimation Method |
|-----------|-------------------|
| Task description | Count tokens in generated text |
| Context files (existing) | Count actual tokens via tokenizer |
| Context files (not yet created) | Estimate from spec: simple module ~2K, API endpoint ~5K, complex module ~10K |
| Implementation code | Simple requirement ~10K, moderate ~20K, complex ~35K |
| Test code | ~40% of implementation estimate |
| Tool call overhead | ~300 tokens × estimated number of tool calls |

These are calibrated for `cl100k_base` tokenization (GPT-4/Claude family). The `--context-window` flag adjusts all sizing calculations proportionally.

---

## Common Configurations

```bash
# Default: 200K (Claude Code with Opus/Sonnet)
spec-decompose ./spec.md

# Smaller window (Codex, smaller models)
spec-decompose ./spec.md --context-window 128000

# Aggressive splitting for parallel fan-out
spec-decompose ./spec.md --context-window 64000
```

Smaller context windows produce more, smaller tasks — which enables higher parallelism at the cost of more inter-task coordination overhead. The default 200K balances task size against parallelism for typical Claude Code usage.

---

## Improving Estimates with `--existing-code`

When decomposing against an existing codebase, the tool can measure actual file sizes instead of estimating:

```bash
spec-decompose ./spec.md --existing-code ./src/
```

This reads the codebase to determine actual token counts for context files that already exist, producing more accurate sizing. Files that don't exist yet still use the heuristic estimates above.
