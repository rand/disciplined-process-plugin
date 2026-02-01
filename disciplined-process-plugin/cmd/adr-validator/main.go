// Command adr-validator validates ADR format and completeness.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/rand/disciplined-process-plugin/internal/hookio"
)

var requiredSections = []string{
	"Status",
	"Context",
	"Decision",
	"Consequences",
}

func main() {
	projectDir := hookio.ProjectDir()
	adrDir := filepath.Join(projectDir, "docs", "adr")
	hookio.Debug("ADR validation in: %s", adrDir)

	entries, err := os.ReadDir(adrDir)
	if err != nil {
		fmt.Println("{\"adrs\": [], \"error\": \"no ADR directory found\"}")
		return
	}

	var results []map[string]any
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".md") {
			continue
		}

		path := filepath.Join(adrDir, entry.Name())
		content, err := os.ReadFile(path)
		if err != nil {
			continue
		}

		missing := checkSections(string(content))
		result := map[string]any{
			"file":    entry.Name(),
			"valid":   len(missing) == 0,
			"missing": missing,
		}
		results = append(results, result)
	}

	data, _ := json.MarshalIndent(map[string]any{"adrs": results}, "", "  ")
	fmt.Println(string(data))
}

func checkSections(content string) []string {
	var missing []string
	lower := strings.ToLower(content)
	for _, section := range requiredSections {
		if !strings.Contains(lower, "## "+strings.ToLower(section)) &&
			!strings.Contains(lower, "# "+strings.ToLower(section)) {
			missing = append(missing, section)
		}
	}
	return missing
}
