#!/bin/bash
# Pre-commit check for disciplined process
# Runs tests and validates spec compliance before allowing commit

set -e

# Load config
CONFIG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/dp-config.yaml"

get_enforcement() {
    if [ -f "$CONFIG_FILE" ]; then
        grep -E "^\s*level:" "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "strict"
    else
        echo "strict"
    fi
}

ENFORCEMENT=$(get_enforcement)

# In minimal mode, skip all checks
if [ "$ENFORCEMENT" = "minimal" ]; then
    exit 0
fi

echo "🔍 Running pre-commit checks..."

# Detect project type and run appropriate tests
run_tests() {
    if [ -f "package.json" ]; then
        if grep -q '"test"' package.json; then
            echo "Running npm test..."
            npm test --passWithNoTests 2>&1 || return 1
        fi
    elif [ -f "Cargo.toml" ]; then
        echo "Running cargo test..."
        cargo test 2>&1 || return 1
    elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
        echo "Running pytest..."
        python -m pytest -x 2>&1 || return 1
    elif [ -f "go.mod" ]; then
        echo "Running go test..."
        go test ./... 2>&1 || return 1
    fi
    return 0
}

# Check for spec trace markers in staged files
check_traces() {
    local src_files
    src_files=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(ts|tsx|js|jsx|py|rs|go|zig)$' | grep -v 'test' || true)
    
    if [ -z "$src_files" ]; then
        return 0
    fi
    
    local missing_traces=0
    for file in $src_files; do
        if ! grep -q '@trace SPEC-' "$file" 2>/dev/null; then
            echo "⚠️  Missing @trace marker: $file"
            missing_traces=$((missing_traces + 1))
        fi
    done
    
    if [ $missing_traces -gt 0 ] && [ "$ENFORCEMENT" = "strict" ]; then
        echo ""
        echo "❌ $missing_traces files missing @trace SPEC-XX.YY markers"
        echo "   Add trace markers linking implementation to specifications."
        return 1
    elif [ $missing_traces -gt 0 ]; then
        echo ""
        echo "⚠️  $missing_traces files missing trace markers (non-blocking in guided mode)"
    fi
    
    return 0
}

# Run checks
FAILED=0

if ! run_tests; then
    echo ""
    echo "❌ Tests failed. Fix tests before committing."
    if [ "$ENFORCEMENT" = "strict" ]; then
        FAILED=1
    fi
fi

if ! check_traces; then
    if [ "$ENFORCEMENT" = "strict" ]; then
        FAILED=1
    fi
fi

if [ $FAILED -eq 1 ]; then
    echo ""
    echo "Commit blocked. Fix issues above or use --no-verify to bypass (not recommended)."
    exit 1
fi

echo "✅ Pre-commit checks passed"
exit 0
