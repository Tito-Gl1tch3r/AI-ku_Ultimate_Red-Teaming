package ai

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
)

func TestChatWithToolsStreamAnthropicGroupsToolResultsInNextUserMessage(t *testing.T) {
	var requestBody []byte
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var err error
		requestBody, err = io.ReadAll(r.Body)
		if err != nil {
			t.Errorf("read request body: %v", err)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	client := NewClient("anthropic", "test-key", server.URL, "test-model")
	messages := []Message{
		{Role: "user", Content: "Inspect both resources"},
		{Role: "assistant", ToolCalls: []ToolCall{
			{ID: "call-1", Type: "function", Function: ToolFunction{Name: "first", Arguments: `{}`}},
			{ID: "call-2", Type: "function", Function: ToolFunction{Name: "second", Arguments: `{}`}},
		}},
		{Role: "tool", ToolCallID: "call-1", Content: "first result"},
		{Role: "tool", ToolCallID: "call-2", Content: "second result"},
	}

	if _, err := client.ChatWithToolsStream(context.Background(), messages, nil, nil); err != nil {
		t.Fatalf("ChatWithToolsStream failed: %v", err)
	}

	var payload struct {
		Messages []struct {
			Role    string          `json:"role"`
			Content json.RawMessage `json:"content"`
		} `json:"messages"`
	}
	if err := json.Unmarshal(requestBody, &payload); err != nil {
		t.Fatalf("decode Anthropic request: %v", err)
	}
	if len(payload.Messages) != 3 {
		t.Fatalf("got %d Anthropic messages, want 3", len(payload.Messages))
	}

	resultsMessage := payload.Messages[2]
	if resultsMessage.Role != "user" {
		t.Fatalf("tool results role = %q, want user", resultsMessage.Role)
	}
	var results []struct {
		Type      string `json:"type"`
		ToolUseID string `json:"tool_use_id"`
	}
	if err := json.Unmarshal(resultsMessage.Content, &results); err != nil {
		t.Fatalf("decode tool results: %v", err)
	}
	if len(results) != 2 {
		t.Fatalf("got %d tool_result blocks, want 2", len(results))
	}
	if results[0].Type != "tool_result" || results[0].ToolUseID != "call-1" {
		t.Errorf("first result = %#v, want call-1 tool_result", results[0])
	}
	if results[1].Type != "tool_result" || results[1].ToolUseID != "call-2" {
		t.Errorf("second result = %#v, want call-2 tool_result", results[1])
	}
}

func TestChatStreamOpenAI(t *testing.T) {
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		t.Skip("OPENAI_API_KEY not set, skipping test")
	}

	client := NewClient("openai", apiKey, "https://api.openai.com/v1", "gpt-3.5-turbo")

	messages := []Message{
		{Role: "user", Content: "Say hello in one word"},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	var result string
	err := client.ChatStream(ctx, messages, func(chunk string) error {
		result += chunk
		t.Logf("Chunk: %s", chunk)
		return nil
	})

	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	if result == "" {
		t.Fatal("No response received")
	}

	t.Logf("Full response: %s", result)
}

func TestChatStreamAnthropic(t *testing.T) {
	apiKey := os.Getenv("ANTHROPIC_API_KEY")
	if apiKey == "" {
		t.Skip("ANTHROPIC_API_KEY not set, skipping test")
	}

	client := NewClient("anthropic", apiKey, "https://api.anthropic.com", "claude-3-haiku-20240307")

	messages := []Message{
		{Role: "user", Content: "Say hello in one word"},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	var result string
	err := client.ChatStream(ctx, messages, func(chunk string) error {
		result += chunk
		t.Logf("Chunk: %s", chunk)
		return nil
	})

	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	if result == "" {
		t.Fatal("No response received")
	}

	t.Logf("Full response: %s", result)
}
