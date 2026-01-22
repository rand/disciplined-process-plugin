# Disciplined Process Plugin

A rigorous, traceable AI-assisted development workflow plugin for Claude Code.

## Why Use This?

AI coding assistants are powerful but can produce inconsistent results. This plugin brings discipline to AI-assisted development by enforcing a proven workflow:

- **Specify before you code** — Write requirements with traceable IDs before implementation
- **Test before you implement** — Tests reference specs and must exist before code
- **Document decisions** — Architecture Decision Records capture the "why"
- **Track dependencies** — Know what's ready to work on and what's blocked
- **Enforce or guide** — Strict mode blocks bad commits; guided mode just warns

Inspired by the [Rue language](https://github.com/rue-language/rue) development process.

## Features

- **Specification-first**: Write specs before code, with traceable paragraph IDs (`[SPEC-01.03]`)
- **Test-driven**: Tests reference specs via `@trace` markers, run before implementation
- **ADRs**: Document architectural decisions systematically
- **Task tracking**: Dependency-aware work management (Beads default, or GitHub/Linear/Markdown)
- **Traceability**: Every line links to specs — know why code exists
- **Enforcement**: Configurable hooks enforce the process (strict), warn (guided), or stay out of the way (minimal)

## The Workflow

A 7-phase loop: **Orient → Specify → Decide → Test → Implement → Review → Close**

Each phase has supporting commands (`/dp:task`, `/dp:spec`, `/dp:adr`, `/dp:review`). See [full documentation](./disciplined-process-plugin/README.md) for details.

## Quick Start

```bash
# 1. Add the plugin repository
/plugin marketplace add rand/disciplined-process-plugin

# 2. Install the plugin
/plugin install disciplined-process@disciplined-process-plugin

# 3. Initialize your project (interactive wizard)
/dp:init

# 4. Start working
/dp:task ready
```

See [full documentation](./disciplined-process-plugin/README.md) for detailed usage.

## Installation

### Prerequisites

- **Claude Code** version 2.0.0 or higher
- **Git** (for Beads task tracker, if used)

### Step-by-Step

1. **Add the plugin repository:**
   ```bash
   /plugin marketplace add rand/disciplined-process-plugin
   ```

2. **Install the plugin:**
   ```bash
   /plugin install disciplined-process@disciplined-process-plugin
   ```

3. **Verify installation:**
   ```bash
   /plugin list
   ```
   You should see `disciplined-process` listed.

4. **Initialize your project:**
   ```bash
   /dp:init
   ```
   The wizard will configure language, task tracking, test frameworks, and enforcement level.

5. **Validate setup:**
   ```bash
   /dp:help                      # Should show command reference
   cat .claude/dp-config.yaml    # Should show your configuration
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/dp:init` | Initialize project with interactive wizard |
| `/dp:task` | Task tracking (ready, create, show, update, close) |
| `/dp:spec` | Specification management (create, add, coverage) |
| `/dp:adr` | Architecture Decision Records |
| `/dp:review` | Code review checklist |
| `/dp:help` | Help and workflow reference |

## Updating

```bash
/plugin marketplace update rand/disciplined-process-plugin
/plugin update disciplined-process@disciplined-process-plugin
```

**Important:** After updating, re-merge hooks to update paths:

```bash
python3 ~/.claude/scripts/merge-plugin-hooks.py
```

## Hooks

This plugin uses Claude Code hooks to enforce the disciplined workflow:

| Hook | Event | Purpose |
|------|-------|---------|
| `pre-commit-check.sh` | `PreToolUse(git commit)` | Block commits without tests/traces (strict mode) |
| `check-trace-markers.sh` | `PostToolUse(Write)` | Warn about missing `@trace` markers |
| `session-start.sh` | `SessionStart` | Show ready work count |
| `pre-push-sync.sh` | `PreToolUse(git push)` | Sync task tracker before push |

### Hook Setup

Plugin hooks need to be merged into `~/.claude/settings.json`:

```bash
# After install or update:
python3 ~/.claude/scripts/merge-plugin-hooks.py
```

If you don't have the merge script:

```bash
mkdir -p ~/.claude/scripts
curl -o ~/.claude/scripts/merge-plugin-hooks.py \
  https://raw.githubusercontent.com/rand/rlm-claude-code/main/scripts/merge-plugin-hooks.py
```

### Verifying Hooks

```bash
# Check hooks are registered
cat ~/.claude/settings.json | jq '.hooks | keys'

# Should show: PreToolUse, PostToolUse, SessionStart
```

### Troubleshooting Hooks

**Hooks not running:**
1. Check enforcement level isn't "minimal" in `dp-config.yaml`
2. Run `python3 ~/.claude/scripts/merge-plugin-hooks.py`
3. Restart Claude Code

**Commits not being blocked (strict mode):**
1. Verify hooks point to current plugin version
2. Check `~/.claude/settings.json` has `PreToolUse` with `Bash(git commit*)` matcher

## Uninstalling

```bash
/plugin uninstall disciplined-process@disciplined-process-plugin
/plugin marketplace remove rand/disciplined-process-plugin
```

Note: Project files created by `/dp:init` are not removed automatically.

## Troubleshooting

### Commands not recognized
1. Verify installation: `/plugin list`
2. Restart Claude Code
3. Reinstall the plugin

### Wizard doesn't detect my language
Select "other" when prompted. The wizard checks for `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, and `build.zig`.

### Hooks not running
1. Check enforcement level isn't "minimal"
2. Verify `.claude/settings.json` exists
3. Run `chmod +x .claude/scripts/*.sh`

### Beads commands fail
1. Ensure Git is initialized: `git status`
2. Check `.beads/` directory exists
3. Run `bd init` manually if needed

## License

MIT

## Support

- [Documentation](./disciplined-process-plugin/README.md)
- [GitHub Issues](https://github.com/rand/disciplined-process-plugin/issues)
- [Discussions](https://github.com/rand/disciplined-process-plugin/discussions)
