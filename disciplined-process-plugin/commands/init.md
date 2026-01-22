---
description: Initialize project with wizard
argument-hint: [--config <path>] [--minimal] [--force]
---

# Initialize Disciplined Process

Interactive setup wizard for the disciplined development workflow.

## Behavior

1. **Check for existing config**: Look for `.claude/dp-config.yaml`
2. **If config exists**: Display config summary and ask for confirmation or edits
3. **If no config**: Run interactive wizard
4. **Create structure**: Set up directories, templates, and tooling

## Interactive Wizard Flow

```
+==========================================================================+
|                   Disciplined Process Plugin Setup                       |
+==========================================================================+
```

### Step 1: Task Tracker Selection
```
1. Task Tracker
   -------------
   Which issue tracker would you like to use?

   [C] Chainlink (recommended)
       - SQLite-based, rich features
       - Session management for AI context
       - Milestones, time tracking

   [B] Beads
       - Git-backed, distributed
       - Multi-machine sync via git
       - Lightweight

   [G] GitHub Issues
       - Native GitHub integration
       - Team collaboration

   [M] Markdown
       - Plain files, no dependencies

   [N] None
       - Skip task tracking

   Selection: C
```

### Step 2: Migration (if applicable)
```
2. Migrating from Beads?
   ----------------------
   Detected .beads/ directory with 12 tasks.

   [M] Migrate to Chainlink now
   [S] Skip (keep both, migrate later)
   [R] Remove Beads data

   Selection: M

   Migrating...
   [x] Parsed 12 Beads issues
   [x] Created 12 Chainlink issues
   [x] Generated migration map: .claude/dp-migration-map.json
   [x] Updated spec references

   Migration complete!
```

### Step 3: Enforcement Level
```
3. Enforcement Level
   ------------------
   How strictly should the workflow be enforced?

   [S] Strict - Blocks commits that violate process
       - Require spec references in implementation
       - Require @trace markers in code
       - Block edits to protected files

   [G] Guided (recommended) - Warns but allows override
       - Suggest best practices
       - Warn about missing traces
       - No hard blocks

   [M] Minimal - No enforcement, just tooling
       - Skills available on demand
       - No hooks or enforcement

   Selection: G
```

### Step 4: Adversarial Review
```
4. Adversarial Review
   -------------------
   Enable VDD-style adversarial code review?

   [E] Enabled - Reviews with Gemini before completion
       - Fresh context per review
       - Hallucination detection
       - Iterative improvement loop

   [D] Disabled

   Selection: E

   Adversary model [gemini-2.5-flash]: ↵
```

### Step 5: Language Detection
```
5. Language Detection
   -------------------
   Detected languages: Python, TypeScript

   Installing language-specific rules...
   [x] .claude/rules/python.md
   [x] .claude/rules/typescript.md
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
# Disciplined Process Configuration v2
version: "2.0"

project:
  name: "my-project"
  languages:
    - python
    - typescript

# Issue tracker selection
task_tracker: chainlink  # chainlink | beads | github | linear | markdown | none

# Chainlink-specific configuration
chainlink:
  features:
    sessions: true
    milestones: true
    time_tracking: true
  rules_path: .claude/rules/

# Beads-specific configuration (when task_tracker: beads)
beads:
  auto_sync: true
  daemon: true

# Enforcement level
enforcement: guided  # strict | guided | minimal

# Adversarial review configuration
adversarial_review:
  enabled: true
  model: gemini-2.5-flash
  max_iterations: 5
  prompt_path: .claude/adversary-prompt.md

# Spec configuration
specs:
  directory: docs/spec/
  id_format: "SPEC-{section:02d}.{item:02d}"
  require_issue_link: true  # In strict mode, specs must link to issues

# ADR configuration
adrs:
  directory: docs/adr/
  template: .claude/templates/adr.md

# Traceability configuration
traceability:
  code_patterns:
    - "src/**/*.py"
    - "src/**/*.ts"
    - "lib/**/*"
  test_patterns:
    - "tests/**/*.py"
    - "tests/**/*.ts"

# Degradation behavior
degradation:
  on_tracker_unavailable: warn  # warn | skip | fail
  on_hook_failure: warn
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
+==========================================================================+
|                          Setup Complete!                                 |
+==========================================================================+

Configuration saved to: .claude/dp-config.yaml

Created:
  [x] .claude/dp-config.yaml      - Plugin configuration
  [x] .claude/settings.json       - Hook configuration
  [x] .claude/rules/python.md     - Python best practices
  [x] .claude/rules/typescript.md - TypeScript best practices
  [x] docs/spec/00-overview.md    - Specification template
  [x] docs/adr/template.md        - ADR template
  [x] docs/adr/0001-adopt-dp.md   - Initial ADR

Next steps:
  chainlink session start         # Begin a work session
  chainlink ready                 # See available tasks
  /dp:spec create 01 "Core"       # Create first spec
  /dp:task ready                  # Find work to do

Workflow reminder:
  Orient   → /dp:task ready
  Specify  → /dp:spec add <section> "<requirement>"
  Decide   → /dp:adr create "<decision>"
  Test     → Write tests with @trace SPEC-XX.YY
  Implement→ Code until tests pass
  Review   → /dp:review [adversarial]
  Close    → /dp:task close <id>

Run '/dp:help' for full command reference.
```
