// Package hookio provides utilities for Claude Code hook input/output.
package hookio

import (
	"encoding/json"
	"fmt"
	"os"
)

// HookInput represents the JSON input received from Claude Code hooks.
type HookInput struct {
	// Common fields
	SessionID string `json:"session_id"`
	CWD       string `json:"cwd,omitempty"`

	// SessionStart specific
	Source string `json:"source,omitempty"`

	// Tool use specific
	ToolName   string          `json:"tool_name,omitempty"`
	ToolInput  json.RawMessage `json:"tool_input,omitempty"`
	ToolOutput json.RawMessage `json:"tool_output,omitempty"`

	// User prompt specific
	UserPrompt string `json:"user_prompt,omitempty"`
}

// HookOutput represents the JSON output to send back to Claude Code.
type HookOutput struct {
	Decision       string              `json:"decision,omitempty"`
	Reason         string              `json:"reason,omitempty"`
	UpdatedInput   json.RawMessage     `json:"updatedInput,omitempty"`
	SuppressOutput bool                `json:"suppressOutput,omitempty"`
	HookSpecific   *HookSpecificOutput `json:"hookSpecificOutput,omitempty"`
}

// HookSpecificOutput contains event-specific response data.
type HookSpecificOutput struct {
	HookEventName     string `json:"hookEventName,omitempty"`
	AdditionalContext string `json:"additionalContext,omitempty"`
}

// ReadInput reads and decodes hook input from stdin.
func ReadInput() (*HookInput, error) {
	var input HookInput
	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		return nil, fmt.Errorf("failed to decode input: %w", err)
	}
	return &input, nil
}

// WriteOutput encodes and writes hook output to stdout.
func WriteOutput(output *HookOutput) error {
	return json.NewEncoder(os.Stdout).Encode(output)
}

func Approve(reason string) {
	WriteOutput(&HookOutput{Decision: "approve", Reason: reason})
}

func Deny(reason string) {
	WriteOutput(&HookOutput{Decision: "deny", Reason: reason})
}

func Ask(reason string) {
	WriteOutput(&HookOutput{Decision: "ask", Reason: reason})
}

func SessionContext(context string) {
	WriteOutput(&HookOutput{
		HookSpecific: &HookSpecificOutput{
			HookEventName:     "SessionStart",
			AdditionalContext: context,
		},
	})
}

// ApproveWithContext approves and injects additional context for the specified hook event.
// The context appears as a system reminder visible to the model.
func ApproveWithContext(eventName, context string) {
	WriteOutput(&HookOutput{
		Decision: "approve",
		HookSpecific: &HookSpecificOutput{
			HookEventName:     eventName,
			AdditionalContext: context,
		},
	})
}

func Debug(format string, args ...any) {
	if os.Getenv("HOOK_DEBUG") == "1" {
		fmt.Fprintf(os.Stderr, "[DEBUG] "+format+"\n", args...)
	}
}

func Fatal(code int, format string, args ...any) {
	fmt.Fprintf(os.Stderr, "[ERROR] "+format+"\n", args...)
	os.Exit(code)
}

func PluginRoot() string {
	root := os.Getenv("CLAUDE_PLUGIN_ROOT")
	if root == "" {
		Fatal(1, "CLAUDE_PLUGIN_ROOT not set")
	}
	return root
}

func ProjectDir() string {
	if dir := os.Getenv("CLAUDE_PROJECT_DIR"); dir != "" {
		return dir
	}
	if dir, err := os.Getwd(); err == nil {
		return dir
	}
	return "."
}
