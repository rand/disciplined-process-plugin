#!/bin/bash
# Pre-push sync - ensure task tracker is synced before pushing

CONFIG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/dp-config.yaml"

get_provider() {
    if [ -f "$CONFIG_FILE" ]; then
        grep -E "^\s*provider:" "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "beads"
    else
        echo "beads"
    fi
}

PROVIDER=$(get_provider)

sync_tasks() {
    case "$PROVIDER" in
        beads)
            if command -v bd &> /dev/null; then
                echo "Syncing beads..."
                bd sync 2>/dev/null || true
            fi
            ;;
        *)
            # Other providers handle their own sync
            ;;
    esac
}

sync_tasks
exit 0
