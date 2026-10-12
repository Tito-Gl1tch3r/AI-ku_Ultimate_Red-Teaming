package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"red-cloud/i18n"
	redc "red-cloud/mod"
	"red-cloud/mod/ai"
	"red-cloud/mod/gologger"
	"red-cloud/mod/mcp"
)

// OrchestratorConfig controls the multi-round orchestrator behavior.
type OrchestratorConfig struct {
	MaxRounds   int    `json:"maxRounds"`   // Maximum orchestration rounds (default 5)
	Objective   string `json:"objective"`   // High-level deployment objective
	AutoApprove bool   `json:"autoApprove"` // Skip user approval between rounds
}

// JudgeEvaluation is the structured output from the Judge agent.
type JudgeEvaluation struct {
	Complete       bool     `json:"complete"`
	Confidence     float64  `json:"confidence"`
	Feedback       string   `json:"feedback"`
	MissingAreas   []string `json:"missing_areas"`
	NextSteps      []string `json:"next_steps"`
	EvidenceSummary string  `json:"evidence_summary"`
}

// OrchestratorStream runs a multi-round orchestration loop:
// plan → deploy → verify → troubleshoot, with a Judge evaluating each round.
func (a *App) OrchestratorStream(conversationId string, config OrchestratorConfig, messages []AIChatMessage) error {
	profile, err := redc.GetActiveProfile()
	if err != nil || profile.AIConfig == nil {
		return fmt.Errorf("%s", i18n.T("app_ai_not_configured"))
	}
	aiConfig := profile.AIConfig
	if aiConfig.APIKey == "" || aiConfig.BaseURL == "" || aiConfig.Model == "" {
		return fmt.Errorf("%s", i18n.T("app_ai_config_incomplete"))
	}

	a.mu.Lock()
	project := a.project
	a.mu.Unlock()
	if project == nil {
		return fmt.Errorf("%s", i18n.T("app_project_not_loaded"))
	}

	maxRounds := config.MaxRounds
	if maxRounds <= 0 {
		maxRounds = 5
	}
	if maxRounds > 20 {
		maxRounds = 20
	}

	uiLang := a.GetLanguage()
	langPrompt := "请用中文回复"
	if uiLang == "en" {
		langPrompt = "Please reply in English"
	}

	// Create provider manager for failover
	pm := buildProviderManager(aiConfig)

	// Setup context
	totalTimeout := time.Duration(maxRounds) * 10 * time.Minute
	ctx, cancel := context.WithTimeout(context.Background(), totalTimeout)
	defer cancel()

	agentCancelMap.Lock()
	agentCancelMap.m[conversationId] = cancel
	agentCancelMap.Unlock()
	defer func() {
		agentCancelMap.Lock()
		delete(agentCancelMap.m, conversationId)
		agentCancelMap.Unlock()
	}()

	// Build MCP tools
	mcpServer := mcp.NewMCPServer(project, a)
	mcpTools := mcpServer.GetTools()
	toolDefs := make([]ai.ToolDefinition, 0, len(mcpTools))
	for _, t := range mcpTools {
		params := map[string]interface{}{
			"type":       t.InputSchema.Type,
			"properties": t.InputSchema.Properties,
		}
		if len(t.InputSchema.Required) > 0 {
			params["required"] = t.InputSchema.Required
		}
		toolDefs = append(toolDefs, ai.ToolDefinition{
			Type: "function",
			Function: ai.ToolFunctionDef{
				Name:        t.Name,
				Description: t.Description,
				Parameters:  params,
			},
		})
	}

	// Knowledge accumulator across rounds
	var evidenceLog []string
	var failureHistory []string
	var totalUsage ai.TokenUsage

	// Safety hooks
	hooks := ai.NewHookChain()

	// Emit orchestrator status
	emitOrchestratorStatus := func(round int, phase string, detail string) {
		a.emitEvent("ai-orchestrator-status", map[string]interface{}{
			"conversationId": conversationId,
			"round":          round,
			"totalRounds":    maxRounds,
			"phase":          phase,
			"detail":         detail,
		})
	}

	// Multi-round orchestration loop
	failoverRetries := 0
	const maxFailoverRetries = 3
	for round := 1; round <= maxRounds; round++ {
		if ctx.Err() != nil {
			break
		}

		emitOrchestratorStatus(round, "planning", fmt.Sprintf("Round %d/%d: Planning", round, maxRounds))

		// Build system prompt with cross-round knowledge injection
		systemPrompt := buildOrchestratorPrompt(config.Objective, round, maxRounds, evidenceLog, failureHistory, langPrompt)

		// Build messages for this round
		aiMessages := make([]ai.Message, 0, len(messages)+2)
		aiMessages = append(aiMessages, ai.Message{Role: "system", Content: systemPrompt})
		for _, m := range messages {
			aiMessages = append(aiMessages, ai.Message{Role: m.Role, Content: m.Content})
		}

		// Inject round context
		if round > 1 {
			roundCtx := fmt.Sprintf("\n[Orchestrator Round %d/%d]\nPrevious evidence: %s\n",
				round, maxRounds, strings.Join(evidenceLog, "; "))
			if len(failureHistory) > 0 {
				roundCtx += fmt.Sprintf("Previous failures: %s\n", strings.Join(failureHistory, "; "))
			}
			aiMessages = append(aiMessages, ai.Message{
				Role:    "user",
				Content: roundCtx + "Continue with the next phase of the objective.",
			})
		}

		// Execute agent loop for this round (reuse tool-calling loop logic)
		emitOrchestratorStatus(round, "executing", fmt.Sprintf("Round %d/%d: Executing", round, maxRounds))

		client := pm.CurrentClient()

		// Context window management: compact if exceeding budget
		contextBudget := 108000
		if aiConfig.ContextWindow > 0 {
			contextBudget = aiConfig.ContextWindow * 9 / 10
		}
		if estimated := ai.EstimateTokens(aiMessages); estimated > contextBudget {
			compactCtx, compactCancel := context.WithTimeout(ctx, 35*time.Second)
			aiMessages = ai.CompactWithLLM(compactCtx, client, aiMessages, ai.CompactOptions{
				KeepRecentRounds: 4,
				ContextBudget:    contextBudget,
				MaxSummaryTokens: 2000,
			})
			compactCancel()
			gologger.Info().Msgf("orchestrator: context compacted from ~%d to ~%d tokens in round %d", estimated, ai.EstimateTokens(aiMessages), round)
		}

		maxToolRounds := 30
		if aiConfig.MaxToolRounds > 0 {
			maxToolRounds = aiConfig.MaxToolRounds
		}

		var roundContent string
		roundErr := a.executeOrchestratorRound(ctx, client, aiMessages, toolDefs, mcpServer, conversationId, maxToolRounds, &totalUsage, &roundContent, hooks, config.AutoApprove)

		if roundErr != nil {
			failureHistory = append(failureHistory, fmt.Sprintf("Round %d failed: %s", round, roundErr.Error()))
			// Try failover (with retry limit to prevent infinite loop)
			if failoverRetries < maxFailoverRetries && ai.ShouldFailover(roundErr.Error()) && pm.Failover(roundErr.Error()) {
				gologger.Info().Msgf("orchestrator: failover triggered in round %d (retry %d/%d)", round, failoverRetries+1, maxFailoverRetries)
				failoverRetries++
				round-- // Retry this round with new provider
				continue
			}
			emitOrchestratorStatus(round, "error", roundErr.Error())
			continue
		}
		failoverRetries = 0 // Reset on success

		// Judge evaluation
		emitOrchestratorStatus(round, "judging", fmt.Sprintf("Round %d/%d: Evaluating results", round, maxRounds))

		evaluation := a.judgeRound(ctx, client, config.Objective, roundContent, evidenceLog, langPrompt)
		evidenceLog = append(evidenceLog, evaluation.EvidenceSummary)

		a.emitEvent("ai-orchestrator-judge", map[string]interface{}{
			"conversationId": conversationId,
			"round":          round,
			"evaluation":     evaluation,
		})

		if evaluation.Complete && evaluation.Confidence >= 0.8 {
			emitOrchestratorStatus(round, "complete",
				fmt.Sprintf("Objective achieved in %d rounds (confidence: %.0f%%)", round, evaluation.Confidence*100))
			a.emitEvent("ai-chat-complete", map[string]interface{}{
				"conversationId": conversationId,
				"success":        true,
				"usage":          totalUsage,
			})
			return nil
		}

		// Append judge feedback for next round
		messages = append(messages, AIChatMessage{
			Role:    "assistant",
			Content: roundContent,
		})
		if evaluation.Feedback != "" {
			messages = append(messages, AIChatMessage{
				Role:    "user",
				Content: fmt.Sprintf("[Judge Feedback for Round %d]: %s\nMissing areas: %s\nNext steps: %s",
					round, evaluation.Feedback,
					strings.Join(evaluation.MissingAreas, ", "),
					strings.Join(evaluation.NextSteps, ", ")),
			})
		}
	}

	// Exhausted all rounds
	a.emitEvent("ai-chat-chunk", map[string]string{
		"conversationId": conversationId,
		"chunk":          fmt.Sprintf("\n\n⚠️ Orchestrator completed %d rounds without fully achieving the objective.", maxRounds),
	})
	a.emitEvent("ai-chat-complete", map[string]interface{}{
		"conversationId": conversationId,
		"success":        true,
		"usage":          totalUsage,
	})
	return nil
}

