package middleware

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

func HMAC(data string, key string) string {
	hash := hmac.New(sha256.New, []byte(key))
	hash.Write([]byte(data))
	return hex.EncodeToString(hash.Sum(nil))
}

func VerifyAgentSignature(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		agentID := r.Header.Get("X-Agent-ID")
		timestamp := r.Header.Get("X-Timestamp")
		receivedSig := r.Header.Get("X-Signature")

		if agentID == "" || timestamp == "" || receivedSig == "" {
			http.Error(w, "Missing required headers", http.StatusBadRequest)
			return
		}

		tsInt, err := strconv.ParseInt(timestamp, 10, 64)
		if err != nil {
			http.Error(w, "Invalid timestamp format", http.StatusBadRequest)
			return
		}
		now := time.Now().Unix()
		if abs(now-tsInt) > 300 {
			http.Error(w, "Timestamp expired or too far from server time", http.StatusUnauthorized)
			return
		}

		secret := os.Getenv("AGENT_SECRET")
		if secret == "" {
			log.Fatal("AGENT_SECRET is not set")
		}

		expectedSig := HMAC(agentID+timestamp, secret)
		if receivedSig != expectedSig {
			http.Error(w, "Invalid agent signature", http.StatusForbidden)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func abs(n int64) int64 {
	if n < 0 {
		return -n
	}
	return n
}
