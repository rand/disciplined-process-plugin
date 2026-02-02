# Changelog

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
