#!/bin/bash
# Session start hook - show ready work and context

CONFIG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/dp-config.yaml"

get_provider() {
    if [ -f "$CONFIG_FILE" ]; then
        grep -E "^\s*provider:" "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "beads"
    else
        echo "beads"
    fi
}

PROVIDER=$(get_provider)

show_ready_work() {
    case "$PROVIDER" in
        beads)
            if command -v bd &> /dev/null; then
                ready_count=$(bd ready --json 2>/dev/null | jq 'length' 2>/dev/null || echo "0")
                if [ "$ready_count" != "0" ] && [ "$ready_count" != "" ]; then
                    echo "{\"feedback\": \"📋 $ready_count tasks ready for work. Run 'bd ready' to see them.\"}"
                fi
            fi
            ;;
        github)
            if command -v gh &> /dev/null; then
                ready_count=$(gh issue list --label ready --json number 2>/dev/null | jq 'length' 2>/dev/null || echo "0")
                if [ "$ready_count" != "0" ] && [ "$ready_count" != "" ]; then
                    echo "{\"feedback\": \"📋 $ready_count GitHub issues ready. Run 'gh issue list --label ready' to see them.\"}"
                fi
            fi
            ;;
        *)
            # Other providers or none - no feedback
            ;;
    esac
}

show_ready_work
exit 0
