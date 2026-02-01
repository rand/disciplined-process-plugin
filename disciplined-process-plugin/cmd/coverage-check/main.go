// Command coverage-check calculates spec-to-test traceability coverage.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/rand/disciplined-process-plugin/internal/hookio"
)

var specIDPattern = regexp.MustCompile(`\[SPEC-(\d+\.\d+)\]`)
var tracePattern = regexp.MustCompile(`@trace\s+SPEC-(\d+\.\d+)`)

func main() {
	projectDir := hookio.ProjectDir()
	hookio.Debug("Coverage check in: %s", projectDir)

	// Find all specs
	specDir := filepath.Join(projectDir, "docs", "spec")
	specs := findSpecs(specDir)

	// Find all traces in test files
	traces := findTraces(projectDir)

	// Calculate coverage
	total := len(specs)
	covered := 0
	var uncovered []string
	for _, spec := range specs {
		if traces[spec] {
			covered++
		} else {
			uncovered = append(uncovered, spec)
		}
	}

	pct := 0.0
	if total > 0 {
		pct = float64(covered) / float64(total) * 100
	}

	result := map[string]any{
		"total_specs":      total,
		"covered_specs":    covered,
		"coverage_percent": fmt.Sprintf("%.1f%%", pct),
		"uncovered":        uncovered,
	}

	data, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(data))
}

func findSpecs(specDir string) []string {
	var specs []string
	filepath.Walk(specDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || !strings.HasSuffix(path, ".md") {
			return nil
		}
		content, err := os.ReadFile(path)
		if err != nil {
			return nil
		}
		matches := specIDPattern.FindAllStringSubmatch(string(content), -1)
		for _, m := range matches {
			specs = append(specs, "SPEC-"+m[1])
		}
		return nil
	})
	return specs
}

func findTraces(projectDir string) map[string]bool {
	traced := make(map[string]bool)
	for _, dir := range []string{"tests", "test", "__tests__", "."} {
		searchDir := filepath.Join(projectDir, dir)
		filepath.Walk(searchDir, func(path string, info os.FileInfo, err error) error {
			if err != nil || info.IsDir() {
				return nil
			}
			content, err := os.ReadFile(path)
			if err != nil {
				return nil
			}
			matches := tracePattern.FindAllStringSubmatch(string(content), -1)
			for _, m := range matches {
				traced["SPEC-"+m[1]] = true
			}
			return nil
		})
	}
	return traced
}
