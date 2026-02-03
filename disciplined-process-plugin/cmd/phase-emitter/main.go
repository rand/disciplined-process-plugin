// Command phase-emitter emits a phase transition event for cross-plugin coordination.
package main

import (
	"os"
	"time"

	"github.com/rand/disciplined-process-plugin/internal/events"
	"github.com/rand/disciplined-process-plugin/internal/hookio"
)

func main() {
	// Can be called two ways:
	// 1. As a hook binary (reads from stdin)
	// 2. As a CLI tool: phase-emitter <to_phase> [from_phase] [task_id]

	if len(os.Args) >= 2 {
		// CLI mode
		toPhase := os.Args[1]
		fromPhase := "unknown"
		taskID := ""
		if len(os.Args) >= 3 {
			fromPhase = os.Args[2]
		}
		if len(os.Args) >= 4 {
			taskID = os.Args[3]
		}

		emitPhase(fromPhase, toPhase, taskID)
		return
	}

	// Hook mode: read from stdin, emit orient phase on session start
	input, err := hookio.ReadInput()
	if err != nil {
		hookio.Debug("phase-emitter: no input, emitting orient phase")
		emitPhase("none", "orient", "")
		return
	}

	hookio.Debug("phase-emitter: session=%s", input.SessionID)

	// On session start, emit orient phase (the default starting phase)
	emitPhase("none", "orient", "")
}

func emitPhase(from, to, taskID string) {
	event := map[string]any{
		"type":       "phase_transition",
		"timestamp":  time.Now().UTC().Format(time.RFC3339),
		"source":     "disciplined-process",
		"from_phase": from,
		"to_phase":   to,
	}
	if taskID != "" {
		event["task_id"] = taskID
	}

	if err := events.Emit(event, "disciplined-process"); err != nil {
		hookio.Debug("phase-emitter: emit error: %v", err)
	}

	// Output valid JSON for Claude Code hook compliance
	hookio.Approve("")
}
