# spec-decompose: Constraint-Aware Specification Decomposition

**Version:** 3.0  
**Status:** Specification  
**Companion tool:** [progress-report](./progress-report.md)

---

## TL;DR

`spec-decompose` turns specifications into dependency-aware, context-window-sized work items for AI agents. Ambiguities become first-class **holes** that block downstream work until explicitly resolved. When specs change, the tool diffs against existing progress rather than starting over. A companion `progress-report` tool provides structured status summaries to humans and agents.

---

## The Problem

AI coding agents reliably fail at three things when given a specification:

1. **Decomposition.** They create orphaned tasks, confuse dependency types, attempt work out of order, and produce tasks too large for a single context window.
2. **Ambiguity handling.** They either halt on ambiguity or silently assume and build on potentially wrong foundations. There is no middle ground that tracks unknowns structurally.
3. **Change absorption.** When specs change mid-flight, there is no principled way to update the task graph without losing progress or creating inconsistencies.

These are not prompting problems — they are structural problems that require structural solutions.

## The Solution

Two complementary tools that form a complete spec-to-execution pipeline:

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `spec-decompose` | Spec documents | Work items + holes in Beads or Markdown | Turn specs into executable work graphs |
| `progress-report` | Project state (git, Beads, task files) | Timestamped summaries + broadcasts | Keep humans and agents oriented |

### What These Tools Do NOT Do

- Author or edit specs (use a spec-writing tool or write them yourself)
- Execute work items (agents do that)
- Replace Beads or any task tracker (they *feed* trackers)
- Manage the full project lifecycle

---

## Architecture

```
Human or Orchestrator
    │
    │  "decompose this spec"
    ▼
┌──────────────────────────────────────────────┐
│  spec-decompose CLI                          │
│                                              │
│  1. Read spec files, count tokens            │
│  2. Read existing state (Beads or Markdown)  │
│  3. Determine: fresh decompose or diff?      │
│  4. Dispatch to decomposition subagent       │
│  5. Parse + validate structured output       │
│  6. Generate output (bd script or md files)  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  Decomposition Subagent                      │
│  (Clean context window — spec only)          │
│                                              │
│  System: Decomposition instructions          │
│  User: Full spec text + existing state       │
│  Output: Structured JSON                     │
│                                              │
│  Model: Opus-class (deep reasoning about     │
│         dependencies, ambiguity, sizing)     │
└──────────────────────────────────────────────┘
```

**Key architectural property:** The decomposer gets a *clean context window* dedicated entirely to analysis. Large specs (50–100K+ tokens) would consume an agent's working memory if loaded alongside other context. The decomposition therefore runs as a dedicated subagent or standalone API call.

For Claude Code: `.claude/agents/decomposer.md`. For standalone use: an API call. For Codex: a separate task/session.

### Sharding for Exceptionally Large Specs

If a spec exceeds ~150K tokens, the CLI shards it:

1. **Overview pass** (~50K + section headers from the rest) → high-level epic/issue structure and requirement clusters.
2. **Cluster passes** (each cluster with its relevant spec sections) → detailed task decomposition.
3. **Merge pass** → validate the combined graph.

For most specs (even large ones), a single call with a 200K context window suffices.

---

## Document Index

This specification is organized into context-efficient sub-documents. Each is self-contained enough to be loaded independently into an agent's context window.

| Document | Tokens (est.) | Contents |
|----------|--------------|----------|
| **[decomposition.md](./decomposition.md)** | ~4K | Core algorithm: input normalization, 5-step decomposition, output generation |
| **[holes.md](./holes.md)** | ~4K | First-class unknowns: taxonomy, lifecycle, resolution patterns |
| **[context-sizing.md](./context-sizing.md)** | ~2K | Budget model, sizing rules, split/merge heuristics |
| **[diff.md](./diff.md)** | ~3K | Incremental re-decomposition when specs change |
| **[orchestration.md](./orchestration.md)** | ~3K | Multi-agent workflows: parallel groups, fan-out, pull-based |
| **[progress-report.md](./progress-report.md)** | ~4K | Progress reporter: triggers, format, broadcast channels |
| **[cli-reference.md](./cli-reference.md)** | ~3K | Complete CLI reference for both tools + configuration |
| **[agent-skills.md](./agent-skills.md)** | ~2K | Task executor and hole resolution skills for agents |
| **[schemas.md](./schemas.md)** | ~3K | JSON schemas, YAML configs, Beads conventions, file formats |

### Cross-Reference Conventions

- `[ALGO-n]` — Decomposition algorithm steps (in [decomposition.md](./decomposition.md))
- `[HOLE-type]` — Hole taxonomy entries (in [holes.md](./holes.md))
- `[SIZE-n]` — Sizing rules (in [context-sizing.md](./context-sizing.md))
- `[DIFF-n]` — Diff algorithm steps (in [diff.md](./diff.md))

---

## Quick Start

```bash
# Fresh decomposition into Beads
spec-decompose docs/spec/auth.md
cat decompose-plan.md        # Review the plan
bash decompose-plan.sh       # Execute it

# Re-decompose after spec change
spec-decompose --diff docs/spec/auth.md
cat decompose-diff.md        # Review changes
bash decompose-diff.sh       # Apply incrementally

# With multi-agent orchestration
spec-decompose docs/spec/auth.md --orchestrate --parallel-slots 4
bash decompose-plan.sh       # Create work items
bash orchestrate.sh           # Fan out to agents

# Progress reporting
progress-report               # One-shot status
progress-report --watch       # Daemon mode with triggers
```

---

## Integration Points

```
spec-decompose                    progress-report
──────────────                    ───────────────
Spec → Work items + holes         Work items → Status summaries
Spec changes → Graph updates      Status → Human/agent awareness

                    ┌─────────┐
         ┌────────→ │  Agents  │ ────────┐
         │          └─────────┘          │
         │               │               │
    Task graph      Execute tasks    Report progress
    (Beads/MD)      (implement)      (summaries)
         │               │               │
         │          ┌────▼────┐          │
         │          │ Beads / │          │
         └──────────│ Task MD │◄─────────┘
                    └────┬────┘
                         │
                    ┌────▼─────┐
                    │ Progress  │
                    │ Reports   │──→ Humans, Slack, Email, Agents
                    └──────────┘
```

### DP Plugin Commands

```
/dp:decompose <spec-files>         → runs spec-decompose
/dp:decompose --diff <spec-files>  → runs spec-decompose --diff
/dp:progress                       → runs progress-report (one-shot)
/dp:progress --watch               → runs progress-report --watch
/dp:task next                      → delegates to bd ready or reads task files
```
