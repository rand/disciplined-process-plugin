#!/bin/bash
# Session start hook - show ready work and context
# Gracefully handles missing CLIs and misconfigured providers

CONFIG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/dp-config.yaml"
WARN_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/.dp-provider-warned"

get_provider() {
    if [ -f "$CONFIG_FILE" ]; then
        grep -E "^\s*provider:" "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "none"
    else
        echo "none"
    fi
}

# Check if CLI is available for provider
check_provider_cli() {
    local provider="$1"
    case "$provider" in
        beads)
            command -v bd &> /dev/null && [ -d "${CLAUDE_PROJECT_DIR:-.}/.beads" ]
            ;;
        github)
            command -v gh &> /dev/null
            ;;
        linear)
            command -v linear &> /dev/null
            ;;
        markdown)
            return 0  # Always available
            ;;
        none)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Warn once per session about missing provider CLI
warn_missing_provider() {
    local provider="$1"
    # Only warn once per day (file mtime check)
    if [ -f "$WARN_FILE" ]; then
        local warn_age=$(($(date +%s) - $(stat -f %m "$WARN_FILE" 2>/dev/null || echo 0)))
        if [ $warn_age -lt 86400 ]; then
            return
        fi
    fi

    mkdir -p "$(dirname "$WARN_FILE")"
    touch "$WARN_FILE"

    case "$provider" in
        beads)
            if ! command -v bd &> /dev/null; then
                echo "{\"feedback\": \"⚠️ Task provider 'beads' configured but 'bd' CLI not found. Run 'bd init' or change provider in dp-config.yaml\"}"
            elif [ ! -d "${CLAUDE_PROJECT_DIR:-.}/.beads" ]; then
                echo "{\"feedback\": \"⚠️ Task provider 'beads' configured but .beads/ not initialized. Run 'bd init' in project root.\"}"
            fi
            ;;
        github)
            echo "{\"feedback\": \"⚠️ Task provider 'github' configured but 'gh' CLI not found. Install GitHub CLI or change provider.\"}"
            ;;
        linear)
            echo "{\"feedback\": \"⚠️ Task provider 'linear' configured but 'linear' CLI not found. Install Linear CLI or change provider.\"}"
            ;;
    esac
}

PROVIDER=$(get_provider)

show_ready_work() {
    # Check if provider is available
    if ! check_provider_cli "$PROVIDER"; then
        warn_missing_provider "$PROVIDER"
        return
    fi

    case "$PROVIDER" in
        beads)
            ready_count=$(bd ready --json 2>/dev/null | jq 'length' 2>/dev/null || echo "")
            if [ -n "$ready_count" ] && [ "$ready_count" != "0" ]; then
                echo "{\"feedback\": \"📋 $ready_count tasks ready. Run '/dp:task ready' to see them.\"}"
            fi
            ;;
        github)
            ready_count=$(gh issue list --label ready --json number 2>/dev/null | jq 'length' 2>/dev/null || echo "")
            if [ -n "$ready_count" ] && [ "$ready_count" != "0" ]; then
                echo "{\"feedback\": \"📋 $ready_count issues ready. Run '/dp:task ready' to see them.\"}"
            fi
            ;;
        markdown)
            if [ -d "${CLAUDE_PROJECT_DIR:-.}/docs/tasks" ]; then
                ready_count=$(grep -l "status: ready" "${CLAUDE_PROJECT_DIR:-.}/docs/tasks"/*.md 2>/dev/null | wc -l | tr -d ' ')
                if [ -n "$ready_count" ] && [ "$ready_count" != "0" ]; then
                    echo "{\"feedback\": \"📋 $ready_count tasks ready in docs/tasks/. Run '/dp:task ready' to see them.\"}"
                fi
            fi
            ;;
        none)
            # Configured to skip task tracking - silent
            ;;
    esac
}

show_ready_work
exit 0
