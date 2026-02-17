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
		// CLI mode — emit event only, no hook output
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

	// Hook mode: read from stdin, emit orient phase, inject workflow context
	input, err := hookio.ReadInput()
	if err != nil {
		hookio.Debug("phase-emitter: failed to read input: %v", err)
		emitPhase("none", "orient", "")
		hookio.Approve("")
		return
	}

	hookio.Debug("phase-emitter: session=%s", input.SessionID)
	emitPhase("none", "orient", "")

	// Inject DP workflow guidance as additionalContext (replaces former prompt hook).
	// This appears as a system reminder to the model without using Haiku as a gatekeeper.
	hookio.ApproveWithContext("UserPromptSubmit",
		"[DP phase: orient] For new features or changes >20 lines, follow DP phase order: spec → test → implement. For bug fixes and trivial changes (<20 lines), skip phase checks.")
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
}