// executeOrchestratorRound runs a single agent round within the orchestrator.
func (a *App) executeOrchestratorRound(ctx context.Context, client *ai.Client, messages []ai.Message, toolDefs []ai.ToolDefinition, mcpServer *mcp.MCPServer, conversationId string, maxToolRounds int, totalUsage *ai.TokenUsage, roundContent *string, hooks *ai.HookChain, autoApprove bool) error {
	var contentBuilder strings.Builder

	for step := 0; step < maxToolRounds; step++ {
		if ctx.Err() != nil {
			return ctx.Err()
		}

		resp, err := client.ChatWithToolsStream(ctx, messages, toolDefs, func(chunk string) error {
			a.emitEvent("ai-chat-chunk", map[string]string{
				"conversationId": conversationId,
				"chunk":          chunk,
			})
			return nil
		})
		if err != nil {
			return err
		}

		totalUsage.PromptTokens += resp.Usage.PromptTokens
		totalUsage.CompletionTokens += resp.Usage.CompletionTokens
		totalUsage.TotalTokens += resp.Usage.TotalTokens
		contentBuilder.WriteString(resp.Content)

		if len(resp.ToolCalls) == 0 {
			*roundContent = contentBuilder.String()
			return nil
		}

		messages = append(messages, ai.Message{
			Role:      "assistant",
			Content:   resp.Content,
			ToolCalls: resp.ToolCalls,
		})

		for _, tc := range resp.ToolCalls {
			args := parseToolArgs(tc)

			// Run safety pre-hooks
			hookResult := hooks.RunPreHooks(tc.Function.Name, args)
			if hookResult.Action == ai.HookBlock {
				resultContent := fmt.Sprintf("⛔ Blocked by safety hook: %s", hookResult.Message)
				a.emitEvent("ai-agent-tool-result", map[string]interface{}{
					"conversationId": conversationId,
					"toolCallId":     tc.ID,
					"toolName":       tc.Function.Name,
					"success":        false,
					"content":        resultContent,
				})
				messages = append(messages, ai.Message{
					Role: "tool", Content: resultContent, ToolCallID: tc.ID, Name: tc.Function.Name,
				})
				continue
			}
			if hookResult.Action == ai.HookConfirm {
				if autoApprove {
					gologger.Info().Msgf("orchestrator: auto-approved %s (autoApprove=true)", tc.Function.Name)
				} else {
					// Use ask_user mechanism for confirmation
					confirmResult, _ := a.handleAskUser(map[string]interface{}{
						"question":       hookResult.Message,
						"choices":        []interface{}{"Yes, proceed", "No, cancel"},
						"allow_freeform": false,
					}, conversationId, ctx)
					if !strings.Contains(strings.ToLower(confirmResult), "yes") &&
						!strings.Contains(strings.ToLower(confirmResult), "proceed") {
						resultContent := "Operation cancelled by user."
						a.emitEvent("ai-agent-tool-result", map[string]interface{}{
							"conversationId": conversationId,
							"toolCallId":     tc.ID,
							"toolName":       tc.Function.Name,
							"success":        false,
							"content":        resultContent,
						})
						messages = append(messages, ai.Message{
							Role: "tool", Content: resultContent, ToolCallID: tc.ID, Name: tc.Function.Name,
						})
						continue
					}
				}
			}

			a.emitEvent("ai-agent-tool-call", map[string]interface{}{
				"conversationId": conversationId,
				"toolCallId":     tc.ID,
				"toolName":       tc.Function.Name,
				"toolArgs":       args,
			})

			resultContent, success := a.executeSingleTool(tc, args, mcpServer, conversationId, ctx)

			// Run post-hooks (annotations)
			resultContent = hooks.RunPostHooks(tc.Function.Name, args, resultContent, success)

			const maxLen = 8000
			if len(resultContent) > maxLen {
				resultContent = resultContent[:maxLen] + "\n\n... (truncated)"
			}

			a.emitEvent("ai-agent-tool-result", map[string]interface{}{
				"conversationId": conversationId,
				"toolCallId":     tc.ID,
				"toolName":       tc.Function.Name,
				"success":        success,
				"content":        resultContent,
			})

			messages = append(messages, ai.Message{
				Role:       "tool",
				Content:    resultContent,
				ToolCallID: tc.ID,
				Name:       tc.Function.Name,
			})
		}
	}

	*roundContent = contentBuilder.String()
	return nil
}

