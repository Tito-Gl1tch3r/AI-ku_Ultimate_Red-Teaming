package admin

import (
	"c2/services"
	"c2/utils"
	"encoding/json"
	"net/http"
)

// RegisterRequest represents the body of a request to register a new admin.
// @Description The RegisterRequest contains the credentials needed to register a new admin.
type RegisterRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// RegisterAdmin registers a new admin.
// @Summary Register new admin
// @Description Registers a new admin with the provided username and password.
// @Tags Admin - Authentication
// @Param register_request body admin.RegisterRequest true "New admin credentials"
// @Success 201 {object} map[string]string "Admin registration success message"
// @Failure 400 {string} string "Invalid input"
// @Failure 500 {string} string "Error registering admin"
// @Router /admin/register [post]
func RegisterAdmin(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		utils.LogError("Invalid input in RegisterAdmin")
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	err = services.RegisterAdmin(req.Username, req.Password)
	if err != nil {
		utils.LogError("Error registering admin")
		http.Error(w, "Error registering admin", http.StatusInternalServerError)
		return
	}

	utils.LogInfo("Admin registered successfully: " + req.Username)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]string{"message": "Admin registered successfully"})
}
