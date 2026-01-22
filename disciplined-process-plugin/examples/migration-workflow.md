# Migration Workflow

Migrating between task trackers while preserving all data and traceability.

## Scenario

Your team has been using Beads and wants to migrate to Chainlink for its session management and time tracking features.

## Pre-Migration Check

```bash
# Check current state
bd stats

# Output:
# Total issues: 47
# Open: 12
# In progress: 3
# Closed: 32
# Blocked: 2

# Ensure everything is synced
bd sync

# Output:
# Already up to date with remote
```

## Dry Run First

Always preview the migration before applying:

```bash
/dp:migrate beads-to-chainlink --dry-run

# Output:
# =================================================
# Migration Preview: Beads → Chainlink
# =================================================
#
# Issues to migrate: 47
#
# ID Mapping (preview):
#   bd-a1b2c3 → chainlink-1
#   bd-d4e5f6 → chainlink-2
#   bd-g7h8i9 → chainlink-3
#   ... (44 more)
#
# Dependencies to recreate: 8
#   bd-a1b2c3 blocks bd-d4e5f6 → chainlink-1 blocks chainlink-2
#   bd-g7h8i9 blocks bd-j0k1l2 → chainlink-3 blocks chainlink-4
#   ...
#
# Spec references to update: 15
#   docs/spec/01-core.md: <!-- beads:bd-a1b2c3 --> → <!-- chainlink:1 -->
#   docs/spec/02-auth.md: <!-- beads:bd-d4e5f6 --> → <!-- chainlink:2 -->
#   ...
#
# No changes made. Run without --dry-run to apply.
```

## Execute Migration

```bash
/dp:migrate beads-to-chainlink

# Output:
# =================================================
# Migration: Beads → Chainlink
# =================================================
#
# Phase 1: Exporting from Beads...
#   [x] Exported 47 issues
#   [x] Exported 8 dependencies
#   [x] Exported labels and metadata
#
# Phase 2: Initializing Chainlink...
#   [x] Created .chainlink/ directory
#   [x] Initialized database
#
# Phase 3: Importing to Chainlink...
#   [x] Created 47 issues
#   [x] Recreated 8 dependencies
#   [x] Preserved timestamps and status
#
# Phase 4: Updating references...
#   [x] Updated 15 spec references
#   [x] Generated migration map
#
# Migration complete!
#
# Files created:
#   .chainlink/           - Chainlink database
#   .claude/dp-migration-map.json - ID mapping reference
#
# Original Beads data preserved in .beads/
# You can safely remove it after verifying migration.
```

## Verify Migration

```bash
# Check Chainlink has all issues
chainlink list --limit 50

# Verify a specific issue
chainlink show 1

# Output:
# Issue #1: Implement user authentication
# Status: open
# Priority: P1
# Created: 2024-01-10 (migrated from bd-a1b2c3)
# Dependencies: blocks #2, #3
# Labels: feature, auth

# Check spec references updated
grep -r "chainlink:" docs/spec/

# Output:
# docs/spec/01-core.md:<!-- chainlink:1 -->
# docs/spec/02-auth.md:<!-- chainlink:2 -->
```

## Migration Map

The migration creates a mapping file for reference:

```bash
cat .claude/dp-migration-map.json

# Output:
{
  "source": "beads",
  "target": "chainlink",
  "migrated_at": "2024-01-15T10:30:00Z",
  "mappings": {
    "bd-a1b2c3": "1",
    "bd-d4e5f6": "2",
    "bd-g7h8i9": "3",
    ...
  },
  "stats": {
    "issues_migrated": 47,
    "dependencies_migrated": 8,
    "references_updated": 15
  }
}
```

## Cleanup (Optional)

After verifying the migration:

```bash
# Remove old Beads data
rm -rf .beads/

# Update dp-config.yaml
# Change: task_tracker: beads
# To:     task_tracker: chainlink

# Commit the migration
git add .chainlink/ .claude/dp-migration-map.json docs/spec/
git commit -m "chore: migrate from Beads to Chainlink

- Migrated 47 issues with full history
- Preserved 8 dependency relationships
- Updated 15 spec references
- Migration map: .claude/dp-migration-map.json"
```

## Reverse Migration

If you need to go back to Beads:

```bash
/dp:migrate chainlink-to-beads --dry-run

# Output:
# =================================================
# Migration Preview: Chainlink → Beads
# =================================================
#
# Issues to migrate: 47
# Note: Session history will not be migrated (Beads doesn't support sessions)
#
# ... (preview output)

/dp:migrate chainlink-to-beads

# Output:
# Migration complete!
# Note: Session and time tracking data preserved in .chainlink/ but not migrated.
```

## Partial Migration

Migrate only specific issues:

```bash
# Migrate only open issues
/dp:migrate beads-to-chainlink --status open

# Migrate specific labels
/dp:migrate beads-to-chainlink --labels "priority:high,feature"
```

## Troubleshooting

### Duplicate Issues

```bash
# If migration creates duplicates, use --force to overwrite
/dp:migrate beads-to-chainlink --force
```

### Missing Dependencies

```bash
# If some dependencies fail to migrate
chainlink dep add 5 3  # Manually add: issue 5 depends on issue 3
```

### Spec References Not Updated

```bash
# Manually update a spec reference
# Change: <!-- beads:bd-xyz123 -->
# To:     <!-- chainlink:42 -->

# Or re-run reference update
/dp:spec link SPEC-01.03 chainlink-42
```