// judgeRound uses the AI to evaluate whether the objective has been achieved.
func (a *App) judgeRound(ctx context.Context, client *ai.Client, objective string, roundOutput string, priorEvidence []string, langPrompt string) JudgeEvaluation {
	judgePrompt := buildJudgePrompt(objective, roundOutput, priorEvidence, langPrompt)

	judgeMessages := []ai.Message{
		{Role: "system", Content: "You are a deployment evaluation judge. Analyze the agent's work and output a JSON evaluation."},
		{Role: "user", Content: judgePrompt},
	}

	judgeCtx, cancel := context.WithTimeout(ctx, 60*time.Second)
	defer cancel()

	var result strings.Builder
	err := client.ChatStream(judgeCtx, judgeMessages, func(chunk string) error {
		result.WriteString(chunk)
		return nil
	})

	if err != nil {
		gologger.Warning().Msgf("orchestrator: judge evaluation failed: %v", err)
		return JudgeEvaluation{
			Complete:       false,
			Confidence:     0,
			Feedback:       "Judge evaluation failed: " + err.Error(),
			EvidenceSummary: "Judge unavailable",
		}
	}

	return parseJudgeOutput(result.String())
}

// buildOrchestratorPrompt creates the system prompt for an orchestration round.
func buildOrchestratorPrompt(objective string, round, maxRounds int, evidence, failures []string, langPrompt string) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf(`You are a RedC Orchestrator Agent. Your objective is to achieve the following goal through systematic multi-round execution:

## Objective
%s

## Current Round
Round %d of %d

## Action Framework
Each round, follow this cycle:
1. **Assess**: What is the current state? What has been done? What remains?
2. **Plan**: What specific actions should be taken this round?
3. **Execute**: Call the necessary tools to make progress
4. **Report**: Summarize what was accomplished, what evidence was gathered

`, objective, round, maxRounds))

	if len(evidence) > 0 {
		sb.WriteString("## Prior Evidence (from previous rounds)\n")
		for i, e := range evidence {
			sb.WriteString(fmt.Sprintf("- Round %d: %s\n", i+1, e))
		}
		sb.WriteString("\n")
	}

	if len(failures) > 0 {
		sb.WriteString("## Known Failures (avoid repeating)\n")
		for _, f := range failures {
			sb.WriteString(fmt.Sprintf("- %s\n", f))
		}
		sb.WriteString("\n")
	}

	sb.WriteString("## Rules\n")
	sb.WriteString("- Focus on making concrete progress each round\n")
	sb.WriteString("- Don't repeat actions that already succeeded in prior rounds\n")
	sb.WriteString("- If a previous approach failed, try a different strategy\n")
	sb.WriteString("- Report findings clearly so the judge can evaluate progress\n\n")
	sb.WriteString(langPrompt)

	return sb.String()
}

