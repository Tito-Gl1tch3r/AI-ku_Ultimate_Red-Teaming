package agent

import (
	"c2/database"
	"c2/utils"
	"encoding/json"
	"net/http"
	"time"
)

type CommandResultRequest struct {
	AgentID string `json:"agent_id"`
	Command string `json:"command"`
	Result  string `json:"result"`
}

// SubmitResult handles the submission of command execution results from an agent.
// @Summary Submit the result of a command executed by an agent
// @Description This endpoint receives the result of a command executed by the agent, updates the corresponding command status, and stores the result in the database.
// @Accept json
// @Produce json
// @Param result body CommandResultRequest true "Command result details"
// @Success 200 {object} map[string]string "Successfully submitted the result"
// @Failure 400 {string} string "Invalid input data"
// @Failure 404 {string} string "Command not found or already processed"
// @Failure 500 {string} string "Internal server error"
// @Router /agent/result [post]
func SubmitResult(w http.ResponseWriter, r *http.Request) {
	var req CommandResultRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		utils.LogError("Invalid input on result submission")
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	db := database.Connect()
	defer db.Close()

	stmt := `UPDATE commands SET result = ?, status = 'done', executed_at = ? 
	         WHERE agent_id = ? AND command = ? AND status = 'pending'`

	res, err := db.Exec(stmt, req.Result, time.Now(), req.AgentID, req.Command)
	if err != nil {
		utils.LogError("Failed to update command result: " + err.Error())
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		http.Error(w, "No matching command found", http.StatusNotFound)
		return
	}

	utils.LogInfo("Result received from agent: " + req.AgentID + " -> " + req.Command)
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{
		"message": "Result submitted successfully",
	})
}
