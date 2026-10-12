package utils

import (
	"bufio"
	"crypto/sha1"
	"math/rand"
	"os"
	"regexp"
	"strings"
)

func IsValidDomain(str string) bool {
	parts := strings.Split(str, ".")

	domainRegex := regexp.MustCompile("^[a-zA-Z0-9][-a-zA-Z0-9]{0,252}[a-zA-Z0-9]$|^[a-zA-Z0-9]$")

	hasValidParts := true

	for _, part := range parts {
		hasValidParts = hasValidParts && domainRegex.MatchString(part)
	}

	return hasValidParts
}

func ReadFile(filePath string) ([]string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var lines []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	return lines, scanner.Err()
}

func WriteFile(filePath string, appendMode bool, b []byte) error {

	var flag int

	if appendMode {
		flag = os.O_WRONLY | os.O_APPEND | os.O_CREATE
	} else {
		flag = os.O_WRONLY | os.O_CREATE | os.O_TRUNC
	}

	file, err := os.OpenFile(filePath, flag, 0644)
	if err != nil {
		return err
	}
	defer file.Close()

	_, err = file.Write(b)
	if err != nil {
		return err
	}

	return nil
}

func FileExists(filename string) bool {
	info, err := os.Stat(filename)
	if os.IsNotExist(err) {
		return false
	}
	if err != nil {
		return false
	}
	return !info.IsDir()
}

func SHA256(s string) []byte {
	h := sha1.New()
	h.Write([]byte(s))
	return h.Sum(nil)
}

func RandomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
	result := make([]byte, length)
	for i := range result {
		result[i] = charset[rand.Intn(len(charset))]
	}
	return string(result)
}
