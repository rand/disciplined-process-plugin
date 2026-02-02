package hookio

import (
	"bytes"
	"encoding/json"
	"os"
	"testing"
)

func TestReadInput(t *testing.T) {
	input := `{"session_id":"test-123","tool_name":"Edit","tool_input":{"file_path":"/tmp/x.py"}}`
	old := os.Stdin
	defer func() { os.Stdin = old }()
	os.Stdin = createTempFile(t, input)

	hi, err := ReadInput()
	if err != nil {
		t.Fatalf("ReadInput failed: %v", err)
	}
	if hi.SessionID != "test-123" {
		t.Errorf("SessionID = %q, want %q", hi.SessionID, "test-123")
	}
	if hi.ToolName != "Edit" {
		t.Errorf("ToolName = %q, want %q", hi.ToolName, "Edit")
	}
}

func TestReadInputMalformed(t *testing.T) {
	old := os.Stdin
	defer func() { os.Stdin = old }()
	os.Stdin = createTempFile(t, "not json")

	_, err := ReadInput()
	if err == nil {
		t.Fatal("Expected error for malformed input")
	}
}

func TestWriteOutput(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	WriteOutput(&HookOutput{Decision: "approve", Reason: "ok"})
	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	buf.ReadFrom(r)

	var parsed HookOutput
	if err := json.Unmarshal(buf.Bytes(), &parsed); err != nil {
		t.Fatalf("Failed to parse output: %v", err)
	}
	if parsed.Decision != "approve" {
		t.Errorf("Decision = %q, want %q", parsed.Decision, "approve")
	}
}

func TestSessionContextOutput(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	SessionContext("test context")
	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	buf.ReadFrom(r)

	var parsed HookOutput
	json.Unmarshal(buf.Bytes(), &parsed)
	if parsed.HookSpecific == nil {
		t.Fatal("HookSpecific is nil")
	}
	if parsed.HookSpecific.AdditionalContext != "test context" {
		t.Errorf("AdditionalContext = %q, want %q", parsed.HookSpecific.AdditionalContext, "test context")
	}
}

func TestProjectDirFromEnv(t *testing.T) {
	t.Setenv("CLAUDE_PROJECT_DIR", "/test/project")
	if dir := ProjectDir(); dir != "/test/project" {
		t.Errorf("ProjectDir = %q, want %q", dir, "/test/project")
	}
}

func TestProjectDirFallback(t *testing.T) {
	t.Setenv("CLAUDE_PROJECT_DIR", "")
	if dir := ProjectDir(); dir == "" {
		t.Error("ProjectDir should not be empty")
	}
}

func createTempFile(t *testing.T, content string) *os.File {
	t.Helper()
	f, err := os.CreateTemp(t.TempDir(), "test-*.json")
	if err != nil {
		t.Fatal(err)
	}
	f.WriteString(content)
	f.Seek(0, 0)
	return f
}
