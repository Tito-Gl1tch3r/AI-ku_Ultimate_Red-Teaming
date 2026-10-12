package mcp

import (
	"encoding/json"
	"fmt"
	"time"
)

func schedulerToolSchemas() []Tool {
	return []Tool{
		{
			Name:        "get_current_time",
			Description: "Get current system time and timezone. Use this before scheduling tasks or when user mentions relative time (e.g., '1小时后', '明天凌晨2点').",
			InputSchema: ToolSchema{
				Type:       "object",
				Properties: map[string]Property{},
			},
		},
		{
			Name:        "schedule_task",
			Description: "Schedule a future task for a case. Supports one-time or recurring tasks (daily/weekly/interval). Can run SSH commands on the case server and send notifications on completion.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"case_id": {
						Type:        "string",
						Description: "Case ID to schedule task for",
					},
					"case_name": {
						Type:        "string",
						Description: "Case name (for display)",
					},
					"action": {
						Type:        "string",
						Description: "Action to perform",
						Enum:        []string{"start", "stop", "kill", "ssh_command"},
					},
					"scheduled_at": {
						Type:        "string",
						Description: "Scheduled time in RFC3339 format (e.g., '2025-01-15T10:30:00+08:00'). Use get_current_time first to know the current time and timezone.",
					},
					"repeat_type": {
						Type:        "string",
						Description: "Repeat type: 'once' (default), 'daily', 'weekly', or 'interval'",
						Enum:        []string{"once", "daily", "weekly", "interval"},
					},
					"repeat_interval": {
						Type:        "number",
						Description: "Repeat interval in minutes (only for repeat_type='interval', e.g., 30 means every 30 minutes)",
					},
					"ssh_command": {
						Type:        "string",
						Description: "SSH command to execute on the case server (only for action='ssh_command'). E.g., 'systemctl restart nginx' or 'df -h && free -m'",
					},
					"notify": {
						Type:        "boolean",
						Description: "Whether to send a system notification when the task executes (default: false)",
					},
				},
				Required: []string{"case_id", "action", "scheduled_at"},
			},
		},
		{
			Name:        "list_scheduled_tasks",
			Description: "List all pending scheduled tasks with their status, next execution time, and repeat settings",
			InputSchema: ToolSchema{
				Type:       "object",
				Properties: map[string]Property{},
			},
		},
		{
			Name:        "cancel_scheduled_task",
			Description: "Cancel a pending scheduled task by its ID",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"task_id": {
						Type:        "string",
						Description: "Task ID to cancel",
					},
				},
				Required: []string{"task_id"},
			},
		},
	}
}

func (s *MCPServer) toolGetCurrentTime() (ToolResult, error) {
	now := time.Now()
	zone, offset := now.Zone()
	offsetHours := offset / 3600
	info := map[string]interface{}{
		"current_time":   now.Format(time.RFC3339),
		"local_time":     now.Format("2006-01-02 15:04:05"),
		"timezone":       zone,
		"utc_offset":     fmt.Sprintf("%+d:00", offsetHours),
		"unix_timestamp": now.Unix(),
	}
	data, _ := json.MarshalIndent(info, "", "  ")
	return ToolResult{
		Content: []ContentItem{{Type: "text", Text: string(data)}},
	}, nil
}

func (s *MCPServer) toolScheduleTask(caseID string, caseName string, action string, scheduledAtStr string, repeatType string, repeatInterval int, sshCommand string, notify bool) (ToolResult, error) {
	if s.app == nil {
		return ToolResult{}, fmt.Errorf("scheduler tools require GUI mode (AppBridge not available)")
	}
	scheduledAt, err := time.Parse(time.RFC3339, scheduledAtStr)
	if err != nil {
		return ToolResult{}, fmt.Errorf("invalid scheduled_at format (expected RFC3339): %v", err)
	}
	if repeatType == "" {
		repeatType = "once"
	}
	result, err := s.app.MCPScheduleTaskFull(caseID, caseName, action, scheduledAt, repeatType, repeatInterval, sshCommand, notify)
	if err != nil {
		return ToolResult{}, err
	}
	data, _ := json.MarshalIndent(result, "", "  ")
	return ToolResult{
		Content: []ContentItem{{Type: "text", Text: string(data)}},
	}, nil
}

func (s *MCPServer) toolListScheduledTasks() (ToolResult, error) {
	if s.app == nil {
		return ToolResult{}, fmt.Errorf("scheduler tools require GUI mode (AppBridge not available)")
	}
	result := s.app.MCPListScheduledTasks()
	data, _ := json.MarshalIndent(result, "", "  ")
	return ToolResult{
		Content: []ContentItem{{Type: "text", Text: string(data)}},
	}, nil
}

func (s *MCPServer) toolCancelScheduledTask(taskID string) (ToolResult, error) {
	if s.app == nil {
		return ToolResult{}, fmt.Errorf("scheduler tools require GUI mode (AppBridge not available)")
	}
	if err := s.app.MCPCancelScheduledTask(taskID); err != nil {
		return ToolResult{}, err
	}
	return ToolResult{
		Content: []ContentItem{{Type: "text", Text: fmt.Sprintf("Scheduled task %s cancelled", taskID)}},
	}, nil
}
