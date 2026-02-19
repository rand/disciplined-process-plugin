# Implementation Plan

**Parent:** [README.md](./README.md)

---

## Overview

Six phases, roughly 3–4 days each. The plan is designed so each phase produces a usable increment — Phase 1 alone is a functioning decomposition prompt that can be used manually.

---

## Phase 1: Decomposition Prompt + Subagent (3–4 days)

Write and test the decomposition prompt including hole identification. Package as:

- `.claude/agents/decomposer.md` (Claude Code subagent)
- Standalone prompt template (for API calls / Codex)
- Task executor skill (`.claude/agents/task-executor.md`)

Test against 3–4 real specs of varying format, size, and quality. Iterate until JSON output is consistently well-structured, holes are correctly identified, and dependency graphs are valid.

**Deliverables:** Decomposer subagent definition, task executor skill, manual testing results.

## Phase 2: CLI Wrapper + Output Generation (3–4 days)

Write the `spec-decompose` CLI (Python, minimal dependencies) that:

- Reads spec files, counts tokens (tiktoken)
- Dispatches to decomposition subagent / API
- Validates the output graph (cycle detection, coverage, sizing per [context-sizing.md](./context-sizing.md))
- Generates `bd` script and plan markdown (including holes)
- Generates Markdown task/hole files and `state.yaml`

Test end-to-end: spec → plan → script → Beads issues → `bd ready` → agent executes.

**Deliverables:** `spec-decompose` CLI, Beads script generation, Markdown output generation, graph validation.

## Phase 3: Diff-Based Re-Decomposition (3–4 days)

Implement `--diff` mode per [diff.md](./diff.md):

- Snapshot existing Beads/Markdown state
- Subagent receives both new spec and existing state
- Diff classification (unchanged/modified/new/removed) including holes
- Incremental script generation
- Human review plan for rework items

Test: modify a spec after initial decomposition, run diff, verify correct classification and minimal updates.

## Phase 4: Progress Reporter (3–4 days)

Implement `progress-report` per [progress-report.md](./progress-report.md):

- State extraction from Beads (`bd stats/list --json`) and git
- Report generation (Markdown + JSON) including Holes section
- Trigger condition evaluation (including hole-specific triggers)
- Watch/daemon mode
- Broadcast: file, Slack (webhook), Discord (webhook), email (sendmail)

## Phase 5: Multi-Agent Orchestration (2–3 days)

Implement `--orchestrate` per [orchestration.md](./orchestration.md):

- Parallel group detection → phase generation
- Fan-out script generation for Claude Code
- Hole-aware pull-based loop template
- Verification gates between phases
- Integration with progress reporter (trigger on phase completion)

## Phase 6: Polish + Cross-Agent Testing (ongoing)

- Test with Codex, Gemini CLI, other agent systems
- Refine token estimation based on observed actual consumption
- Add `--existing-code` for better file size estimates
- Edge cases: very large specs, specs with no structure, adversarial inputs
- Documentation and examples

---

## Open Questions

1. **Language for CLI wrapper.** Python is most portable and has good libraries for token counting (tiktoken). Shell is simpler but brittle for JSON parsing. **Recommendation:** Python with minimal dependencies.

2. **Token counting model.** Different models tokenize differently. Should the tool accept a `--tokenizer` flag, or use `cl100k_base` as a reasonable approximation? **Recommendation:** Default to `cl100k_base`, accept `--tokenizer` as advanced option.

3. **Beads compaction interaction.** Beads has its own compaction (summarizing old closed tasks). Should progress reports be aware of this? **Recommendation:** Independent systems — progress reports are a separate historical record.

4. **Report retention.** How many progress reports to keep? **Recommendation:** Keep all (they're small). Auto-archive after epic completion.

5. **Code snippets in reports.** Currently reports reference files changed but don't inline code. Including key snippets (API signatures) might help reviewers. **Recommendation:** Add as `--verbose` flag, not default.

6. **Hole auto-resolution during decomposition.** The `--auto-resolve` flag would have agents attempt validation/research holes during decomposition itself. This adds latency but may reduce hole count. **Recommendation:** Implement in Phase 2, default off.
