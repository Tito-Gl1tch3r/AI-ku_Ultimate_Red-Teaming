package admin

import (
	"c2/database"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gorilla/mux"
)

type UpdateTagsAndNotesRequest struct {
	Tags  []string `json:"tags"`
	Notes string   `json:"notes"`
}

// UpdateTagsAndNotes updates the tags and notes of an agent.
// @Summary Update agent tags and notes
// @Description Updates the tags and notes of an agent based on the provided agent ID.
// @Tags Admin - Agent Management
// @Param agent_id path string true "Agent ID"
// @Param update_request body admin.UpdateTagsAndNotesRequest true "Agent tags and notes"
// @Success 200 {string} string "Agent tags and notes updated successfully"
// @Failure 400 {string} string "Invalid request body"
// @Failure 500 {string} string "Failed to update agent information"
// @Router /admin/agents/{agent_id}/update-meta [put]
func UpdateTagsAndNotes(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	agentID := vars["agent_id"]

	var requestData UpdateTagsAndNotesRequest
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, fmt.Sprintf("Invalid request body: %v", err), http.StatusBadRequest)
		return
	}

	err := database.UpdateTagsAndNotes(agentID, requestData.Tags, requestData.Notes)
	if err != nil {
		http.Error(w, "Failed to update agent information", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Write([]byte("Agent tags and notes updated successfully"))
}
