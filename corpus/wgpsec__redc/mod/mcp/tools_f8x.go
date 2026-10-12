package mcp

import "encoding/json"

func f8xToolSchemas() []Tool {
	return []Tool{
		{
			Name:        "install_tool",
			Description: "Install a tool on a remote VPS using f8x. Use get_f8x_catalog to find available tools first.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"case_id": {
						Type:        "string",
						Description: "The case ID of the target VPS",
					},
					"tool_name": {
						Type:        "string",
						Description: "The tool ID to install (e.g. 'nuclei', 'nmap', 'httpx')",
					},
				},
				Required: []string{"case_id", "tool_name"},
			},
		},
		{
			Name:        "get_installed_tools",
			Description: "Get the list of tools installed on a remote VPS. Returns tool names with install timestamps.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"case_id": {
						Type:        "string",
						Description: "The case ID of the target VPS",
					},
				},
				Required: []string{"case_id"},
			},
		},
		{
			Name:        "get_f8x_catalog",
			Description: "Get the catalog of available tools that can be installed via f8x. Supports filtering by category and keyword search.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"category": {
						Type:        "string",
						Description: "Filter by category (optional): basic, development, pentest-recon, pentest-exploit, pentest-post, blue-team, red-infra, vuln-env, misc, system",
					},
					"search": {
						Type:        "string",
						Description: "Search keyword to filter tools by name or description (optional)",
					},
				},
				Required: []string{},
			},
		},
	}
}

func (s *MCPServer) toolInstallF8xTool(params map[string]interface{}) (ToolResult, error) {
	caseID, _ := params["case_id"].(string)
	toolName, _ := params["tool_name"].(string)

	if caseID == "" || toolName == "" {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "case_id and tool_name are required"}}}, nil
	}

	if s.app == nil {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "f8x tools require GUI mode (AppBridge)"}}}, nil
	}

	taskID, err := s.app.MCPInstallF8xTool(caseID, toolName)
	if err != nil {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "Install failed: " + err.Error()}}}, nil
	}

	result := map[string]string{
		"status":  "started",
		"task_id": taskID,
		"tool":    toolName,
		"message": "Installation of " + toolName + " started. Use exec_command to check status if needed.",
	}
	data, _ := json.Marshal(result)
	return ToolResult{Content: []ContentItem{{Type: "text", Text: string(data)}}}, nil
}

func (s *MCPServer) toolGetInstalledTools(params map[string]interface{}) (ToolResult, error) {
	caseID, _ := params["case_id"].(string)

	if caseID == "" {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "case_id is required"}}}, nil
	}

	if s.app == nil {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "This tool requires GUI mode (AppBridge)"}}}, nil
	}

	installed, err := s.app.MCPGetInstalledTools(caseID)
	if err != nil {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "Error: " + err.Error()}}}, nil
	}

	data, _ := json.Marshal(installed)
	return ToolResult{Content: []ContentItem{{Type: "text", Text: string(data)}}}, nil
}

func (s *MCPServer) toolGetF8xCatalog(params map[string]interface{}) (ToolResult, error) {
	category, _ := params["category"].(string)
	search, _ := params["search"].(string)

	if s.app == nil {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "This tool requires GUI mode (AppBridge)"}}}, nil
	}

	catalog, err := s.app.MCPGetF8xCatalog(category, search)
	if err != nil {
		return ToolResult{Content: []ContentItem{{Type: "text", Text: "Error: " + err.Error()}}}, nil
	}

	data, _ := json.Marshal(catalog)
	return ToolResult{Content: []ContentItem{{Type: "text", Text: string(data)}}}, nil
}