// buildJudgePrompt creates the prompt for the Judge evaluation.
func buildJudgePrompt(objective string, roundOutput string, priorEvidence []string, langPrompt string) string {
	truncatedOutput := roundOutput
	if len(truncatedOutput) > 4000 {
		truncatedOutput = truncatedOutput[:4000] + "... (truncated)"
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf(`Evaluate whether the following objective has been achieved based on the agent's output.

## Objective
%s

## Agent Output (this round)
%s

`, objective, truncatedOutput))

	if len(priorEvidence) > 0 {
		sb.WriteString("## Prior Evidence\n")
		for i, e := range priorEvidence {
			sb.WriteString(fmt.Sprintf("- Round %d: %s\n", i+1, e))
		}
		sb.WriteString("\n")
	}

	sb.WriteString(`## Output Format
Respond with ONLY a JSON object (no markdown fences):
{
  "complete": true/false,
  "confidence": 0.0-1.0,
  "feedback": "what went well or needs improvement",
  "missing_areas": ["area1", "area2"],
  "next_steps": ["step1", "step2"],
  "evidence_summary": "brief summary of concrete evidence gathered this round"
}

` + langPrompt)

	return sb.String()
}

// parseJudgeOutput extracts the JudgeEvaluation from the LLM's response.
func parseJudgeOutput(text string) JudgeEvaluation {
	text = strings.TrimSpace(text)

	// Try to find JSON in the text
	start := strings.Index(text, "{")
	end := strings.LastIndex(text, "}")
	if start >= 0 && end > start {
		text = text[start : end+1]
	}

	var eval JudgeEvaluation
	if err := json.Unmarshal([]byte(text), &eval); err != nil {
		gologger.Warning().Msgf("orchestrator: failed to parse judge output: %v", err)
		return JudgeEvaluation{
			Complete:       false,
			Confidence:     0.3,
			Feedback:       "Could not parse judge evaluation: " + text[:minInt(len(text), 200)],
			EvidenceSummary: "Parse failed",
		}
	}
	return eval
}

// buildProviderManager creates a ProviderManager from AIConfig.
func buildProviderManager(aiConfig *redc.AIConfig) *ai.ProviderManager {
	primary := ai.ProviderConfig{
		Name:     "primary",
		Provider: aiConfig.Provider,
		APIKey:   aiConfig.APIKey,
		BaseURL:  aiConfig.BaseURL,
		Model:    aiConfig.Model,
	}

	var fallbacks []ai.ProviderConfig
	for _, fb := range aiConfig.FallbackProviders {
		fallbacks = append(fallbacks, ai.ProviderConfig{
			Name:     fb.Name,
			Provider: fb.Provider,
			APIKey:   fb.APIKey,
			BaseURL:  fb.BaseURL,
			Model:    fb.Model,
		})
	}

	return ai.NewProviderManager(primary, fallbacks)
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}
