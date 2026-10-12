package utils

import (
	"fmt"
	"io"
	"log"
	"os"
	"time"
)

func LogInfo(message string) {
	log.Printf("[INFO] [%s] %s", time.Now().Format(time.RFC3339), message)
}

func LogWarning(message string) {
	log.Printf("[WARNING] [%s] %s", time.Now().Format(time.RFC3339), message)
}

func LogError(message string) {
	log.Printf("[ERROR] [%s] %s", time.Now().Format(time.RFC3339), message)
}

func LogErrorWithErr(context string, err error) {
	if err != nil {
		log.Printf("[ERROR] [%s] %s: %v", time.Now().Format(time.RFC3339), context, err)
	}
}

func SetupLogger() (*os.File, error) {
	logPath := os.Getenv("APP_LOG_PATH")
	if logPath == "" {
		logPath = "app.log"
	}

	logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
	if err != nil {
		return nil, fmt.Errorf("unable to open log file: %v", err)
	}

	multiWriter := io.MultiWriter(os.Stdout, logFile)
	log.SetOutput(multiWriter)

	log.SetFlags(log.LstdFlags)
	return logFile, nil
}
