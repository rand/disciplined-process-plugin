# Disciplined Process Plugin Specifications
[SPEC-00]

## Purpose

[SPEC-00.01] This document defines the specifications for the disciplined-process plugin for Claude Code.

## Scope

[SPEC-00.02] The plugin provides a rigorous, traceable AI-assisted development workflow with:
- Task tracking integration
- Specification management with traceability
- Architecture Decision Records
- Code review (standard and adversarial)
- Goal-backward verification

## Sections

| Section | Description | File |
|---------|-------------|------|
| SPEC-00 | Overview (this document) | `00-overview.md` |
| SPEC-01 | Task Tracking | `01-task-tracking.md` |
| SPEC-02 | Specifications and Traceability | `02-specifications.md` |
| SPEC-03 | Architecture Decision Records | `03-architecture-decisions.md` |
| SPEC-04 | Code Review | `04-code-review.md` |
| SPEC-05 | Goal-Backward Verification | `05-verification.md` |
| SPEC-06 | Plan Validation | `06-plan-validation.md` |

## Definitions

[SPEC-00.03] Key terms used throughout this specification:

- **Spec**: A requirement identified by `[SPEC-XX.YY]` format
- **Trace**: A `@trace SPEC-XX.YY` marker linking code to specs
- **ADR**: Architecture Decision Record documenting design choices
- **Task**: A unit of work tracked in the configured task tracker
- **Verification**: Process of confirming goal achievement (not just task completion)
- **Truth**: An observable behavior that must be true for a goal to be achieved
- **Artifact**: A file or component that must exist to support a truth
- **Key Link**: A connection between artifacts that must be wired correctly
