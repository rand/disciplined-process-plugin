// Command trace-validator checks for @trace SPEC-XX.YY markers in test files
// when implementation files reference specs.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/rand/disciplined-process-plugin/internal/events"
	"github.com/rand/disciplined-process-plugin/internal/hookio"
)

var specRefPattern = regexp.MustCompile(`SPEC-\d+\.\d+`)
var tracePattern = regexp.MustCompile(`@trace\s+SPEC-\d+\.\d+`)

func main() {
	input, err := hookio.ReadInput()
	if err != nil {
		hookio.Debug("Failed to read input: %v", err)
		os.Exit(1)
	}

	hookio.Debug("Trace validator: tool=%s", input.ToolName)

	// Extract file path from tool output
	var toolOutput map[string]any
	if err := json.Unmarshal(input.ToolOutput, &toolOutput); err != nil {
		hookio.Approve("")
		return
	}

	filePath, ok := toolOutput["filePath"].(string)
	if !ok {
		// Try tool input
		var toolInput map[string]any
		if err := json.Unmarshal(input.ToolInput, &toolInput); err == nil {
			filePath, _ = toolInput["file_path"].(string)
		}
	}
	if filePath == "" {
		hookio.Approve("")
		return
	}

	// Skip non-implementation files
	if isTestFile(filePath) || isSpecFile(filePath) || isDocFile(filePath) {
		hookio.Approve("")
		return
	}

	// Read the file and check for spec references
	content, err := os.ReadFile(filePath)
	if err != nil {
		hookio.Approve("")
		return
	}

	specRefs := specRefPattern.FindAllString(string(content), -1)
	if len(specRefs) == 0 {
		hookio.Approve("")
		return
	}

	// Deduplicate
	seen := make(map[string]bool)
	var uniqueRefs []string
	for _, ref := range specRefs {
		if !seen[ref] {
			seen[ref] = true
			uniqueRefs = append(uniqueRefs, ref)
		}
	}

	// Check for corresponding @trace markers in test files
	projectDir := hookio.ProjectDir()
	missing := findMissingTraces(projectDir, uniqueRefs)

	if len(missing) > 0 {
		msg := fmt.Sprintf("Spec refs without @trace markers in tests: %s", strings.Join(missing, ", "))
		hookio.Debug(msg)

		events.Emit(map[string]any{
			"type":       "trace_validation",
			"source":     "disciplined-process",
			"file":       filePath,
			"spec_refs":  uniqueRefs,
			"missing":    missing,
			"all_traced": false,
		}, "disciplined-process")

		hookio.Approve(msg)
	} else {
		events.Emit(map[string]any{
			"type":       "trace_validation",
			"source":     "disciplined-process",
			"file":       filePath,
			"spec_refs":  uniqueRefs,
			"all_traced": true,
		}, "disciplined-process")

		hookio.Approve("")
	}
}

func isTestFile(path string) bool {
	base := filepath.Base(path)
	return strings.HasPrefix(base, "test_") || strings.HasSuffix(base, "_test.go") ||
		strings.Contains(base, ".test.") || strings.Contains(base, ".spec.")
}

func isSpecFile(path string) bool {
	return strings.Contains(path, "docs/spec/") || strings.Contains(path, "specs/")
}

func isDocFile(path string) bool {
	return strings.HasSuffix(path, ".md") || strings.Contains(path, "docs/")
}

func findMissingTraces(projectDir string, specRefs []string) []string {
	var missing []string

	// Find test files
	testPatterns := []string{
		"**/test_*.py",
		"**/*_test.go",
		"**/*.test.ts",
		"**/*.test.tsx",
		"**/*.spec.ts",
	}

	var testFiles []string
	for _, pattern := range testPatterns {
		matches, _ := filepath.Glob(filepath.Join(projectDir, pattern))
		testFiles = append(testFiles, matches...)
		// Also check common test dirs
		for _, dir := range []string{"tests", "test", "__tests__"} {
			matches, _ = filepath.Glob(filepath.Join(projectDir, dir, pattern))
			testFiles = append(testFiles, matches...)
		}
	}

	// Read all test files and collect traces
	tracedSpecs := make(map[string]bool)
	for _, tf := range testFiles {
		content, err := os.ReadFile(tf)
		if err != nil {
			continue
		}
		traces := tracePattern.FindAllString(string(content), -1)
		for _, t := range traces {
			// Extract SPEC-XX.YY from "@trace SPEC-XX.YY"
			parts := strings.Fields(t)
			if len(parts) >= 2 {
				tracedSpecs[parts[1]] = true
			}
		}
	}

	for _, ref := range specRefs {
		if !tracedSpecs[ref] {
			missing = append(missing, ref)
		}
	}

	return missing
}
