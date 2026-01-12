#!/bin/bash
# Pre-push sync - ensure task tracker is synced before pushing
# Gracefully skips if provider unavailable

CONFIG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/dp-config.yaml"

get_provider() {
    if [ -f "$CONFIG_FILE" ]; then
        grep -E "^\s*provider:" "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "none"
    else
        echo "none"
    fi
}

PROVIDER=$(get_provider)

sync_tasks() {
    case "$PROVIDER" in
        beads)
            # Only sync if bd is available AND .beads exists
            if command -v bd &> /dev/null && [ -d "${CLAUDE_PROJECT_DIR:-.}/.beads" ]; then
                bd sync 2>/dev/null || true
            fi
            ;;
        github)
            # GitHub syncs automatically via gh CLI
            ;;
        linear)
            # Linear syncs automatically
            ;;
        markdown|none)
            # No sync needed
            ;;
    esac
}

sync_tasks
exit 0
