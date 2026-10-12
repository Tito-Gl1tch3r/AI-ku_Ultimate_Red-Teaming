package admin

import (
	"c2/database"
	"c2/utils"
	"database/sql"
	"encoding/json"
	"net/http"
)

// LoginRequest represents the body of a login request for the admin.
// @Description The LoginRequest contains the credentials needed for admin login.
type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// LoginAdmin authenticates the admin and generates a JWT token upon successful login.
// @Summary Admin login
// @Description Authenticates an admin based on the provided username and password and returns a JWT token.
// @Tags Admin - Authentication
// @Param login_request body admin.LoginRequest true "Login credentials"
// @Success 200 {object} map[string]string "JWT token"
// @Failure 400 {string} string "Invalid input"
// @Failure 401 {string} string "Invalid credentials"
// @Failure 500 {string} string "Database error or token generation error"
// @Router /admin/login [post]
func LoginAdmin(w http.ResponseWriter, r *http.Request) {
	var req LoginRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		utils.LogError("Invalid input in LoginAdmin")
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	db := database.Connect()
	defer db.Close()

	var hashedPassword string
	err = db.QueryRow("SELECT password FROM users WHERE username = ?", req.Username).Scan(&hashedPassword)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Invalid credentials", http.StatusUnauthorized)
		} else {
			utils.LogError("Database error in LoginAdmin")
			http.Error(w, "Database error", http.StatusInternalServerError)
		}
		return
	}

	if !utils.VerifyPassword(hashedPassword, req.Password) {
		http.Error(w, "Invalid credentials", http.StatusUnauthorized)
		return
	}

	token, err := utils.GenerateJWT(req.Username)
	if err != nil {
		utils.LogError("Error generating token in LoginAdmin")
		http.Error(w, "Error generating token", http.StatusInternalServerError)
		return
	}

	utils.LogInfo("Admin logged in successfully: " + req.Username)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"token": token})
}
