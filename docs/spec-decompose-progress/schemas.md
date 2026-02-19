# Schemas & Reference

**Parent:** [README.md](./README.md)  
**Related:** [decomposition.md](./decomposition.md) · [holes.md](./holes.md) · [progress-report.md](./progress-report.md)

---

## Decomposition Output JSON

The subagent produces this JSON structure, which the CLI then transforms into Beads scripts or Markdown files.

### Requirement Graph

```json
{
  "requirements": [
    {
      "id": "SPEC-03.01",
      "text": "The system MUST authenticate users via OAuth 2.0 PKCE flow.",
      "type": "functional",
      "complexity": "complex",
      "depends_on": ["SPEC-05.01"],
      "complexity_signals": {
        "conditions": 3,
        "error_cases": 4,
        "integrations": 2,
        "entities_referenced": ["User", "OAuthProvider", "Session"]
      }
    }
  ],
  "constraints": [
    {
      "id": "CON-01",
      "text": "Must support OAuth providers: Google, GitHub, Microsoft",
      "applies_to": ["SPEC-03.01", "SPEC-03.02"]
    }
  ],
  "ambiguities": [
    {
      "id": "AMB-01",
      "text": "Spec does not define behavior when OAuth token is revoked mid-session",
      "affects": ["SPEC-03.04", "SPEC-03.06"],
      "severity": "high"
    }
  ]
}
```

### Full Decomposition Output

```json
{
  "spec_source": ["docs/spec/auth.md"],
  "epic": {
    "title": "User Authentication System",
    "description": "..."
  },
  "issues": [
    {
      "number": 1,
      "title": "OAuth Integration",
      "tasks": [1, 2, 3]
    }
  ],
  "tasks": [
    {
      "number": 1,
      "title": "Configure OAuth provider",
      "description": "Self-contained task description...",
      "priority": 1,
      "depends_on_tasks": [],
      "depends_on_holes": [],
      "spec_traces": ["SPEC-03.01"],
      "context_files": [
        {
          "path": "src/config/oauth.py",
          "reason": "Configuration module to extend",
          "estimated_tokens": 800
        }
      ],
      "acceptance_criteria": [
        "OAuth provider configuration loads from environment variables",
        "Unit test covers missing config values"
      ],
      "produces": ["src/config/oauth.py", "tests/unit/test_oauth_config.py"],
      "estimated_tokens": {
        "overhead": 3200,
        "implementation": 10000,
        "tests": 4000,
        "total": 17200
      },
      "orchestration": {
        "parallel_group": "foundation",
        "estimated_wall_minutes": "5-10",
        "can_run_with": [2, 9],
        "blocks": [3]
      }
    }
  ],
  "holes": [
    {
      "number": "H001",
      "title": "Session behavior on OAuth token revocation",
      "hole_type": "clarification",
      "priority": 1,
      "known": {
        "input": "User with active session + revoked OAuth token",
        "output": "[? error/redirect/logout behavior]",
        "constraints": ["Must not leave orphaned sessions (SPEC-03.06)"],
        "related_types": ["Session", "OAuthToken", "User"]
      },
      "unknown": [
        "Eager invalidation (push) vs lazy on next request (pull)?",
        "User experience: error page, silent re-auth, or redirect to login?"
      ],
      "blocks_tasks": [5, 6],
      "resolution_method": "human_input",
      "traces": ["SPEC-03.04", "SPEC-03.06"],
      "estimated_resolution_effort": "low"
    }
  ],
  "parallel_groups": [
    {
      "name": "foundation",
      "tasks": [1, 2, 9],
      "rationale": "No shared dependencies, different modules"
    }
  ],
  "coverage": {
    "requirements_total": 15,
    "requirements_covered": 15,
    "requirements_with_holes": 3,
    "uncovered": []
  }
}
```

---

## Progress Report JSON

Machine-readable companion to the Markdown progress report.

```json
{
  "timestamp": "2026-02-19T15:45:00Z",
  "trigger": "issue_completed",
  "epic_progress": 0.33,
  "tasks": {
    "total": 12,
    "completed": 4,
    "in_progress": 0,
    "blocked": 4,
    "ready": 3,
    "not_started": 1
  },
  "holes": {
    "total": 4,
    "resolved": 2,
    "open_blocking": 2,
    "tasks_blocked_by_holes": 3,
    "avg_resolution_minutes": 22
  },
  "ready_task_ids": ["bd-m1n2", "bd-o3p4", "bd-q5r6"],
  "recently_completed": ["bd-e5f6", "bd-g7h8"],
  "discovered_issues": ["bd-x1y2"],
  "open_holes": [
    {
      "id": "H001",
      "type": "clarification",
      "blocks": ["T005", "T006"],
      "urgency": "high"
    }
  ],
  "risks": ["critical_path_dependency_on_bd-w1x2"],
  "files_changed": ["src/api/auth/token_exchange.py"]
}
```

---

## Task Markdown Format

Individual task files in `docs/tasks/tasks/`:

