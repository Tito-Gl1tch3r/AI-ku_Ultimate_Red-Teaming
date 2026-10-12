// mod/plugin/template_http.go
package plugin

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"strings"
	"time"
)

var httpClient = &http.Client{Timeout: 30 * time.Second}

func fnHTTPGet(rawURL string, headers interface{}) (string, error) {
	return doHTTP("GET", rawURL, headers, "")
}

func fnHTTPPost(rawURL string, headers interface{}, body string) (string, error) {
	return doHTTP("POST", rawURL, headers, body)
}

func fnHTTPPut(rawURL string, headers interface{}, body string) (string, error) {
	return doHTTP("PUT", rawURL, headers, body)
}

func fnHTTPDelete(rawURL string, headers interface{}) (string, error) {
	return doHTTP("DELETE", rawURL, headers, "")
}

func doHTTP(method, rawURL string, headers interface{}, body string) (string, error) {
	var bodyReader io.Reader
	if body != "" {
		bodyReader = strings.NewReader(body)
	}

	req, err := http.NewRequest(method, rawURL, bodyReader)
	if err != nil {
		return "", fmt.Errorf("http %s: %w", method, err)
	}

	if headers != nil {
		switch h := headers.(type) {
		case map[string]interface{}:
			for k, v := range h {
				req.Header.Set(k, fmt.Sprintf("%v", v))
			}
		case map[string]string:
			for k, v := range h {
				req.Header.Set(k, v)
			}
		}
	}

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("http %s %s: %w", method, rawURL, err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("http read body: %w", err)
	}

	return string(respBody), nil
}

func fnExec(name string, args ...string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()
	cmd := exec.CommandContext(ctx, name, args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return string(out), fmt.Errorf("exec %s: %w: %s", name, err, string(out))
	}
	return strings.TrimSpace(string(out)), nil
}
