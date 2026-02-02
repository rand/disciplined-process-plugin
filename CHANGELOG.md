# Changelog

## [2.1.1] - 2026-02-02

### Fixed
- **hook-dispatch.sh**: Export `CLAUDE_PLUGIN_ROOT` env var so Go binaries can find plugin root

### Added
- `phase-context.py` — command hook for UserPromptSubmit that injects current DP phase and active task as context (replaces prompt hook)
- `spec-info.py` — command hook for PreToolUse Edit/Write that reports spec references in edited files (informational, never blocks)
- `session-end-check.py` — command hook for Stop that reports uncommitted changes and open tasks

### Removed
- `UserPromptSubmit` prompt hook — caused Claude to block "vague" prompts; replaced with phase-context.py command hook
- `PreToolUse` spec-check prompt hook on Edit/Write/MultiEdit — blocked simple edits; replaced with spec-info.py command hook
- `Stop` prompt hook — replaced with session-end-check.py command hook

### Changed
- Hook architecture: prompt hooks replaced with command hooks that provide dynamic state data; CLAUDE.md provides static workflow instructions
- Only remaining prompt hook is `PreToolUse` on `Bash(git commit*)` for test-before-commit enforcement (targeted, intentional)

## [2.1.0] - 2026-02-02

### Added
- Go validation binaries: trace-validator, coverage-check, adr-validator, phase-emitter
- Hybrid hook architecture: prompt-based hooks for LLM judgment + Go binaries for validation
- Cross-plugin event system for DP↔RLM coordination
- JSON Schema definitions for DP events (phase-transition, spec-review, task-update)
- Python event emission/consumption helpers (`scripts/events/`)
- Platform-aware hook dispatcher with fallback chain
- GitHub Actions CI for cross-compilation (5 platforms)
- Unit tests for hookio and events packages

### Changed
- hooks.json redesigned with prompt-based hooks for process enforcement
- Session start now emits initial orient phase event
- Trace validator uses filepath.Walk for recursive test discovery

### Deprecated
- Python hook scripts moved to `scripts/legacy/`
- Set `DP_USE_LEGACY_HOOKS=1` to use legacy Python hooks
