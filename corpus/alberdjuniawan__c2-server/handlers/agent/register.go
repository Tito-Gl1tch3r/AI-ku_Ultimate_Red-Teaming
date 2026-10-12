package agent

import (
	"c2/database"
	"c2/services"
	"c2/utils"
	"encoding/json"
	"net/http"

	"github.com/google/uuid"
)

type RegisterRequest struct {
	Hostname string `json:"hostname"`
	OS       string `json:"os"`
	Arch     string `json:"arch"`
}

type RegisterResponse struct {
	Message string `json:"message"`
	Token   string `json:"token,omitempty"`
}

// RegisterAgent handles the registration of a new agent.
// @Summary Register a new agent
// @Description Registers a new agent with the provided hostname, OS, and architecture, and generates a token for the agent.
// @Accept json
// @Produce json
// @Param agent body RegisterRequest true "Agent registration details"
// @Success 201 {object} RegisterResponse "Successfully registered agent with a generated token"
// @Failure 400 {string} string "Invalid input data"
// @Failure 409 {string} string "Agent already registered"
// @Failure 500 {string} string "Internal server error during registration"
// @Router /agent/register [post]
func RegisterAgent(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		utils.LogError("Invalid input in RegisterAgent")
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	newID := uuid.New().String()

	ip := r.RemoteAddr

	db := database.Connect()
	defer db.Close()

	var count int
	err = db.QueryRow("SELECT COUNT(*) FROM agents WHERE id = ?", newID).Scan(&count)
	if err != nil {
		utils.LogError("Error checking if agent already exists: " + err.Error())
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	if count > 0 {
		utils.LogError("Agent already registered: " + newID)
		http.Error(w, "Agent already registered", http.StatusConflict)
		return
	}

	token, err := services.RegisterAgent(newID, ip, req.Hostname, req.OS, req.Arch)
	if err != nil {
		utils.LogError("Error registering agent: " + err.Error())
		http.Error(w, "Error registering agent", http.StatusInternalServerError)
		return
	}

	utils.LogInfo("Agent registered successfully: " + newID)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(RegisterResponse{
		Message: "Agent registered successfully",
		Token:   token,
	})
}
