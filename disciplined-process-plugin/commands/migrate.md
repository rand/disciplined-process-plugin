---
description: Migrate between task tracker providers
argument-hint: <beads-to-chainlink|chainlink-to-beads> [--dry-run]
---

# Migrate Command

Migrate issues between Beads and Chainlink task trackers with full data preservation.

## Subcommands

### beads-to-chainlink
Migrate from Beads to Chainlink.

```
/dp:migrate beads-to-chainlink [--dry-run]
```

**Requirements**:
- `.beads/` directory must exist with `issues.jsonl`
- `chainlink` CLI must be installed

**Process**:
1. **Parse Beads Data**: Read `.beads/issues.jsonl`, extract all issue metadata
2. **Create Chainlink Issues**: Initialize Chainlink if needed, create all issues
3. **Recreate Dependencies**: Map `blocks`, `related`, `parent-child` relationships
4. **Generate Mapping**: Create `.claude/dp-migration-map.json` for ID translation
5. **Update References**: Update spec files and code comments with new IDs
6. **Update Config**: Set `task_tracker: chainlink` in `dp-config.yaml`

**Data Preserved**:
- Issue title, description, status, priority
- Labels and assignees
- Dependencies (blocks, related, parent-child)
- Spec references ([SPEC-XX.YY] links)
- Created/updated timestamps

**Output**:
```
Migrating Beads → Chainlink
===========================

Found 15 issues in .beads/issues.jsonl

Step 1/5: Parsing Beads data... done
Step 2/5: Creating Chainlink issues...
  [1/15] bd-a1b2 → CL-1 (Implement authentication)
  [2/15] bd-f14c → CL-2 (Fix parser edge case)
  ...
Step 3/5: Recreating dependencies... done (8 relationships)
Step 4/5: Updating spec references... done (3 files updated)
Step 5/5: Updating configuration... done

Migration complete!
  - 15 issues migrated
  - 8 dependencies preserved
  - Mapping saved to .claude/dp-migration-map.json

Verify with: chainlink list
```

### chainlink-to-beads
Migrate from Chainlink to Beads.

```
/dp:migrate chainlink-to-beads [--dry-run]
```

**Requirements**:
- `.chainlink/` directory must exist
- `bd` CLI must be installed

**Data Loss Warnings**:
| Feature | Behavior |
|---------|----------|
| Sessions | **Lost** - Beads doesn't support sessions |
| Time tracking | **Lost** - Beads doesn't track time |
| Milestones | **Flattened** - Converted to labels |
| Related issues | **Converted** - Become comments |
| Issue IDs | **Regenerated** - New hash-based IDs |

**Confirmation Required**:
```
Warning: The following data will be lost during migration:
  - 3 sessions with handoff notes
  - 5h 30m of time tracking data
  - 2 milestones (converted to labels)

Continue? [y/N]
```

## Options

### --dry-run
Preview migration without making changes.

```
/dp:migrate beads-to-chainlink --dry-run
```

**Output**:
```
DRY RUN - No changes will be made
==================================

Would migrate 15 issues:
  bd-a1b2 → CL-1 (Implement authentication)
  bd-f14c → CL-2 (Fix parser edge case)
  ...

Would create 8 dependency relationships
Would update 3 spec files
Would update dp-config.yaml

To execute, run without --dry-run
```

## Mapping File

After migration, `.claude/dp-migration-map.json` contains ID mappings:

```json
{
  "migrated_at": "2026-01-22T10:30:00Z",
  "source": "beads",
  "target": "chainlink",
  "version": "1.0",
  "mappings": [
    {
      "source_id": "bd-a1b2",
      "target_id": "CL-1",
      "title": "Implement authentication",
      "spec_refs": ["SPEC-01.01", "SPEC-01.02"]
    },
    {
      "source_id": "bd-f14c",
      "target_id": "CL-2",
      "title": "Fix parser edge case",
      "spec_refs": []
    }
  ]
}
```

This file enables:
- Reverse migration if needed
- Updating references in documentation
- Translating old IDs in git history

## Rollback

If migration fails mid-way:
1. Original data is preserved (no destructive operations until final step)
2. Partial migration can be cleaned with `/dp:migrate cleanup`
3. Mapping file records progress for manual recovery

## Post-Migration

After successful migration:
1. Verify issues: `chainlink list` or `bd list`
2. Check dependencies: `chainlink blocked` or `bd blocked`
3. Update any hardcoded issue IDs in documentation
4. Commit the migration: `git add -A && git commit -m "Migrate to [tracker]"`
