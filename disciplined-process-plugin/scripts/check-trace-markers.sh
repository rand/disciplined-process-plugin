#!/bin/bash
# Check for @trace SPEC-XX.YY markers in implementation files
# Called after file writes to remind about traceability

FILES="$1"

if [ -z "$FILES" ]; then
    exit 0
fi

# Skip test files
if echo "$FILES" | grep -qE '(test|spec|_test\.|\.test\.)'; then
    exit 0
fi

# Check each file
for file in $FILES; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Skip if file already has trace markers
    if grep -q '@trace SPEC-' "$file" 2>/dev/null; then
        continue
    fi
    
    # Get file extension for appropriate comment syntax
    ext="${file##*.}"
    
    case "$ext" in
        ts|tsx|js|jsx|go|rs|zig)
            comment="//"
            ;;
        py)
            comment="#"
            ;;
        *)
            continue
            ;;
    esac
    
    # Output reminder as feedback (non-blocking)
    echo "{\"feedback\": \"💡 Consider adding @trace SPEC-XX.YY marker to $file to link implementation to specification\"}"
done

exit 0