```markdown
# T001: Configure OAuth provider

**Status:** open
**Priority:** P1
**Depends on:** (none)
**Blocks:** T003
**Spec traces:** SPEC-03.01

## Description

[Self-contained description an agent can work from without reading the full spec]

## Context Files to Read

| File | Reason | Est. Tokens |
|------|--------|-------------|
| src/config/oauth.py | Configuration module to extend | ~800 |

## Acceptance Criteria

- [ ] OAuth provider configuration loads from environment variables
- [ ] Unit test covers missing config values

## Orchestration

<!-- ORCHESTRATION METADATA
parallel_group: foundation
estimated_tokens: 17200
estimated_wall_minutes: 5-10
produces: ["src/config/oauth.py", "tests/unit/test_oauth_config.py"]
consumes: []
can_run_with: [2, 9]
blocks: [3]
-->

## Completion Notes

_Not yet completed._
```

---

## Hole Markdown Format

Individual hole files in `docs/tasks/holes/`:

```markdown
# H001: Session behavior on OAuth token revocation

**Type:** clarification
**Priority:** P1
**Status:** open
**Blocks:** T005, T006

## Known

- Input: User with active session + revoked OAuth token
- Output: [? some error/redirect/logout behavior]
- Constraint: Must not leave orphaned sessions (SPEC-03.06)

## Unknown

- Eager invalidation (push) vs lazy on next request (pull)?
- User experience: error page, silent re-auth, or redirect to login?

## Resolution Method

Human input required. Answer the questions above.

## Resolution

_Not yet resolved._

<!-- When resolved, fill in:
## Resolution
Decision: [decision text]
Rationale: ...
Resolved by: [human/agent]
Date: ...
-->
```

---

## State File (state.yaml)

Machine-readable state for diffing in Markdown mode:

```yaml
version: 1
spec_source:
  - docs/spec/auth.md
  - docs/spec/auth-appendix.md
spec_hash: "sha256:abc123..."  # For detecting spec changes
generated_at: "2026-02-19T14:00:00Z"

epic:
  title: "User Authentication System"

tasks:
  - number: 1
    title: "Configure OAuth provider"
    status: open
    priority: 1
    depends_on: []
    blocks: [3]
    traces: ["SPEC-03.01"]
    estimated_tokens: 17200

holes:
  - number: H001
    title: "Session behavior on OAuth token revocation"
    type: clarification
    status: open
    blocks: [5, 6]
    traces: ["SPEC-03.04", "SPEC-03.06"]

parallel_groups:
  - name: foundation
    tasks: [1, 2, 9]

dependencies:
  - from: 3
    to: 1
    type: blocks
  - from: 5
    to: H001
    type: blocks
```

---

## Configuration YAML

Full schema for `.claude/progress-report.yaml`:

```yaml
# Trigger conditions (all optional, defaults shown)
triggers:
  interval: 30m              # Time-based polling
  tasks_completed: 3         # After N completions
  issue_completed: true      # When full issue completes
  epic_milestone: true       # At 25/50/75/100%
  on_failure: true           # On task failure
  on_rework: true            # When diff creates rework
  on_blocker: true           # When all work blocked
  hole_created: true         # New hole discovered
  hole_resolved: true        # Hole resolved
  all_work_hole_blocked: true # All work blocked by holes
  on_demand: true            # Manual trigger always available

# Broadcast channels (all optional)
broadcast:
  file: true
  agent_brief: docs/progress/latest.md

  email:
    enabled: false
    to: []
    on_triggers: []

  slack:
    enabled: false
    webhook_url: ""
    channel: ""
    on_triggers: []
    format: summary  # summary | full

  discord:
    enabled: false
    webhook_url: ""
    on_triggers: []
    format: summary

  webhook:
    enabled: false
    url: ""
    method: POST
    payload: json  # json | markdown
    on_triggers: [all]
```

---

## Beads Label Conventions

| Label | Meaning |
|-------|---------|
| `hole` | All holes |
| `hole:clarification` | Needs human answer |
| `hole:validation` | Needs verification (agent-resolvable) |
| `hole:research` | Needs investigation (agent-resolvable) |
| `hole:synthesis` | Needs design combination |
| `hole:escalation` | Agent hit a wall |
| `hole:agent-resolvable` | Convenience: validation + research |
| `hole:human-required` | Convenience: clarification + escalation |

---

## Cross-Reference Index

| ID Pattern | Defined In | Meaning |
|------------|-----------|---------|
| `[ALGO-n]` | [decomposition.md](./decomposition.md) | Decomposition algorithm steps |
| `[ALGO-1b]` | [decomposition.md](./decomposition.md) | Hole identification step |
| `[HOLE-type]` | [holes.md](./holes.md) | Hole taxonomy entries |
| `[SIZE-n]` | [context-sizing.md](./context-sizing.md) | Sizing rules |
| `[DIFF-n]` | [diff.md](./diff.md) | Diff algorithm steps |
