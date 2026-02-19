---
description: Decompose specifications into dependency-aware work items
argument-hint: <spec-files...> [--diff] [--output beads|markdown] [--orchestrate]
---

# Decompose Command

Turns specifications into dependency-aware, context-window-sized work items for AI agents. Ambiguities become first-class **holes** that block downstream work until explicitly resolved.

## Usage

```
/dp:decompose <spec-files...> [options]
```

## Modes

### Fresh Decomposition (default)
```
/dp:decompose docs/spec/auth.md
```
Creates a complete task graph from scratch.

### Diff Mode
```
/dp:decompose --diff docs/spec/auth.md
```
When specs change, diffs against existing progress rather than starting over.

### Orchestrate Mode
```
/dp:decompose docs/spec/auth.md --orchestrate --parallel-slots 4
```
Generates a fan-out script for multi-agent parallel execution.

### Dry Run
```
/dp:decompose docs/spec/auth.md --dry-run
```
Shows the plan without generating output files.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output, -o` | beads | Output format: `beads` or `markdown` |
| `--dir` | docs/tasks/ | Output directory for markdown mode |
| `--context-window` | 200000 | Target context window in tokens |
| `--constitution` | none | Path to constitution/principles file |
| `--diff` | false | Diff against existing state |
| `--holes-strategy` | graph | How to handle ambiguities: `graph`, `warn`, `strict`, `assume` |
| `--auto-resolve` | false | Let agents resolve validation/research holes |
| `--orchestrate` | false | Generate fan-out orchestration script |
| `--parallel-slots` | 3 | Max concurrent agents |
| `--model` | opus | Model for decomposition subagent |
| `--existing-code` | none | Codebase path for accurate sizing |
| `--epic-title` | auto | Override generated epic title |
| `--dry-run` | false | Plan only, no output files |
| `--json-input` | none | Read decomposition from JSON file |

## Output Files

| File | When | Contents |
|------|------|----------|
| `decompose-plan.md` | Always | Human-readable plan |
| `decompose-plan.sh` | `--output beads` | `bd` commands to execute |
| `decompose-diff.md` | `--diff` | Change analysis |
| `decompose-diff.sh` | `--diff --output beads` | Incremental commands |
| `orchestrate.sh` | `--orchestrate` | Fan-out script |
| `docs/tasks/` | `--output markdown` | Task/hole files + state.yaml |

## Workflow

```bash
# 1. Decompose
/dp:decompose docs/spec/auth.md

# 2. Review the plan
cat decompose-plan.md

# 3. Execute (creates Beads issues)
bash decompose-plan.sh

# 4. Start working
bd ready
```

## Integration

- Uses the `decomposer` subagent (`.claude/agents/decomposer.md`) for clean-context analysis
- Work items follow the `task-executor` skill workflow
- Holes use Beads labels: `hole`, `hole:clarification`, `hole:agent-resolvable`, etc.
- Progress tracked via `/dp:progress` command
