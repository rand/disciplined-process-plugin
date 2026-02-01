// Package events provides cross-plugin event utilities for disciplined-process.
package events

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

type Event struct {
	Type          string    `json:"type"`
	Timestamp     time.Time `json:"timestamp"`
	Source        string    `json:"source"`
	SessionID     string    `json:"session_id,omitempty"`
	CorrelationID string    `json:"correlation_id,omitempty"`
}

type PhaseTransitionEvent struct {
	Event
	FromPhase        string   `json:"from_phase"`
	ToPhase          string   `json:"to_phase"`
	TaskID           string   `json:"task_id,omitempty"`
	SpecRefs         []string `json:"spec_refs,omitempty"`
	ValidationPassed bool     `json:"validation_passed"`
}

func eventsDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	dir := filepath.Join(home, ".claude", "events")
	os.MkdirAll(dir, 0755)
	return dir
}

func Emit(event any, source string) error {
	dir := eventsDir()

	logFile := filepath.Join(dir, source+"-events.jsonl")
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	if err := json.NewEncoder(f).Encode(event); err != nil {
		return err
	}

	latestFile := filepath.Join(dir, source+"-latest.json")
	data, err := json.MarshalIndent(event, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(latestFile, data, 0644)
}

func ReadLatest(source string) (map[string]any, error) {
	dir := eventsDir()
	latestFile := filepath.Join(dir, source+"-latest.json")

	data, err := os.ReadFile(latestFile)
	if err != nil {
		return nil, err
	}

	var event map[string]any
	if err := json.Unmarshal(data, &event); err != nil {
		return nil, err
	}
	return event, nil
}

func GetDPPhase() string {
	event, err := ReadLatest("disciplined-process")
	if err != nil {
		return "unknown"
	}
	if event["type"] == "phase_transition" {
		if phase, ok := event["to_phase"].(string); ok {
			return phase
		}
	}
	return "unknown"
}

func GetRLMMode() string {
	event, err := ReadLatest("rlm-claude-code")
	if err != nil {
		return "unknown"
	}
	if event["type"] == "mode_change" {
		if mode, ok := event["to_mode"].(string); ok {
			return mode
		}
	}
	return "unknown"
}
