package events

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestEmitAndReadLatest(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	os.MkdirAll(filepath.Join(tmpDir, ".claude", "events"), 0755)

	event := map[string]any{"type": "test_event", "value": 42}
	if err := Emit(event, "test-source"); err != nil {
		t.Fatalf("Emit failed: %v", err)
	}

	latest, err := ReadLatest("test-source")
	if err != nil {
		t.Fatalf("ReadLatest failed: %v", err)
	}
	if latest["type"] != "test_event" {
		t.Errorf("type = %v, want test_event", latest["type"])
	}
}

func TestReadLatestMissing(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	os.MkdirAll(filepath.Join(tmpDir, ".claude", "events"), 0755)

	_, err := ReadLatest("nonexistent")
	if err == nil {
		t.Error("Expected error for missing source")
	}
}

func TestGetDPPhaseUnknown(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	os.MkdirAll(filepath.Join(tmpDir, ".claude", "events"), 0755)

	if phase := GetDPPhase(); phase != "unknown" {
		t.Errorf("GetDPPhase = %q, want %q", phase, "unknown")
	}
}

func TestGetDPPhaseFromEvent(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	os.MkdirAll(filepath.Join(tmpDir, ".claude", "events"), 0755)

	Emit(map[string]any{"type": "phase_transition", "to_phase": "implement"}, "disciplined-process")

	if phase := GetDPPhase(); phase != "implement" {
		t.Errorf("GetDPPhase = %q, want %q", phase, "implement")
	}
}

func TestGetRLMModeUnknown(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	os.MkdirAll(filepath.Join(tmpDir, ".claude", "events"), 0755)

	if mode := GetRLMMode(); mode != "unknown" {
		t.Errorf("GetRLMMode = %q, want %q", mode, "unknown")
	}
}

func TestEmitAppendsToLog(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	evDir := filepath.Join(tmpDir, ".claude", "events")
	os.MkdirAll(evDir, 0755)

	Emit(map[string]any{"type": "first"}, "append-test")
	Emit(map[string]any{"type": "second"}, "append-test")

	latest, _ := ReadLatest("append-test")
	if latest["type"] != "second" {
		t.Errorf("latest type = %v, want second", latest["type"])
	}

	data, _ := os.ReadFile(filepath.Join(evDir, "append-test-events.jsonl"))
	lines := 0
	for _, b := range data {
		if b == '\n' {
			lines++
		}
	}
	if lines != 2 {
		t.Errorf("log has %d lines, want 2", lines)
	}
}

func TestLatestFileIsIndented(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	os.MkdirAll(filepath.Join(tmpDir, ".claude", "events"), 0755)

	Emit(map[string]any{"type": "indent_test"}, "indent-src")

	data, _ := os.ReadFile(filepath.Join(tmpDir, ".claude", "events", "indent-src-latest.json"))
	var raw json.RawMessage
	json.Unmarshal(data, &raw)

	// Re-marshal without indent to compare — if they differ, original was indented
	compact, _ := json.Marshal(raw)
	if string(compact) == string(data) {
		t.Error("Latest file should be indented")
	}
}
