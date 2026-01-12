---
description: Initialize a project with the disciplined development process. Sets up specifications, ADRs, tests, and task tracking with an interactive wizard or from existing config.
argument-hint: [--config <path>] [--minimal] [--force]
---

# Initialize Disciplined Process

This command sets up a project with the disciplined development workflow.

## Behavior

1. **Check for existing config**: Look for `.claude/dp-config.yaml`
2. **If config exists**: Display config summary and ask for confirmation or edits
3. **If no config**: Run interactive wizard
4. **Create structure**: Set up directories, templates, and tooling

## Interactive Wizard Flow

Run wizard when no config exists or user requests edits:

### Step 1: Project Basics
```
🔧 Disciplined Process Setup

Project name: {infer from package.json, Cargo.toml, etc., or ask}
Primary language: {detect or ask: rust, typescript, python, go, zig, other}
```

### Step 2: Task Tracking
```
📋 Task Tracking

This workflow uses task tracking for work management.

Checking available providers...
  ✓ Beads (bd CLI found, git initialized)
  ✗ GitHub Issues (gh CLI not found)
  ✓ Linear (linear CLI found)
  ✓ Markdown (always available)
  ✓ None (skip tracking)

Options:
  1. Beads (recommended) - Git-backed, dependency-aware
     Features: ready work, dependencies, discovered-from linking
  2. GitHub Issues - GitHub issue integration
     Features: ready work (via labels), milestones
     ⚠️  Requires: gh CLI (not found - install with 'brew install gh')
  3. Linear - Linear app integration
     Features: ready work, native priorities
  4. Markdown - Plain markdown files in docs/tasks/
     Features: ready work (manual status)
  5. None - Skip task tracking

Choice [1]:
```

**CLI Verification**: Before accepting a provider choice, verify the required CLI is available:
- **Beads**: Check `command -v bd` and `git rev-parse --git-dir`
- **GitHub**: Check `command -v gh` and `gh auth status`
- **Linear**: Check `command -v linear`

If a provider's CLI is missing, show installation instructions and allow:
- Install now (if possible)
- Choose different provider
- Proceed anyway (with warning)

### Step 3: Test Frameworks
```
🧪 Test Configuration

Based on {language}, recommended frameworks:

Unit tests:     {framework} ✓
Integration:    {framework} ✓
Property tests: {framework} [install? y/n]
E2E tests:      {framework} [configure? y/n]
```

### Step 4: Enforcement Level
```
⚙️ Enforcement Level

How strictly should the workflow be enforced?

  1. Strict (default)
     - Hooks block commits without passing tests
     - Require spec references in implementation
     - Require task IDs in commits

  2. Guided
     - Hooks warn but don't block
     - Skills suggest best practices
     - No hard requirements

  3. Minimal
     - Skills available on demand
     - No hooks or enforcement
     - For exploratory work

Choice [1]:
```

### Step 5: Confirmation
```
📁 Ready to create:

  .claude/dp-config.yaml          - Configuration
  .claude/settings.json           - Hooks and permissions (merge with existing)
  docs/
    spec/00-overview.md           - Specification template
    adr/template.md               - ADR template
    adr/0001-adopt-disciplined-process.md
    process/code-review.md        - Review checklist
    process/workflow.md           - Workflow reference
  tests/
    unit/.gitkeep
    integration/.gitkeep
    property/.gitkeep
    e2e/.gitkeep
  CLAUDE.md                       - Update with project info (or create)

{If Beads selected:}
  .beads/                         - Initialize via 'bd init'

Proceed? [Y/n]:
```

## Config File Format

`.claude/dp-config.yaml`:

```yaml
# Disciplined Process Configuration
version: "1.0"

project:
  name: "my-project"
  language: "typescript"
  
tracking:
  provider: "beads"  # beads | github | linear | markdown | none
  
testing:
  frameworks:
    unit: "vitest"
    integration: "vitest"
    property: "fast-check"
    e2e: "playwright"
    
enforcement:
  level: "strict"  # strict | guided | minimal
  
hooks:
  pre_commit:
    - "run_tests"
    - "check_traces"
  post_commit:
    - "sync_tasks"
```

## Arguments

- `--config <path>`: Use specific config file
- `--minimal`: Skip optional components (property tests, e2e)
- `--force`: Overwrite existing files without prompting
- `--wizard`: Force wizard even if config exists

## Execution

After collecting configuration:

1. Create `.claude/dp-config.yaml`
2. Update/create `.claude/settings.json` with hooks
3. Create `docs/spec/00-overview.md` from template
4. Create `docs/adr/template.md`
5. Create initial ADR documenting this adoption
6. Create `docs/process/code-review.md`
7. Create test directory structure
8. Update `CLAUDE.md` with project adaptations
9. If Beads: run `bd init --quiet`
10. Display next steps

## Post-Init Output

```
✅ Disciplined process initialized!

Next steps:
  1. Review and customize docs/spec/00-overview.md
  2. Create your first spec: /dp:spec create 01-core
  3. Check ready work: /dp:task ready
  4. Start implementing with test-first approach

Run '/dp:help' for command reference.
```
