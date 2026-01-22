# Disciplined Process Plugin v2 Specification

**Version:** 2.0.0-draft  
**Date:** January 21, 2026  
**Author:** Rand Arete  
**Status:** Draft for Implementation

---

## Executive Summary

This specification defines the upgrade path for [disciplined-process-plugin](https://github.com/rand/disciplined-process-plugin) to version 2.0. The update transitions to [Chainlink](https://github.com/dollspace-gay/chainlink) as the default issue tracker while preserving [Beads](https://github.com/steveyegge/beads) as an option, integrates adversarial validation through [rlm-claude-code](https://github.com/rand/rlm-claude-code)'s multi-provider routing, and adopts current Claude Code hooks best practices.

### Key Design Principles

1. **No abstraction layer over trackers** — Claude uses native CLIs directly for better error messages, documentation, and maintainability
2. **Adversarial validation via rlm-claude-code** — Leverages existing model routing infrastructure rather than building parallel systems
3. **Bidirectional spec-issue linking** — Maintains traceability between `[SPEC-XX.YY]` markers and Chainlink issues
4. **Lossless migration** — Preserves all data and traceability when migrating from Beads to Chainlink
5. **Graceful degradation** — Never block the user; when components fail, degrade to simpler functionality with clear guidance on recovery

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Referenced Systems](#2-referenced-systems)
3. [Issue Tracker Strategy](#3-issue-tracker-strategy)
4. [Migration System](#4-migration-system)
5. [Spec-Issue Bidirectional Linking](#5-spec-issue-bidirectional-linking)
6. [Adversarial Validation System](#6-adversarial-validation-system)
7. [Hooks Architecture](#7-hooks-architecture)
8. [Integration with rlm-claude-code](#8-integration-with-rlm-claude-code)
9. [Initialization Wizard](#9-initialization-wizard)
10. [Command Reference](#10-command-reference)
11. [File Structure](#11-file-structure)
12. [Implementation Notes](#12-implementation-notes)
13. [Failure Modes and Graceful Degradation](#13-failure-modes-and-graceful-degradation)

---

## 1. System Architecture

### 1.1 High-Level Overview

```
+-----------------------------------------------------------------------+
|                          rlm-claude-code                              |
|                                                                       |
|  +----------------+  +----------------+  +------------------------+   |
|  |  Orchestrator  |  |  Model Router  |  |    Context Manager     |   |
|  |                |<-|  (Anthropic,   |  |   (handles large ctx)  |   |
|  |                |  |   Gemini, etc) |  |                        |   |
|  +----------------+  +----------------+  +------------------------+   |
+-----------------------------------------------------------------------+
         |                      |
         v                      v
+------------------------+  +---------------------------------------+
|  disciplined-process   |  |       Adversarial Review Agent        |
|                        |  |  (uses rlm model router to invoke     |
|  +------------------+  |  |   Gemini with fresh context)          |
|  | Chainlink CLI    |  |  +---------------------------------------+
|  | (native commands)|  |
|  +------------------+  |
|                        |
|  +------------------+  |
|  | Specs & ADRs     |  |
|  | ([SPEC-XX.YY])   |  |
|  +------------------+  |
|                        |
|  +------------------+  |
|  | Claude Code      |  |
|  | Hooks (v2.0.45+) |  |
|  +------------------+  |
+------------------------+
```

### 1.2 Component Interaction Flow

```
+========================================================================+
|                         DEVELOPMENT SESSION                            |
+========================================================================+
                                  |
                                  v
+------------------------------------------------------------------------+
|  SessionStart Hook                                                     |
|                                                                        |
|    1. Load Chainlink session context                                   |
|    2. Display previous handoff notes                                   |
|    3. Inject project rules from .claude/rules/                         |
|    4. Set current working issue (if any)                               |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Development Loop                                                      |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  | UserPromptSubmit Hook                                            |  |
|  |   - Validate spec references in requests                         |  |
|  |   - Inject language-specific rules                               |  |
|  |   - Log prompt for audit trail                                   |  |
|  +------------------------------------------------------------------+  |
|                                 |                                      |
|                                 v                                      |
|  +------------------------------------------------------------------+  |
|  | PreToolUse Hook                                                  |  |
|  |   - Block modifications to protected files                       |  |
|  |   - Enforce spec-first workflow (guided/strict mode)             |  |
|  +------------------------------------------------------------------+  |
|                                 |                                      |
|                                 v                                      |
|  +------------------------------------------------------------------+  |
|  | PostToolUse Hook                                                 |  |
|  |   - Run formatters (prettier, gofmt, etc.)                       |  |
|  |   - Update traceability index                                    |  |
|  |   - Validate @trace markers                                      |  |
|  +------------------------------------------------------------------+  |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Review Phase: /dp:review adversarial                                  |
|                                                                        |
|    +--------------+     +--------------+     +--------------+          |
|    |   Gather     |---->|   Invoke     |---->|   Present    |          |
|    |   Context    |     |   Adversary  |     |   Critique   |          |
|    |   (diff,     |     |   (Gemini,   |     |   to Human   |          |
|    |   specs,     |     |   fresh ctx) |     |              |          |
|    |   tests)     |     |              |     |              |          |
|    +--------------+     +--------------+     +--------------+          |
|                                                    |                   |
|                    +-------------------------------+                   |
|                    |               |               |                   |
|                    v               v               v                   |
|               [Accept]       [Reject as       [Done]                   |
|               Address        hallucinated]    Exit loop                |
|               issues         Log & continue                            |
|                    |               |                                   |
|                    +-------+-------+                                   |
|                            |                                           |
|                            v                                           |
|                    Iterate until                                       |
|                    convergence                                         |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Stop Hook                                                             |
|                                                                        |
|    1. Prompt for session handoff notes                                 |
|    2. Update Chainlink session state                                   |
|    3. Sync issue tracker to git                                        |
+------------------------------------------------------------------------+
```

---

## 2. Referenced Systems

### 2.1 Chainlink

**Repository:** https://github.com/dollspace-gay/chainlink  
**Purpose:** SQLite-based local issue tracker with session management

**Key Features:**
- Local-first SQLite storage (`.chainlink/issues.db`)
- Session management with handoff notes for AI context preservation
- Hierarchical issues: Epics → Issues → Sub-issues
- Dependencies (`block`/`unblock`) and related issues (`relate`/`unrelate`)
- Milestones for release planning
- Time tracking with start/stop timers
- `chainlink next` for priority-based work recommendations
- `chainlink tree` for hierarchy visualization
- Claude Code hooks with behavioral guardrails
- Customizable rules in `.chainlink/rules/`

**Why Chainlink over Beads:**
- Session management preserves context across Claude Code restarts
- Richer feature set (milestones, time tracking, recommendations)
- SQLite provides faster queries than JSONL scanning
- Simpler conflict resolution (single local database vs. git-backed JSONL)

### 2.2 Beads

**Repository:** https://github.com/steveyegge/beads  
**Purpose:** Git-backed distributed issue tracker for AI agents

**Key Features:**
- Git as database: JSONL in `.beads/` versioned like code
- Hash-based IDs (`bd-a1b2`) prevent merge collisions
- Four dependency types: blocks, related, parent-child, discovered-from
- Auto-sync between SQLite cache and JSONL
- Semantic compaction for memory decay

**Why Preserve Beads Support:**
- Existing projects already using Beads
- Distributed/git-backed model suits some workflows
- Multi-machine sync via git (no central server)
- Active ecosystem (beads-ui, bdui, vscode-beads)

### 2.3 rlm-claude-code

**Repository:** https://github.com/rand/rlm-claude-code  
**Paper:** [Recursive Language Models (arXiv:2512.24601)](https://arxiv.org/abs/2512.24601)

**Key Features:**
- Intelligent orchestration for complex tasks
- Multi-provider model routing (Anthropic, OpenAI, Gemini)
- Unbounded context handling via REPL decomposition
- Custom agents with configurable model backends
- Trajectory logging and visualization

**Integration Points:**
- Model router for adversarial review (invoke Gemini with fresh context)
- Agents directory for custom adversary agent
- Context manager compatibility with Chainlink's context provider

### 2.4 VDD (Verification-Driven Development)

**Gist:** https://gist.github.com/dollspace-gay/45c95ebfb5a3a3bae84d8bebd662cc25

**Core Concepts:**
- Builder AI implements, Adversary AI (Sarcasmotron) critiques
- Fresh context window per adversary turn prevents "relationship drift"
- Hallucination-based termination: when adversary invents problems, code is complete
- Human arbitrates which critiques are legitimate vs. fabricated

### 2.5 Claude Code Hooks

**Documentation:** https://code.claude.com/docs/en/hooks  
**Reference:** https://code.claude.com/docs/en/hooks-guide

**Current Best Practices (January 2026):**
- Use `.claude/settings.json` at project level
- Python scripts with UV for dependency isolation
- Leverage v2.0.45+ `PermissionRequest` hooks for approval automation
- Use `/hooks` interactive UI for configuration, manual editing for version control
- Hook events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SessionEnd`

---

## 3. Issue Tracker Strategy

### 3.1 Design Decision: No Abstraction Layer

**Rationale:**

1. **Fundamentally different data models** — Chainlink uses SQLite with sessions/milestones; Beads uses git-backed JSONL with hash-based IDs
2. **Feature loss through abstraction** — Chainlink's richer features (sessions, time tracking) would be inaccessible
3. **Claude Code works better with native tools** — Better error messages, tab completion, documentation
4. **Maintenance burden** — Abstraction layer would require updates for each tracker's changes

**Implementation:**

The plugin detects which tracker is configured and:
1. Sets `CLAUDE.md` instructions to use that tracker's native commands
2. Configures hooks appropriate to the tracker
3. Exposes tracker-specific `/dp:*` commands that delegate to native CLI

### 3.2 Configuration Schema

```yaml
# .claude/dp-config.yaml

# Issue tracker selection
task_tracker: chainlink  # Options: chainlink | beads

# Chainlink-specific configuration
chainlink:
  features:
    sessions: true
    milestones: true
    time_tracking: true
  rules_path: .claude/rules/  # Symlinked to .chainlink/rules/

# Beads-specific configuration (when task_tracker: beads)
beads:
  auto_sync: true
  daemon: true

# Enforcement level
enforcement: guided  # Options: strict | guided | minimal

# Adversarial review configuration
adversarial_review:
  enabled: true
  model: gemini-2.5-flash
  max_iterations: 5
  prompt_path: .claude/adversary-prompt.md

# Spec configuration
specs:
  directory: specs/
  id_format: "SPEC-{section:02d}.{item:02d}"
  require_issue_link: true  # In strict mode, specs must link to issues

# ADR configuration
adrs:
  directory: adrs/
  template: .claude/templates/adr.md
```

### 3.3 Command Delegation

When `task_tracker: chainlink`:

| Plugin Command | Executes |
|----------------|----------|
| `/dp:task ready` | `chainlink ready` |
| `/dp:task create "title"` | `chainlink create "title"` |
| `/dp:task show <id>` | `chainlink show <id>` |
| `/dp:task update <id> --status in_progress` | `chainlink update <id> --status in_progress` |
| `/dp:task close <id>` | `chainlink close <id>` |
| `/dp:session start` | `chainlink session start` |
| `/dp:session work <id>` | `chainlink session work <id>` |
| `/dp:session end --notes "..."` | `chainlink session end --notes "..."` |

When `task_tracker: beads`:

| Plugin Command | Executes |
|----------------|----------|
| `/dp:task ready` | `bd ready` |
| `/dp:task create "title"` | `bd create "title"` |
| `/dp:task show <id>` | `bd show <id>` |
| `/dp:task update <id> --status in_progress` | `bd update <id> --status in_progress` |
| `/dp:task close <id>` | `bd close <id>` |
| `/dp:session start` | *(unavailable — Beads doesn't support sessions)* |

---

## 4. Migration System

### 4.1 Beads → Chainlink Migration

```bash
/dp:migrate beads-to-chainlink [--dry-run]
```

**Process:**

```
+------------------------------------------------------------------------+
|  Step 1: Parse Beads Data                                              |
|                                                                        |
|    - Read .beads/issues.jsonl                                          |
|    - Parse hash-based IDs (bd-a1b2, bd-f14c)                           |
|    - Extract: title, description, status, priority, dependencies       |
|    - Preserve hierarchical relationships (bd-a1b2.1, bd-a1b2.2)        |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Step 2: Create Chainlink Issues                                       |
|                                                                        |
|    - Initialize Chainlink if not present: chainlink init               |
|    - Create issues preserving all metadata                             |
|    - Map Beads hash IDs to Chainlink integer IDs                       |
|    - Recreate dependency relationships                                 |
|    - Convert discovered-from to related issues                         |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Step 3: Generate Mapping File                                         |
|                                                                        |
|    Location: .claude/dp-migration-map.json                             |
|                                                                        |
|    {                                                                   |
|      "migrated_at": "2026-01-21T15:30:00Z",                            |
|      "source": "beads",                                                |
|      "target": "chainlink",                                            |
|      "mappings": [                                                     |
|        {                                                               |
|          "bead_id": "bd-a1b2",                                         |
|          "chainlink_id": 1,                                            |
|          "spec_refs": ["SPEC-01.03", "SPEC-01.04"]                     |
|        },                                                              |
|        { "bead_id": "bd-f14c", "chainlink_id": 2, ... }                |
|      ]                                                                 |
|    }                                                                   |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Step 4: Update References                                             |
|                                                                        |
|    - Update spec files: <!-- bd-a1b2 --> to <!-- chainlink:1 -->       |
|    - Update @trace markers in code/tests                               |
|    - Update CLAUDE.md task tracker instructions                        |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Step 5: Update Configuration                                          |
|                                                                        |
|    - Set task_tracker: chainlink in dp-config.yaml                     |
|    - Optionally archive .beads/ directory                              |
+------------------------------------------------------------------------+
```

### 4.2 Chainlink → Beads Migration

```bash
/dp:migrate chainlink-to-beads [--dry-run]
```

**Data Loss Warnings:**

| Feature | Behavior |
|---------|----------|
| Sessions | **Lost** — Beads doesn't support sessions |
| Time tracking | **Lost** — Beads doesn't track time |
| Milestones | **Flattened** — Converted to labels |
| Related issues | **Converted** — Become comments |
| Issue IDs | **Regenerated** — New hash-based IDs |

The migration script will display warnings before proceeding and require explicit confirmation.

---

## 5. Spec-Issue Bidirectional Linking

### 5.1 Spec Format

```markdown
# Feature: User Authentication
[SPEC-01] <!-- chainlink:12 -->

## Requirements

[SPEC-01.01] User can log in with email/password <!-- chainlink:13 -->

The system shall authenticate users via email and password combination.
Password requirements: minimum 8 characters, one uppercase, one number.

[SPEC-01.02] User can reset password via email <!-- chainlink:14 -->

The system shall send a password reset link valid for 24 hours.

[SPEC-01.03] Session expires after 30 minutes of inactivity <!-- chainlink:15 -->

## Non-Functional Requirements

[SPEC-01.10] Authentication latency < 500ms <!-- chainlink:16 -->
```

### 5.2 Issue Format

When creating issues, reference specs in description:

```bash
chainlink create "Implement login endpoint" \
  -d "Implements [SPEC-01.01]. Must validate email format and password requirements." \
  -p high \
  -l backend,auth
```

### 5.3 Code Traceability

```python
# @trace SPEC-01.01
def authenticate_user(email: str, password: str) -> User:
    """
    Authenticate user with email and password.
    
    Implements SPEC-01.01: User can log in with email/password
    """
    # @trace SPEC-01.01.a - Email validation
    if not validate_email(email):
        raise InvalidEmailError()
    
    # @trace SPEC-01.01.b - Password validation
    if not validate_password(password):
        raise InvalidPasswordError()
    
    return user_service.authenticate(email, password)
```

### 5.4 Traceability Report

```bash
/dp:trace coverage
```

**Output:**

```
Spec Coverage Report
========================================================================

Section: Authentication (SPEC-01)
------------------------------------------------------------------------
SPEC-01.01  [x] chainlink:13 (closed)   tests: 5/5 passing   code: auth.py:42
SPEC-01.02  [!] chainlink:14 (open)     tests: 0 written     code: -
SPEC-01.03  [x] chainlink:15 (closed)   tests: 3/3 passing   code: session.py:18
SPEC-01.10  [ ] No linked issue         tests: -             code: -

Summary: 2/4 specs fully covered, 1 in progress, 1 not started
========================================================================
```

### 5.5 Enforcement via Hooks

The `UserPromptSubmit` hook validates spec references based on enforcement level:

| Enforcement | New Issue Without Spec | Code Without @trace |
|-------------|------------------------|---------------------|
| `strict` | **Block** — Must reference spec | **Block** — Must have trace marker |
| `guided` | **Warn** — Suggest adding spec reference | **Warn** — Suggest adding trace |
| `minimal` | Allow | Allow |

---

## 6. Adversarial Validation System

### 6.1 Integration with rlm-claude-code

Rather than building separate adversarial infrastructure, this system plugs into rlm-claude-code's existing model routing capabilities.

### 6.2 Adversary Agent Definition

**Location:** `agents/adversary.md`

```markdown
---
name: adversary
description: Hyper-critical code reviewer for VDD workflow
model: gemini-2.5-flash
fresh_context: true
tools: Read, Grep, Glob
---

# Sarcasmotron: Adversarial Code Reviewer

You are Sarcasmotron, a hyper-critical code reviewer with zero tolerance for:

## What You Hunt For

1. **Placeholder Code**
   - TODO comments that should be implementation
   - Stub functions with `pass` or `NotImplementedError`
   - "Fix later" comments
   - Hardcoded test values in production code

2. **Generic Error Handling**
   - Bare `except:` clauses
   - `catch (Exception e)` without specific handling
   - Swallowed errors with no logging
   - Error messages that don't help debugging

3. **Logic Gaps**
   - Missing edge cases (null, empty, negative)
   - Off-by-one errors
   - Race conditions in concurrent code
   - Unchecked return values

4. **Security Issues**
   - SQL injection vectors
   - Unsanitized user input
   - Hardcoded credentials
   - Missing authentication checks

5. **Convention Violations**
   - Inconsistent naming
   - Missing type hints (Python)
   - Unused imports/variables
   - Functions doing too many things

## How You Critique

- Be harsh but accurate
- Reference specific line numbers
- Explain WHY something is wrong
- Suggest concrete fixes

## Critical Constraint

If you cannot find legitimate issues, say exactly:
"No issues found."

Do NOT invent problems. You will be called out for hallucinating.
Fabricated critiques waste everyone's time and undermine trust.

---

## Context to Review

$CONTEXT
```

### 6.3 Workflow

```bash
/dp:review adversarial
```

**Process Flow:**

```
+------------------------------------------------------------------------+
|  Step 1: Gather Context                                                |
|                                                                        |
|    - Current diff: git diff HEAD                                       |
|    - Relevant specs: specs linked to modified files                    |
|    - Test coverage: tests for modified code                            |
|    - Previous critiques: to avoid repetition                           |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Step 2: Invoke Adversary via rlm-claude-code                          |
|                                                                        |
|    # Internally executes:                                              |
|    claude --agent adversary --fresh-context "$CONTEXT"                 |
|                                                                        |
|    Key properties:                                                     |
|      - fresh_context: true  (No conversation history)                  |
|      - model: gemini-2.5-flash  (Different model family)               |
|      - Isolated from builder's context                                 |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
|  Step 3: Present Critique to Human                                     |
|                                                                        |
|    ================================================================    |
|    Adversary Critique (Iteration 1)                                    |
|    ================================================================    |
|                                                                        |
|    1. [LOGIC] auth.py:45                                               |
|       Function validate_user returns early on line 45 without          |
|       checking the is_active flag, allowing deactivated users          |
|       through authentication.                                          |
|                                                                        |
|    2. [EDGE CASE] auth.py:52                                           |
|       No handling for empty email string - will cause IndexError       |
|       in email.split('@') on line 52.                                  |
|                                                                        |
|    3. [SECURITY] auth.py:78                                            |
|       Password comparison uses == instead of constant-time             |
|       comparison, vulnerable to timing attacks.                        |
|                                                                        |
|    ----------------------------------------------------------------    |
|    Options:                                                            |
|    [A]ccept all and address                                            |
|    [P]artially accept (select which)                                   |
|    [R]eject as hallucinated                                            |
|    [D]one (code is complete)                                           |
|    ----------------------------------------------------------------    |
+------------------------------------------------------------------------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
              v                   v                   v
        [A] Accept          [R] Reject          [D] Done
              |                   |                   |
              v                   v                   v
     Builder addresses     Log as hallucinated   Exit loop
     issues, then          Continue to next      Code complete
     loop repeats          iteration
```

### 6.4 Hallucination Detection

The system flags suspicious critiques when:

- Line numbers referenced don't exist in the file
- Function/variable names aren't present in the code
- File paths don't match modified files
- Critique contradicts visible code structure

**Example hallucination flag:**

```
[!]  POTENTIAL HALLUCINATION DETECTED
    Critique #3 references `password_hash` on line 78,
    but line 78 contains: `return user.is_authenticated`
    
    The function `compare_password` doesn't exist in auth.py.
    
    Consider rejecting this critique.
```

### 6.5 Convergence Criteria

The loop terminates when:

1. **Adversary returns "No issues found"** — Code is considered complete
2. **Human selects "Done"** — Manual termination
3. **Max iterations reached** — Configurable limit (default: 5)
4. **All critiques rejected as hallucinated** — Adversary has lost grounding

---

## 7. Hooks Architecture

### 7.1 Directory Structure

```
.claude/
|-- settings.json              # Hook configuration
|-- settings.local.json        # Local overrides (gitignored)
|-- hooks/
|   |-- session_start.py       # UV script for SessionStart
|   |-- prompt_guard.py        # UV script for UserPromptSubmit
|   |-- pre_edit.py            # UV script for PreToolUse
|   |-- post_edit.py           # UV script for PostToolUse
|   +-- stop_handler.py        # UV script for Stop
|-- rules/
|   |-- global.md              # No stubs, error handling, security
|   |-- project.md             # Project-specific conventions
|   |-- python.md              # Python best practices
|   |-- typescript.md          # TypeScript best practices
|   +-- ...                    # Other language-specific rules
+-- dp-config.yaml             # Plugin configuration
```

### 7.2 settings.json Configuration

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session_start.py",
            "timeout": 10
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prompt_guard.py",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre_edit.py",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post_edit.py",
            "timeout": 30
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/stop_handler.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### 7.3 Hook Responsibilities

| Hook | Event | Responsibilities |
|------|-------|------------------|
| `session_start.py` | `SessionStart` | Load Chainlink session, display handoff notes, inject context |
| `prompt_guard.py` | `UserPromptSubmit` | Validate spec references, inject rules, log for audit |
| `pre_edit.py` | `PreToolUse` | Block protected files, enforce spec-first (strict mode) |
| `post_edit.py` | `PostToolUse` | Run formatters, update traceability, validate @trace |
| `stop_handler.py` | `Stop` | Prompt for handoff notes, sync issue tracker |

### 7.4 Hook Output Schema

Hooks communicate via JSON output to stdout:

```json
{
  "continue": true,
  "suppressOutput": false,
  "decision": "allow",
  "reason": "File modification permitted",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "Spec SPEC-01.03 linked to this file"
  }
}
```

**Exit Codes:**

| Code | Meaning |
|------|---------|
| 0 | Success, continue |
| 1 | Error, show stderr to user |
| 2 | Block operation, feed stderr to Claude |

---

## 8. Integration with rlm-claude-code

### 8.1 Coordination Points

1. **Model routing for adversarial review**
   - rlm-claude-code's model router handles Gemini API calls
   - Fresh context per adversary invocation (no conversation history)
   - Configurable model in `dp-config.yaml`

2. **Context provider compatibility**
   - Chainlink's `context-provider.py` output consumed by rlm's context manager
   - Both systems respect `.claude/rules/` directory
   - No duplication of context injection logic

3. **Slash commands namespace**
   - `/dp:*` — disciplined-process commands
   - `/rlm *` — rlm-claude-code commands
   - No conflicts between namespaces

4. **Hooks coexistence**
   - rlm-claude-code registers hooks in `~/.claude/settings.json` (user level)
   - disciplined-process registers hooks in `.claude/settings.json` (project level)
   - Both run; project hooks take precedence on conflict

### 8.2 API Key Management

Gemini API keys for adversarial review should be managed through rlm-claude-code's centralized configuration:

```bash
# ~/.claude/.env (managed by rlm-claude-code)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...  # For Gemini adversary
```

---

## 9. Initialization Wizard

### 9.1 Wizard Flow

```bash
/dp:init
```

**Output:**

```
+==========================================================================+
|                   Disciplined Process Plugin Setup                       |
+==========================================================================+

1. Task Tracker
   -------------
   Which issue tracker would you like to use?
   
   [C] Chainlink (recommended)
       • SQLite-based, rich features
       • Session management for AI context
       • Milestones, time tracking
   
   [B] Beads
       • Git-backed, distributed
       • Multi-machine sync via git
       • Lightweight
   
   Selection: C

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

3. Enforcement Level
   ------------------
   How strictly should the workflow be enforced?
   
   [S] Strict — Blocks commits that violate process
   [G] Guided — Warns but allows override
   [M] Minimal — No enforcement, just tooling
   
   Selection: G

4. Adversarial Review
   -------------------
   Enable VDD-style adversarial code review?
   
   [E] Enabled — Reviews with Gemini before completion
   [D] Disabled
   
   Selection: E
   
   Adversary model [gemini-2.5-flash]: ↵

5. Language Detection
   -------------------
   Detected languages: Python, TypeScript
   
   Installing language-specific rules...
   [x] .claude/rules/python.md
   [x] .claude/rules/typescript.md

+==========================================================================+
|                          Setup Complete!                                 |
+==========================================================================+

Next steps:
  chainlink session start          # Begin a work session
  chainlink ready                  # See available tasks
  /dp:spec create auth "User Authentication"  # Create first spec
  
Configuration saved to: .claude/dp-config.yaml
```

---

## 10. Command Reference

### 10.1 Spec Management

| Command | Description |
|---------|-------------|
| `/dp:spec create <section> "<title>"` | Create new spec section |
| `/dp:spec add <id> "<requirement>"` | Add requirement to existing spec |
| `/dp:spec link <spec-id> <issue-id>` | Link spec to Chainlink issue |
| `/dp:spec unlink <spec-id>` | Remove issue link from spec |
| `/dp:spec show <id>` | Display spec with linked issues |
| `/dp:spec coverage` | Show spec-to-issue-to-test coverage report |

### 10.2 ADR Management

| Command | Description |
|---------|-------------|
| `/dp:adr create "<title>"` | Create new Architecture Decision Record |
| `/dp:adr list` | List all ADRs with status |
| `/dp:adr show <id>` | Display ADR content |
| `/dp:adr supersede <id> "<new-title>"` | Supersede an ADR with new decision |
| `/dp:adr deprecate <id> "<reason>"` | Mark ADR as deprecated |

### 10.3 Review Commands

| Command | Description |
|---------|-------------|
| `/dp:review` | Quick checklist review (lightweight) |
| `/dp:review adversarial` | Full VDD adversarial validation loop |
| `/dp:review adversarial --model <model>` | Override adversary model |
| `/dp:review adversarial --max-iterations <n>` | Set iteration limit |

### 10.4 Migration Commands

| Command | Description |
|---------|-------------|
| `/dp:migrate beads-to-chainlink` | Migrate from Beads to Chainlink |
| `/dp:migrate chainlink-to-beads` | Migrate from Chainlink to Beads |
| `/dp:migrate --dry-run` | Preview migration without changes |
| `/dp:migrate status` | Show migration history |

### 10.5 Task Commands (Chainlink Backend)

| Command | Description |
|---------|-------------|
| `/dp:task ready` | Show ready work (no blockers) |
| `/dp:task create "<title>"` | Create new issue |
| `/dp:task show <id>` | Show issue details |
| `/dp:task update <id> --status <status>` | Update issue status |
| `/dp:task close <id>` | Close issue |
| `/dp:task tree` | Show issue hierarchy |
| `/dp:task next` | Recommend next issue to work on |

### 10.6 Session Commands (Chainlink Only)

| Command | Description |
|---------|-------------|
| `/dp:session start` | Start work session, show handoff notes |
| `/dp:session work <id>` | Set current working issue |
| `/dp:session status` | Show current session info |
| `/dp:session end --notes "..."` | End session with handoff notes |

### 10.7 Traceability Commands

| Command | Description |
|---------|-------------|
| `/dp:trace coverage` | Full traceability report |
| `/dp:trace orphans` | Find code without @trace markers |
| `/dp:trace validate` | Validate all trace markers reference valid specs |

### 10.8 Diagnostic Commands

| Command | Description |
|---------|-------------|
| `/dp:health` | Comprehensive health check of all components |
| `/dp:health --quick` | Fast startup health check (critical issues only) |
| `/dp:status` | Current degradation level and disabled features |
| `/dp:logs` | View recent error logs |
| `/dp:logs --tail 50` | View last 50 log entries |

### 10.9 Recovery Commands

| Command | Description |
|---------|-------------|
| `/dp:repair` | Interactive repair wizard |
| `/dp:repair --all` | Run all repair operations |
| `/dp:repair --config` | Regenerate configuration from defaults |
| `/dp:repair --hooks` | Regenerate missing hook scripts |
| `/dp:repair --database` | Run database integrity check and repair |
| `/dp:repair --specs` | Fix orphan references in specs |
| `/dp:repair --dry-run` | Show what would be repaired |
| `/dp:reset --soft` | Reset config to defaults, preserve data |
| `/dp:reset --hard` | Full reset (requires confirmation) |
| `/dp:unlock --force` | Force release database locks |

---

## 11. File Structure

### 11.1 Final Project Structure

```
project/
|-- .claude/
|   |-- settings.json              # Hook configuration
|   |-- settings.local.json        # Local overrides (gitignored)
|   |-- dp-config.yaml             # Plugin configuration
|   |-- dp-migration-map.json      # Migration audit trail
|   |-- dp-migration-in-progress   # Migration lock file (transient)
|   |-- dp-migration-checkpoint.json  # Migration resume point (transient)
|   |-- hooks/
|   |   |-- session_start.py
|   |   |-- prompt_guard.py
|   |   |-- pre_edit.py
|   |   |-- post_edit.py
|   |   +-- stop_handler.py
|   |-- logs/                      # Error and debug logs
|   |   |-- hook-errors.log        # Hook execution errors
|   |   |-- migration.log          # Migration operation log
|   |   +-- adversary.log          # Adversarial review sessions
|   |-- backups/                   # Automatic backups
|   |   |-- issues.db.backup       # Last known good database
|   |   +-- dp-config.yaml.backup  # Config before last change
|   |-- outputs/                   # Generated reports
|   |   +-- issues-*.md            # Large issue lists
|   |-- rules/
|   |   |-- global.md              # Universal rules
|   |   |-- project.md             # Project-specific
|   |   +-- <language>.md          # Language-specific
|   |-- commands/
|   |   +-- dp.md                  # Slash command definitions
|   |-- agents/
|   |   +-- adversary.md           # Adversarial reviewer agent
|   |-- templates/
|   |   |-- adr.md                 # ADR template
|   |   |-- spec.md                # Spec template
|   |   +-- hook.py                # Hook script template
|   +-- adversary-prompt.md        # Customizable adversary prompt
|-- .chainlink/
|   |-- issues.db                  # Chainlink SQLite database
|   |-- issues.db.backup           # Auto-backup before migrations
|   |-- pre-migration-backup/      # Full backup before tracker switch
|   +-- rules/                     # Symlink → .claude/rules/
|-- specs/
|   |-- 01-authentication.md
|   |-- 02-authorization.md
|   +-- ...
|-- adrs/
|   |-- 001-use-chainlink.md
|   |-- 002-adversarial-review.md
|   +-- ...
|-- CLAUDE.md                      # Project instructions
+-- ...
```

### 11.2 Gitignore Recommendations

```gitignore
# .gitignore additions for disciplined-process

# Local settings (user-specific)
.claude/settings.local.json

# Logs (can be large, user-specific errors)
.claude/logs/

# Transient migration files
.claude/dp-migration-in-progress
.claude/dp-migration-checkpoint.json

# Generated outputs (can be regenerated)
.claude/outputs/

# Backups (local safety net)
.claude/backups/

# Chainlink local database
.chainlink/issues.db
.chainlink/issues.db-*
.chainlink/issues.db.backup
.chainlink/pre-migration-backup/

# Chainlink daemon files
.chainlink/bd.sock
.chainlink/bd.pipe
.chainlink/.exclusive-lock

# Migration artifacts (optional - may want to keep for audit)
# .claude/dp-migration-map.json
```

---

## 12. Implementation Notes

### 12.1 Prerequisites

1. **Chainlink CLI** — Users install separately: `cargo install chainlink`
2. **Beads CLI** — If using Beads: follow Beads installation instructions
3. **rlm-claude-code** — Plugin system handles installation
4. **UV** — For Python hook isolation: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 12.2 Rules Sync Strategy

**Recommendation:** Symlink `.chainlink/rules/` to `.claude/rules/` for single source of truth.

```bash
# During /dp:init when Chainlink is selected:
mkdir -p .chainlink
ln -s ../.claude/rules .chainlink/rules
```

This ensures:
- Both systems read the same rules
- Updates to rules apply everywhere
- No duplication or drift

### 12.3 rlm-claude-code Version Requirements

This specification assumes rlm-claude-code supports:

- Custom agents with `fresh_context: true` property
- Model routing to Gemini
- Agent invocation via `claude --agent <name>`

**Verify these features are implemented before proceeding.**

### 12.4 Testing Strategy

1. **Unit tests** — Each hook script independently
2. **Integration tests** — Full workflow from session start to review
3. **Migration tests** — Round-trip Beads ↔ Chainlink
4. **Adversarial tests** — Verify hallucination detection

### 12.5 Rollout Plan

1. **Phase 1:** Core infrastructure (hooks, configuration)
2. **Phase 2:** Chainlink integration and migration
3. **Phase 3:** Adversarial review system
4. **Phase 4:** Documentation and examples

---

## 13. Failure Modes and Graceful Degradation

This section defines expected failure scenarios, detection mechanisms, user messaging standards, and graceful degradation strategies. The guiding principle is: **never lose user data, always provide actionable guidance, and degrade to simpler functionality rather than failing completely.**

### 13.1 Design Philosophy

```
+-------------------------------------------------------------------------+
|                    Graceful Degradation Hierarchy                       |
|-------------------------------------------------------------------------|
|                                                                         |
|   Level 0: Full Functionality                                           |
|   ==========================                                            |
|   All systems operational, all features available                       |
|                                                                         |
|            | Component failure detected                                 |
|            v                                                            |
|   Level 1: Reduced Functionality                                        |
|   ============================                                          |
|   Core workflow continues, advanced features disabled                   |
|   Example: Adversarial review unavailable, but spec tracking works      |
|                                                                         |
|            | Issue tracker unavailable                                  |
|            v                                                            |
|   Level 2: Manual Mode                                                  |
|   ===================                                                   |
|   Plugin provides guidance, user executes manually                      |
|   Example: "Run 'chainlink ready' to see available tasks"               |
|                                                                         |
|            | Configuration corrupted                                    |
|            v                                                            |
|   Level 3: Safe Mode                                                    |
|   ================                                                      |
|   Minimal hooks, no enforcement, preserve data                          |
|   Example: Hooks disabled, but files protected from deletion            |
|                                                                         |
|            | Unrecoverable state                                        |
|            v                                                            |
|   Level 4: Recovery Mode                                                |
|   ======================                                                |
|   Guide user through repair/reinstallation                              |
|   Example: "Run '/dp:repair' to diagnose and fix issues"                |
|                                                                         |
+-------------------------------------------------------------------------+
```

### 13.2 Dependency Failures

#### 13.2.1 Issue Tracker Binary Not Installed

| Aspect | Chainlink Missing | Beads Missing |
|--------|-------------------|---------------|
| **Detection** | `which chainlink` returns empty | `which bd` returns empty |
| **When Checked** | `/dp:init`, `SessionStart` hook, any `/dp:task` command | Same |
| **User Message** | See below | See below |
| **Degradation** | Level 2: Manual guidance mode | Level 2: Manual guidance mode |
| **Recovery** | Provide installation command | Provide installation command |

**Chainlink Missing Message:**
```
+==========================================================================+
|  [!]  Chainlink CLI Not Found                                             |
+==========================================================================+
|                                                                          |
|  The Chainlink issue tracker is configured but not installed.            |
|                                                                          |
|  To install:                                                             |
|    cargo install chainlink                                               |
|                                                                          |
|  Or switch to Beads (if installed):                                      |
|    Edit .claude/dp-config.yaml: task_tracker: beads                      |
|                                                                          |
|  Current mode: MANUAL GUIDANCE                                           |
|  Task tracking commands will show instructions but not execute.          |
|                                                                          |
+==========================================================================+
```

#### 13.2.2 UV/Python Not Available

| Aspect | Details |
|--------|---------|
| **Detection** | `which uv` returns empty, or `python3 --version` fails |
| **When Checked** | Any hook execution |
| **User Message** | "Python hooks require UV. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh`" |
| **Degradation** | Level 1: Hooks disabled, core commands work |
| **Recovery** | Install UV, restart Claude Code |

**Fallback Behavior:**
```python
# In each hook script, wrap execution:
try:
    # Normal hook logic
except Exception as e:
    # Log error but don't block Claude Code
    print(json.dumps({
        "continue": True,
        "suppressOutput": False,
        "reason": f"Hook degraded: {e}. Continuing without enforcement."
    }))
    sys.exit(0)  # Don't block on hook failure
```

#### 13.2.3 rlm-claude-code Not Installed

| Aspect | Details |
|--------|---------|
| **Detection** | Agent invocation fails, `claude --agent` not recognized |
| **When Checked** | `/dp:review adversarial` |
| **User Message** | See below |
| **Degradation** | Level 1: Adversarial review disabled, manual review available |
| **Recovery** | Install rlm-claude-code plugin |

**Message:**
```
+==========================================================================+
|  [!]  Adversarial Review Unavailable                                      |
+==========================================================================+
|                                                                          |
|  rlm-claude-code is required for adversarial validation but not found.   |
|                                                                          |
|  Options:                                                                |
|  1. Install rlm-claude-code: /plugin install rlm-claude-code             |
|  2. Use manual review: /dp:review (checklist mode)                       |
|  3. Disable in config: adversarial_review.enabled: false                 |
|                                                                          |
|  Falling back to manual review mode.                                     |
|                                                                          |
+==========================================================================+
```

#### 13.2.4 Version Mismatches

| Component | Detection | Impact | Degradation |
|-----------|-----------|--------|-------------|
| Chainlink CLI vs DB schema | `chainlink info --json` returns version mismatch | Commands may fail unpredictably | Prompt migration: `chainlink migrate` |
| Beads CLI vs JSONL format | `bd info --schema --json` | Import/export may corrupt | Prompt: `bd migrate` |
| Claude Code hooks API | Hook receives unexpected input schema | Hook crashes | Catch-all error handler, continue |
| rlm-claude-code agents | Agent YAML has unsupported fields | Agent won't load | Fall back to built-in review |

**Version Check at Startup:**
```python
# session_start.py
def check_versions():
    issues = []
    
    # Check Chainlink
    result = subprocess.run(['chainlink', 'info', '--json'], capture_output=True)
    if result.returncode == 0:
        info = json.loads(result.stdout)
        if info.get('schema_version', 0) < REQUIRED_SCHEMA_VERSION:
            issues.append({
                'component': 'chainlink',
                'issue': 'schema_outdated',
                'fix': 'Run: chainlink migrate'
            })
    
    # Check rlm-claude-code
    if not Path('.claude/agents/adversary.md').exists():
        issues.append({
            'component': 'adversary',
            'issue': 'agent_missing',
            'fix': 'Run: /dp:init --repair-agents'
        })
    
    return issues
```

### 13.3 Data Corruption Scenarios

#### 13.3.1 Chainlink Database Corruption

| Aspect | Details |
|--------|---------|
| **Detection** | SQLite integrity check fails, queries return errors |
| **Symptoms** | "database disk image is malformed", missing tables |
| **User Message** | See below |
| **Degradation** | Level 3: Safe mode, no issue tracking |
| **Recovery** | Restore from backup or reinitialize |

**Detection Code:**
```python
def check_database_integrity():
    try:
        conn = sqlite3.connect('.chainlink/issues.db')
        result = conn.execute('PRAGMA integrity_check').fetchone()
        if result[0] != 'ok':
            return {'status': 'corrupted', 'details': result[0]}
        return {'status': 'ok'}
    except sqlite3.DatabaseError as e:
        return {'status': 'error', 'details': str(e)}
```

**Corruption Message:**
```
+==========================================================================+
|  [E] DATABASE CORRUPTION DETECTED                                         |
+==========================================================================+
|                                                                          |
|  The Chainlink database appears to be corrupted.                         |
|  Error: database disk image is malformed                                 |
|                                                                          |
|  Your data may be recoverable. Do NOT delete any files.                  |
|                                                                          |
|  Recovery options:                                                       |
|                                                                          |
|  1. AUTOMATIC REPAIR (recommended):                                      |
|     /dp:repair --database                                                |
|     Attempts to recover data and rebuild indexes.                        |
|                                                                          |
|  2. RESTORE FROM BACKUP:                                                 |
|     cp .chainlink/issues.db.backup .chainlink/issues.db                  |
|     (if backup exists from last successful session)                      |
|                                                                          |
|  3. EXPORT WHAT'S READABLE:                                              |
|     /dp:repair --export-salvageable                                      |
|     Saves recoverable issues to chainlink-recovery.json                  |
|                                                                          |
|  4. REINITIALIZE (data loss):                                            |
|     rm .chainlink/issues.db && chainlink init                            |
|                                                                          |
|  Current mode: SAFE MODE - Issue tracking disabled                       |
|                                                                          |
+==========================================================================+
```

#### 13.3.2 Beads JSONL Corruption

| Aspect | Details |
|--------|---------|
| **Detection** | JSON parse error on any line, invalid UTF-8 |
| **Symptoms** | `bd list` fails, import errors |
| **User Message** | Line number and content of corruption |
| **Degradation** | Level 2: SQLite cache may still work |
| **Recovery** | `bd import --repair` or manual JSONL editing |

**Recovery Strategy:**
```python
def repair_jsonl(path):
    """Attempt to repair corrupted JSONL by skipping bad lines."""
    good_lines = []
    bad_lines = []
    
    with open(path, 'r', errors='replace') as f:
        for i, line in enumerate(f, 1):
            try:
                json.loads(line)
                good_lines.append(line)
            except json.JSONDecodeError as e:
                bad_lines.append({'line': i, 'content': line[:100], 'error': str(e)})
    
    if bad_lines:
        # Write recovery report
        with open(f'{path}.recovery-report.json', 'w') as f:
            json.dump({'bad_lines': bad_lines, 'recovered': len(good_lines)}, f)
        
        # Write repaired file
        with open(f'{path}.repaired', 'w') as f:
            f.writelines(good_lines)
    
    return {'good': len(good_lines), 'bad': len(bad_lines)}
```

#### 13.3.3 Configuration File Corruption

| File | Detection | Degradation | Recovery |
|------|-----------|-------------|----------|
| `dp-config.yaml` | YAML parse error | Use defaults | `/dp:init --repair-config` |
| `settings.json` | JSON parse error | Disable hooks | Manual edit or delete |
| `adversary.md` | Missing frontmatter | Disable adversarial | Regenerate from template |
| Spec files | Invalid spec ID format | Skip file in reports | Manual correction |

**Config Validation with Defaults:**
```python
def load_config_with_fallback():
    defaults = {
        'task_tracker': 'chainlink',
        'enforcement': 'guided',
        'adversarial_review': {'enabled': False},
    }
    
    try:
        with open('.claude/dp-config.yaml') as f:
            config = yaml.safe_load(f)
            return {**defaults, **config}
    except FileNotFoundError:
        log_warning("Config not found, using defaults")
        return defaults
    except yaml.YAMLError as e:
        log_error(f"Config corrupted: {e}")
        notify_user(
            "[!] Configuration Error",
            f"dp-config.yaml is invalid: {e}\n"
            "Using default settings. Run /dp:repair --config to fix."
        )
        return defaults
```

#### 13.3.4 Migration Mapping Loss

| Aspect | Details |
|--------|---------|
| **Detection** | `dp-migration-map.json` missing after migration |
| **Impact** | Can't trace old Beads IDs to new Chainlink IDs |
| **Degradation** | Traceability reports show warnings |
| **Recovery** | Re-run migration with `--rebuild-map` |

**Orphan Reference Handling:**
```
When processing spec file: specs/01-authentication.md

[!] ORPHAN REFERENCE DETECTED
   Line 15: <!-- bd-a1b2 --> references Beads ID
   Migration map not found or doesn't contain this ID.

   Options:
   1. Link to existing Chainlink issue: /dp:spec link SPEC-01.03 <chainlink-id>
   2. Create new issue from spec: /dp:spec create-issue SPEC-01.03
   3. Remove stale reference: /dp:spec unlink SPEC-01.03
```

### 13.4 Runtime Failures

#### 13.4.1 Hook Execution Failures

| Failure Type | Detection | User Impact | Handling |
|--------------|-----------|-------------|----------|
| Timeout | Hook exceeds `timeout` setting | Session blocked | Kill process, continue with warning |
| Crash | Non-zero exit code (except 2) | Feature disabled | Log, notify, continue |
| Invalid Output | JSON parse error on stdout | Decision unclear | Default to "continue" |
| Permission Denied | OS error on script execution | Hook won't run | Skip hook, warn user |

**Hook Wrapper with Comprehensive Error Handling:**
```python
#!/usr/bin/env python3
"""
Hook wrapper that ensures graceful degradation.
All hooks should use this pattern.
"""
import sys
import json
import traceback
from pathlib import Path

def safe_hook_main(hook_logic):
    """Wrap hook logic with error handling that never blocks Claude Code."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        # Execute hook logic
        result = hook_logic(input_data)
        
        # Validate and output result
        if result is None:
            result = {"continue": True}
        
        print(json.dumps(result))
        sys.exit(0)
        
    except json.JSONDecodeError as e:
        # Input wasn't valid JSON - likely Claude Code API change
        log_error(f"Hook input parse error: {e}")
        print(json.dumps({
            "continue": True,
            "reason": "Hook received unexpected input format. Continuing without enforcement."
        }))
        sys.exit(0)
        
    except KeyboardInterrupt:
        # Timeout or user interrupt
        print(json.dumps({
            "continue": True,
            "reason": "Hook interrupted. Continuing."
        }))
        sys.exit(0)
        
    except Exception as e:
        # Unexpected error - log but don't block
        log_error(f"Hook crashed: {e}\n{traceback.format_exc()}")
        print(json.dumps({
            "continue": True,
            "reason": f"Hook error: {type(e).__name__}. Continuing without enforcement."
        }))
        sys.exit(0)

def log_error(message):
    """Log to file since stderr may not be visible."""
    log_path = Path('.claude/logs/hook-errors.log')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'a') as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")
```

#### 13.4.2 Adversarial Review Failures

| Failure | Detection | User Message | Degradation |
|---------|-----------|--------------|-------------|
| API key missing | `GOOGLE_API_KEY` not set | "Gemini API key not configured" | Offer manual review |
| API rate limited | 429 response | "Rate limited, retry in X seconds" | Queue and retry, or skip |
| API error | 5xx response | "Gemini service error" | Retry 3x, then skip |
| Network timeout | Connection timeout | "Network error" | Retry with backoff |
| Model not found | 404 on model | "Model gemini-2.5-flash not available" | Fall back to claude-sonnet |
| Context too large | Token limit exceeded | "Code diff too large for review" | Chunk and review incrementally |
| Infinite loop | Iteration count > max | "Max iterations reached" | Force exit with summary |

**Adversarial Review with Retry Logic:**
```python
class AdversarialReviewer:
    def __init__(self, config):
        self.max_retries = 3
        self.retry_delay = [1, 5, 15]  # Exponential backoff
        self.max_iterations = config.get('max_iterations', 5)
        self.fallback_models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'claude-sonnet']
    
    def invoke_adversary(self, context):
        last_error = None
        
        for model in self.fallback_models:
            for attempt in range(self.max_retries):
                try:
                    return self._call_model(model, context)
                except RateLimitError:
                    delay = self.retry_delay[min(attempt, len(self.retry_delay)-1)]
                    self.notify_user(f"Rate limited. Retrying in {delay}s...")
                    time.sleep(delay)
                except NetworkError as e:
                    last_error = e
                    continue
                except ModelNotFoundError:
                    self.notify_user(f"Model {model} not available, trying next...")
                    break  # Try next model
            
        # All models failed
        return self._fallback_to_manual(last_error)
    
    def _fallback_to_manual(self, error):
        self.notify_user(f"""
+==========================================================================+
|  [!]  Adversarial Review Unavailable                                      |
+==========================================================================+
|                                                                          |
|  Could not connect to any review model.                                  |
|  Last error: {str(error)[:50]}
|                                                                          |
|  Falling back to manual review checklist.                                |
|  You can retry later with: /dp:review adversarial --retry                |
|                                                                          |
+==========================================================================+
        """)
        return self._manual_review_checklist()
```

#### 13.4.3 Issue Tracker Command Failures

| Command | Failure Mode | Detection | Graceful Response |
|---------|--------------|-----------|-------------------|
| `chainlink ready` | DB locked | Exit code + "database is locked" | Retry after 1s, then show cached |
| `chainlink create` | Validation error | Exit code + stderr | Show error, suggest fix |
| `chainlink update` | Issue not found | "Issue X not found" | Suggest `/dp:task list` |
| `bd ready` | Daemon not running | "daemon not responding" | Start daemon, retry |
| `bd sync` | Git conflict | "CONFLICT in .beads/" | Show conflict resolution guide |

**Command Execution Wrapper:**
```python
def execute_tracker_command(cmd, args, retries=2):
    """Execute tracker command with retry and helpful error messages."""
    
    for attempt in range(retries + 1):
        result = subprocess.run(
            [cmd] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {'success': True, 'output': result.stdout}
        
        error = result.stderr.lower()
        
        # Retryable errors
        if 'database is locked' in error and attempt < retries:
            time.sleep(1)
            continue
        
        if 'daemon not responding' in error:
            subprocess.run([cmd, 'daemon', 'start'])
            continue
        
        # Non-retryable errors with helpful messages
        if 'not found' in error:
            return {
                'success': False,
                'error': result.stderr,
                'suggestion': f"Issue may have been deleted. Run '{cmd} list' to see available issues."
            }
        
        if 'CONFLICT' in error:
            return {
                'success': False,
                'error': result.stderr,
                'suggestion': "Git conflict detected. See /dp:help resolve-conflicts"
            }
        
        return {'success': False, 'error': result.stderr}
    
    return {'success': False, 'error': 'Max retries exceeded'}
```

### 13.5 Migration Failures

#### 13.5.1 Interrupted Migration

| Aspect | Details |
|--------|---------|
| **Risk** | Data partially migrated, references inconsistent |
| **Detection** | `.claude/dp-migration-in-progress` marker file exists |
| **Prevention** | Atomic operations, write to temp then rename |
| **Recovery** | Resume from checkpoint or rollback |

**Migration Transaction Pattern:**
```python
class MigrationTransaction:
    def __init__(self, source, target):
        self.marker = Path('.claude/dp-migration-in-progress')
        self.checkpoint = Path('.claude/dp-migration-checkpoint.json')
        self.source = source
        self.target = target
    
    def __enter__(self):
        if self.marker.exists():
            raise MigrationInProgressError(
                "A previous migration was interrupted.\n"
                "Run '/dp:migrate --resume' to continue or '/dp:migrate --rollback' to abort."
            )
        
        self.marker.write_text(json.dumps({
            'started': datetime.now().isoformat(),
            'source': self.source,
            'target': self.target
        }))
        return self
    
    def checkpoint(self, state):
        """Save progress for resume capability."""
        self.checkpoint.write_text(json.dumps(state))
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success - clean up markers
            self.marker.unlink(missing_ok=True)
            self.checkpoint.unlink(missing_ok=True)
        else:
            # Failure - leave markers for recovery
            pass
        return False
```

#### 13.5.2 Data Loss During Migration

| Data Type | Risk | Mitigation |
|-----------|------|------------|
| Session history | Beads→Chainlink loses sessions | Warn user, sessions don't exist in Beads |
| Time tracking | Chainlink→Beads loses time data | Warn user, export to CSV first |
| Milestones | Chainlink→Beads converts to labels | Warn, document mapping |
| Related issues | May become orphaned | Preserve as comments |
| Custom fields | Target may not support | Export to JSON sidecar |

**Pre-Migration Warning:**
```
+==========================================================================+
|  Migration: Chainlink → Beads                                            |
+==========================================================================+
|                                                                          |
|  [!]  DATA TRANSFORMATION WARNING                                         |
|                                                                          |
|  The following data will be transformed or lost:                         |
|                                                                          |
|  +--------------------┬---------------------------------------------+   |
|  | Feature            | Behavior                                    |   |
|  |--------------------┼---------------------------------------------|   |
|  | Sessions (3)       | [E] LOST - Beads has no session support      |   |
|  | Time entries (47)  | [E] LOST - Export first with --export-time   |   |
|  | Milestones (2)     | [W] CONVERTED to labels                      |   |
|  | Related issues     | [W] CONVERTED to comments                    |   |
|  | Issues (24)        | [OK] PRESERVED                                |   |
|  | Dependencies (18)  | [OK] PRESERVED                                |   |
|  +--------------------┴---------------------------------------------+   |
|                                                                          |
|  A backup will be created at: .chainlink/pre-migration-backup/           |
|                                                                          |
|  Continue? [y/N]                                                         |
|                                                                          |
+==========================================================================+
```

### 13.6 Concurrency Issues

#### 13.6.1 Multiple Claude Code Sessions

| Scenario | Risk | Detection | Mitigation |
|----------|------|-----------|------------|
| Two sessions same project | DB lock contention | SQLite busy timeout | Retry with backoff |
| Hook running while user edits config | Race condition | File mtime check | Re-read config each invocation |
| Parallel adversarial reviews | Wasted API calls | Lock file | Skip if lock held |
| Git operations during Beads sync | Merge conflicts | Git status check | Defer sync, warn user |

**Database Access Pattern:**
```python
def with_db_retry(func, max_wait=10):
    """Execute database operation with busy retry."""
    start = time.time()
    while True:
        try:
            return func()
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                if time.time() - start > max_wait:
                    raise DatabaseBusyError(
                        "Database locked by another process.\n"
                        "Another Claude Code session may be using this project.\n"
                        "Wait for it to complete or run: /dp:unlock --force"
                    )
                time.sleep(0.5)
            else:
                raise
```

#### 13.6.2 Beads Git Conflicts

**Conflict Resolution Guide:**
```
+==========================================================================+
|  [C] GIT CONFLICT IN BEADS DATA                                           |
+==========================================================================+
|                                                                          |
|  Conflict detected in: .beads/issues.jsonl                               |
|                                                                          |
|  This happens when issues were modified in multiple branches.            |
|                                                                          |
|  Resolution options:                                                     |
|                                                                          |
|  1. AUTOMATIC MERGE (recommended for most cases):                        |
|     bd merge --auto                                                      |
|     Keeps all issues, merges changes, resolves ID conflicts.             |
|                                                                          |
|  2. KEEP LOCAL (discard remote changes):                                 |
|     git checkout --ours .beads/issues.jsonl                              |
|     bd import --force                                                    |
|                                                                          |
|  3. KEEP REMOTE (discard local changes):                                 |
|     git checkout --theirs .beads/issues.jsonl                            |
|     bd import --force                                                    |
|                                                                          |
|  4. MANUAL MERGE:                                                        |
|     Edit .beads/issues.jsonl to resolve conflicts                        |
|     bd import --validate                                                 |
|                                                                          |
|  After resolving:                                                        |
|     git add .beads/issues.jsonl                                          |
|     git commit -m "Resolved beads conflict"                              |
|                                                                          |
+==========================================================================+
```

### 13.7 Network Failures

#### 13.7.1 API Connectivity Issues

| Service | Impact | Detection | Offline Behavior |
|---------|--------|-----------|------------------|
| Gemini API | Adversarial review fails | Connection timeout | Queue for later, offer manual |
| Git remote | Beads sync fails | Push/pull timeout | Work locally, sync later |
| Plugin registry | Can't install plugins | HTTP error | Use local cache or manual install |

**Offline Mode Detection:**
```python
def check_network_status():
    """Quick check if external services are reachable."""
    services = {
        'gemini': ('generativelanguage.googleapis.com', 443),
        'github': ('github.com', 443),
    }
    
    status = {}
    for name, (host, port) in services.items():
        try:
            socket.create_connection((host, port), timeout=2)
            status[name] = 'online'
        except (socket.timeout, socket.error):
            status[name] = 'offline'
    
    return status
```

**Offline Mode Message:**
```
+==========================================================================+
|  [N] LIMITED CONNECTIVITY DETECTED                                        |
+==========================================================================+
|                                                                          |
|  Some services are unreachable:                                          |
|  • Gemini API: offline (adversarial review unavailable)                  |
|  • GitHub: offline (git push/pull will fail)                             |
|                                                                          |
|  The following features are disabled:                                    |
|  • /dp:review adversarial                                                |
|  • Beads auto-sync                                                       |
|                                                                          |
|  Local features remain available:                                        |
|  • Issue tracking (Chainlink)                                            |
|  • Spec management                                                       |
|  • Hook enforcement                                                      |
|                                                                          |
|  Changes will sync when connectivity is restored.                        |
|                                                                          |
+==========================================================================+
```

### 13.8 Resource Exhaustion

#### 13.8.1 Disk Space

| Threshold | Detection | Action |
|-----------|-----------|--------|
| < 1GB free | `shutil.disk_usage()` | Warning message |
| < 100MB free | Check before writes | Block writes, prompt cleanup |
| 0 bytes free | Write fails | Emergency mode, read-only |

**Disk Space Check:**
```python
def check_disk_space(required_mb=100):
    """Check if sufficient disk space is available."""
    usage = shutil.disk_usage('.')
    free_mb = usage.free / (1024 * 1024)
    
    if free_mb < required_mb:
        raise DiskSpaceError(
            f"Insufficient disk space: {free_mb:.0f}MB free, {required_mb}MB required.\n"
            f"Free up space or run: /dp:cleanup --old-logs --old-backups"
        )
```

#### 13.8.2 Context Window Limits

| Scenario | Detection | Mitigation |
|----------|-----------|------------|
| Too many issues to display | Count > 100 | Paginate, show summary |
| Diff too large for review | Token estimate > limit | Chunk by file |
| Spec coverage report huge | Many specs | Generate to file, show link |

**Large Output Handling:**
```python
def format_issue_list(issues, max_inline=20):
    """Format issue list with overflow handling."""
    if len(issues) <= max_inline:
        return format_table(issues)
    
    # Too many for inline display
    summary = f"Found {len(issues)} issues. Showing top {max_inline} by priority:\n\n"
    summary += format_table(issues[:max_inline])
    summary += f"\n\nFull list saved to: .claude/outputs/issues-{timestamp}.md"
    summary += "\nFilter with: /dp:task list --status open --priority 0-1"
    
    # Write full list to file
    write_full_list(issues)
    
    return summary
```

### 13.9 Configuration Errors

#### 13.9.1 Invalid Configuration Values

| Field | Invalid Value | Default | User Message |
|-------|---------------|---------|--------------|
| `task_tracker` | "jira" | "chainlink" | "Unknown tracker 'jira'. Using chainlink." |
| `enforcement` | "extreme" | "guided" | "Unknown level 'extreme'. Using guided." |
| `max_iterations` | -1 | 5 | "max_iterations must be positive. Using 5." |
| `model` | "gpt-9000" | "gemini-2.5-flash" | "Model 'gpt-9000' not available. Using gemini-2.5-flash." |

**Config Validation with Coercion:**
```python
def validate_config(config):
    """Validate config, coercing invalid values to defaults with warnings."""
    warnings = []
    
    # task_tracker
    valid_trackers = ['chainlink', 'beads']
    if config.get('task_tracker') not in valid_trackers:
        warnings.append(f"Unknown task_tracker '{config.get('task_tracker')}'. Using 'chainlink'.")
        config['task_tracker'] = 'chainlink'
    
    # enforcement
    valid_levels = ['strict', 'guided', 'minimal']
    if config.get('enforcement') not in valid_levels:
        warnings.append(f"Unknown enforcement '{config.get('enforcement')}'. Using 'guided'.")
        config['enforcement'] = 'guided'
    
    # max_iterations
    max_iter = config.get('adversarial_review', {}).get('max_iterations', 5)
    if not isinstance(max_iter, int) or max_iter < 1:
        warnings.append(f"Invalid max_iterations '{max_iter}'. Using 5.")
        config.setdefault('adversarial_review', {})['max_iterations'] = 5
    
    return config, warnings
```

#### 13.9.2 Conflicting Settings

| Conflict | Detection | Resolution |
|----------|-----------|------------|
| `enforcement: strict` + `adversarial_review.enabled: false` | Startup validation | Warn: "Strict mode without review may block work" |
| Beads configured but `.beads/` missing | File check | Offer to initialize or switch tracker |
| Hooks reference missing scripts | Path validation | Disable specific hook, warn |

### 13.10 Health Check System

#### 13.10.1 `/dp:health` Command

```
/dp:health
```

**Output:**
```
+==========================================================================+
|                      Disciplined Process Health Check                    |
+==========================================================================+
|                                                                          |
|  Configuration                                                           |
|  -------------                                                           |
|  [x] dp-config.yaml          Valid, loaded successfully                    |
|  [x] settings.json           Valid, 5 hooks configured                     |
|  [!] settings.local.json     Not found (optional)                          |
|                                                                          |
|  Issue Tracker: Chainlink                                                |
|  ------------------------                                                |
|  [x] Binary                  v0.8.2 installed at /usr/local/bin/chainlink  |
|  [x] Database                .chainlink/issues.db (234 KB, 47 issues)      |
|  [x] Integrity               PRAGMA integrity_check passed                 |
|  [x] Schema                  Version 3 (current)                           |
|  [!] Active session          None (start with 'chainlink session start')  |
|                                                                          |
|  Hooks                                                                   |
|  -----                                                                   |
|  [x] session_start.py        Executable, syntax valid                      |
|  [x] prompt_guard.py         Executable, syntax valid                      |
|  [x] pre_edit.py             Executable, syntax valid                      |
|  [x] post_edit.py            Executable, syntax valid                      |
|  [!] stop_handler.py         MISSING - sessions won't save properly        |
|                                                                          |
|  Adversarial Review                                                      |
|  ------------------                                                      |
|  [x] rlm-claude-code         Installed, v1.2.0                             |
|  [x] Adversary agent         .claude/agents/adversary.md present           |
|  [x] GOOGLE_API_KEY          Set (ends in ...4f7a)                         |
|  [x] Gemini API              Reachable, 142ms latency                      |
|                                                                          |
|  Specs & ADRs                                                            |
|  -----------                                                             |
|  [x] specs/                  5 spec files, 23 requirements                 |
|  [x] adrs/                   3 ADRs (2 accepted, 1 superseded)             |
|  [!] Orphan references       2 specs reference deleted issues              |
|                                                                          |
|  Disk Space                                                              |
|  ----------                                                              |
|  [x] Available               42.3 GB free                                  |
|                                                                          |
|  ======================================================================  |
|  Summary: 15 checks passed, 3 warnings, 1 error                          |
|                                                                          |
|  To fix errors:                                                          |
|  • stop_handler.py: Run '/dp:repair --hooks' to regenerate               |
|                                                                          |
|  To address warnings:                                                    |
|  • Active session: Run 'chainlink session start'                         |
|  • Orphan references: Run '/dp:trace validate --fix'                     |
|                                                                          |
+==========================================================================+
```

#### 13.10.2 Startup Health Check

The `SessionStart` hook performs a lightweight health check and reports critical issues:

```python
def quick_health_check():
    """Fast health check for session startup."""
    critical = []
    warnings = []
    
    # Check config exists
    if not Path('.claude/dp-config.yaml').exists():
        critical.append("Config missing - run /dp:init")
        return critical, warnings
    
    # Check tracker
    config = load_config()
    tracker = config.get('task_tracker', 'chainlink')
    
    if tracker == 'chainlink':
        if not shutil.which('chainlink'):
            critical.append("Chainlink not installed - run 'cargo install chainlink'")
        elif not Path('.chainlink/issues.db').exists():
            warnings.append("Chainlink not initialized - run 'chainlink init'")
    
    # Check for interrupted migration
    if Path('.claude/dp-migration-in-progress').exists():
        critical.append("Interrupted migration detected - run '/dp:migrate --resume' or '--rollback'")
    
    return critical, warnings
```

### 13.11 Recovery Commands

#### 13.11.1 `/dp:repair` Command

```
/dp:repair [--all] [--config] [--hooks] [--database] [--specs]
```

| Flag | Action |
|------|--------|
| `--all` | Run all repair operations |
| `--config` | Regenerate dp-config.yaml from defaults + detected settings |
| `--hooks` | Regenerate missing hook scripts from templates |
| `--database` | Run SQLite integrity check, vacuum, rebuild indexes |
| `--specs` | Fix orphan references, validate spec ID format |
| `--dry-run` | Show what would be repaired without making changes |

#### 13.11.2 `/dp:reset` Command

```
/dp:reset [--soft] [--hard] [--preserve-data]
```

| Mode | Action |
|------|--------|
| `--soft` | Reset config to defaults, keep data |
| `--hard` | Remove all plugin files, reinitialize |
| `--preserve-data` | With `--hard`, export issues before reset |

**Reset Confirmation:**
```
+==========================================================================+
|  [!]  RESET CONFIRMATION                                                  |
+==========================================================================+
|                                                                          |
|  You are about to reset disciplined-process-plugin.                      |
|                                                                          |
|  Mode: --hard                                                            |
|                                                                          |
|  This will DELETE:                                                       |
|  • .claude/dp-config.yaml                                                |
|  • .claude/hooks/*.py (5 files)                                          |
|  • .claude/agents/adversary.md                                           |
|  • .claude/dp-migration-map.json                                         |
|                                                                          |
|  This will PRESERVE:                                                     |
|  • .chainlink/issues.db (47 issues)                                      |
|  • specs/ (5 files)                                                      |
|  • adrs/ (3 files)                                                       |
|                                                                          |
|  Type 'RESET' to confirm:                                                |
|                                                                          |
+==========================================================================+
```

### 13.12 Error Message Standards

All error messages should follow this format:

```
+==========================================================================+
|  [ICON] [ERROR TYPE]                                                     |
+==========================================================================+
|                                                                          |
|  [Clear description of what went wrong]                                  |
|                                                                          |
|  [Technical details if helpful]                                          |
|                                                                          |
|  [Numbered list of recovery options, most recommended first]             |
|                                                                          |
|  [Current degradation mode if applicable]                                |
|                                                                          |
+==========================================================================+
```

**Icons:**
- [E] Critical error (system unusable)
- [!] Warning (reduced functionality)
- [N] Network issue
- [C] Conflict
- [D] Data issue
- [T] Timeout

**Principles:**
1. Never show raw stack traces to users
2. Always provide at least one actionable recovery option
3. Indicate current degradation level
4. Log detailed errors to `.claude/logs/` for debugging
5. Include relevant command to get more help

---

## Appendix A: External References

### Repositories

- **disciplined-process-plugin:** https://github.com/rand/disciplined-process-plugin
- **Chainlink:** https://github.com/dollspace-gay/chainlink
- **Beads:** https://github.com/steveyegge/beads
- **rlm-claude-code:** https://github.com/rand/rlm-claude-code
- **RLM Reference Implementation:** https://github.com/alexzhang13/rlm

### Documentation

- **Claude Code Hooks Guide:** https://code.claude.com/docs/en/hooks-guide
- **Claude Code Hooks Reference:** https://code.claude.com/docs/en/hooks
- **Claude Code Plugins:** https://code.claude.com/docs/en/plugins
- **Claude Code Subagents:** https://code.claude.com/docs/en/sub-agents
- **Claude Code Settings:** https://code.claude.com/docs/en/settings

### Papers & Articles

- **RLM Paper:** Zhang, A. L., Kraska, T., & Khattab, O. (2025). Recursive Language Models. arXiv:2512.24601. https://arxiv.org/abs/2512.24601
- **RLM Blog:** https://alexzhang13.github.io/blog/2025/rlm/
- **VDD Methodology:** https://gist.github.com/dollspace-gay/45c95ebfb5a3a3bae84d8bebd662cc25

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **ADR** | Architecture Decision Record — documents significant design decisions |
| **Beads** | Git-backed issue tracker using JSONL storage |
| **Chainlink** | SQLite-based issue tracker with session management |
| **Degradation Level** | Numbered tier (0-4) indicating current functionality reduction |
| **Fresh Context** | Invoking an LLM without conversation history |
| **Graceful Degradation** | Reducing functionality instead of failing completely when components are unavailable |
| **Hallucination** | When an LLM fabricates information not grounded in provided context |
| **Health Check** | Automated verification of component status and configuration validity |
| **Orphan Reference** | A spec-to-issue or code-to-spec link where the target no longer exists |
| **Recovery Mode** | Operational state focused on repairing corrupted or missing components |
| **RLM** | Recursive Language Model — inference strategy for unbounded context |
| **Safe Mode** | Minimal functionality mode that prioritizes data preservation |
| **Sarcasmotron** | Adversarial reviewer agent in VDD methodology |
| **Spec** | Specification document with traceable requirement IDs |
| **VDD** | Verification-Driven Development — adversarial validation methodology |
| **@trace** | Code comment marker linking implementation to specifications |

---

*End of Specification*
